import asyncio
import time

from typing import List

from config import CONFIG
from schemas import WorkOrder, WorkResult
from agents.base_agent import BaseAgent
from agents.video_prompt_crafter import VideoPromptCrafter
from agents.video_qc import VideoQCAgent
from video.video_api import VideoProvider, CloudGPUProvider, KenBurnsDegradation, VideoClipResult
from logger_config import setup_logger

logger = setup_logger("VideoLead")

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
                    "clip_duration": clip_duration,
                },
                story_hash=story_hash,
                priority=2,
            )
            agent = VideoPromptCrafter(timeout_ms=30000)
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

        clip_results = []
        for p in prompts:
            result = await self._provider.generate(
                prompt=p.get("video_prompt", ""),
                reference_image_url=p.get("reference_image_url"),
                seed=p.get("seed", 0),
                duration_s=p.get("expected_duration_s", clip_duration),
            )
            clip_results.append({
                "prompt_data": p,
                "clip_result": result,
            })

            if not result.success and self._try_fallback():
                logger.info(f"CloudGPU failed, degrading to Ken Burns")
                kb = KenBurnsDegradation()
                result2 = await kb.generate(
                    prompt=p.get("video_prompt", ""),
                    reference_image_url=p.get("reference_image_url"),
                )
                clip_results[-1]["clip_result"] = result2

        qc_tasks = []
        for cr in clip_results:
            pd = cr["prompt_data"]
            clip = cr["clip_result"]
            if not clip.success:
                continue
            qc_wo = WorkOrder(
                agent_type="video_qc",
                input_data={
                    "clip_url": clip.clip_url or "",
                    "video_prompt": pd.get("video_prompt", ""),
                    "expected_duration_s": pd.get("expected_duration_s", clip_duration),
                    "character_anchors": pd.get("character_anchors", []),
                    "color_palette": "",
                },
                story_hash=story_hash,
                priority=3,
            )
            agent = VideoQCAgent(timeout_ms=15000)
            qc_tasks.append(agent.execute(qc_wo))

        qc_results = []
        if qc_tasks:
            qc_raw = await asyncio.gather(
                *[run_with_sem(t) for t in qc_tasks],
                return_exceptions=True,
            )
            for r in qc_raw:
                if isinstance(r, WorkResult) and r.success:
                    qc_results.append(r.output_data)
                elif isinstance(r, Exception):
                    qc_results.append({"status": "warning", "score": 0.5, "issues": [str(r)]})

        wall = (time.time() - start) * 1000

        approved_clips = []
        for i, cr in enumerate(clip_results):
            clip = cr["clip_result"]
            qc = qc_results[i] if i < len(qc_results) else {"status": "approved", "score": 0.5}
            approved_clips.append({
                "scene_id": cr["prompt_data"].get("scene_id", f"scene_{i}"),
                "prompt": cr["prompt_data"].get("video_prompt", ""),
                "seed": cr["prompt_data"].get("seed", 0),
                "source": clip.source,
                "qc_status": qc.get("status", "warning"),
                "qc_score": qc.get("score", 0.5),
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
