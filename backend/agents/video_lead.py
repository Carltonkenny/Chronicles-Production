import asyncio
import time
from pathlib import Path
from typing import List

from config import CONFIG
from schemas import WorkOrder, WorkResult
from agents.base_agent import BaseAgent
from agents.video_prompt_crafter import VideoPromptCrafter
from video.video_api import VideoProvider, CloudGPUProvider, KenBurnsDegradation, VideoClipResult, ImageConditioningInput
from logger_config import setup_logger

logger = setup_logger("VideoLead")

CLIPS_DIR = Path(__file__).parent.parent / "generated" / "clips"

PROVIDER_MAP = {
    "cloud_gpu": CloudGPUProvider,
    "ken_burns": KenBurnsDegradation,
}


class VideoLead(BaseAgent):
    agent_type = "video_lead"

    def __init__(self, timeout_ms: int = None, provider: str = None):
        super().__init__(timeout_ms or 120000)
        provider_name = provider or CONFIG.VIDEO_PROVIDER
        provider_class = PROVIDER_MAP.get(provider_name, CloudGPUProvider)
        self._provider: VideoProvider = provider_class()

    async def _execute_internal(self, work_order: WorkOrder) -> WorkResult:
        data = work_order.input_data
        story_hash = work_order.story_hash or "unknown"
        scenes = data.get("scenes", [])
        visual_bible = data.get("visual_bible", {})
        character_bibles = data.get("character_bibles", {})
        reference_images = data.get("reference_images", {})
        audio_prompts = data.get("audio_prompts", {})
        clip_duration = data.get("clip_duration", CONFIG.CLIP_DURATION_S)

        start = time.time()

        crafter_tasks = []
        for scene in scenes:
            if not isinstance(scene, dict):
                continue
            wo = WorkOrder(
                agent_type="video_prompt_crafter",
                input_data={
                    "scene": scene,
                    "visual_bible": visual_bible,
                    "character_bibles": character_bibles,
                    "reference_images": reference_images,
                    "audio_prompts": audio_prompts,
                    "clip_duration": clip_duration,
                },
                story_hash=story_hash,
                priority=2,
            )
            agent = VideoPromptCrafter(timeout_ms=90000)
            crafter_tasks.append(agent.execute(wo))

        sem = asyncio.Semaphore(CONFIG.MAX_CONCURRENT_LLM)
        async def run_with_sem(task):
            async with sem:
                return await task

        logger.info(f"[{self.agent_type}] Spawning {len(crafter_tasks)} prompt crafters")
        crafter_results = await asyncio.gather(
            *[run_with_sem(t) for t in crafter_tasks],
            return_exceptions=True,
        )

        prompts = []
        for r in crafter_results:
            if isinstance(r, WorkResult) and r.success:
                prompts.append(r.output_data)
            elif isinstance(r, Exception):
                logger.warning(f"Prompt crafter failed: {r}")

        if not prompts:
            return WorkResult(
                success=False,
                error_message="All prompt crafters failed",
                wall_time_ms=(time.time() - start) * 1000,
            )

        CLIPS_DIR.mkdir(parents=True, exist_ok=True)

        clip_results = []
        for p in prompts:
            clip_path = ""
            image_refs = p.get("images", [])
            images = [ImageConditioningInput(url=img.get("url", ""), frame_idx=img.get("frame_idx", 0), strength=img.get("strength", 1.0))
                      for img in image_refs] if image_refs else None
            result = await self._provider.generate(
                prompt=p.get("video_prompt", ""),
                images=images,
                audio_prompt=p.get("audio_prompt"),
                seed=p.get("seed", 0),
                duration_s=p.get("expected_duration_s", clip_duration),
            )
            if result.success and result.clip_bytes:
                scene_id = p.get("scene_id", f"scene_{len(clip_results)}")
                filename = f"{story_hash}_{scene_id}.mp4"
                clip_path = str(CLIPS_DIR / filename)
                try:
                    Path(clip_path).write_bytes(result.clip_bytes)
                    result.clip_url = f"/clips/{filename}"
                except OSError as e:
                    logger.warning(f"Failed to write clip {filename}: {e}")
                    clip_path = ""
            clip_results.append({
                "prompt_data": p,
                "clip_result": result,
                "clip_path": clip_path,
            })

            if not result.success and self._try_fallback():
                logger.info(f"CloudGPU failed, degrading to Ken Burns")
                kb = KenBurnsDegradation()
                image_refs = p.get("images", [])
                images_fb = [ImageConditioningInput(url=img.get("url", ""), frame_idx=img.get("frame_idx", 0), strength=img.get("strength", 1.0))
                             for img in image_refs] if image_refs else None
                result2 = await kb.generate(
                    prompt=p.get("video_prompt", ""),
                    images=images_fb,
                )
                clip_results[-1]["clip_result"] = result2
                clip_results[-1]["clip_path"] = ""

        wall = (time.time() - start) * 1000

        approved_clips = []
        for i, cr in enumerate(clip_results):
            clip = cr["clip_result"]
            clip_path = cr.get("clip_path", "")
            qc_status = "approved" if clip.success else "rejected"
            qc_score = 1.0 if clip.success else 0.0
            if clip.success and clip_path and Path(clip_path).exists():
                st = Path(clip_path).stat()
                if st.st_size < 1000:
                    qc_status = "warning"
                    qc_score = 0.5
            approved_clips.append({
                "scene_id": cr["prompt_data"].get("scene_id", f"scene_{i}"),
                "prompt": cr["prompt_data"].get("video_prompt", ""),
                "seed": cr["prompt_data"].get("seed", 0),
                "source": clip.source,
                "clip_path": clip_path,
                "clip_url": clip.clip_url or "",
                "qc_status": qc_status,
                "qc_score": qc_score,
            })

        success_count = sum(1 for c in clip_results if c["clip_result"].success)
        logger.info(
            f"[{self.agent_type}] Complete: {success_count}/{len(clip_results)} clips "
            f"in {wall:.0f}ms"
        )

        return WorkResult(
            success=success_count > 0,
            output_data={
                "clips": approved_clips,
                "total_clips": len(clip_results),
                "successful_clips": success_count,
                "wall_time_ms": wall,
            },
            wall_time_ms=wall,
            tokens_used=self.tokens_used,
        )

    def _try_fallback(self) -> bool:
        return CONFIG.VIDEO_PROVIDER != "pollinations"
