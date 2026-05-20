from agents.base_agent import BaseAgent
from schemas import WorkOrder, WorkResult
from prompts.video_qc_prompt import VIDEO_QC_PROMPT
from utils.llm_client import call_llm
from logger_config import setup_logger

logger = setup_logger("VideoQC")


class VideoQCAgent(BaseAgent):
    agent_type = "video_qc"

    async def _execute_internal(self, work_order: WorkOrder) -> WorkResult:
        data = work_order.input_data
        clip_url = data.get("clip_url", "")
        video_prompt = data.get("video_prompt", "")
        expected_duration = data.get("expected_duration_s", 8)
        character_anchors = data.get("character_anchors", [])
        color_palette = data.get("color_palette", "")

        if not clip_url:
            return WorkResult(
                success=True,
                output_data={
                    "status": "approved",
                    "score": 0.5,
                    "issues": ["No clip URL to validate — auto-approved"],
                },
                wall_time_ms=self.wall_time_ms,
                tokens_used=self.tokens_used,
            )

        prompt = VIDEO_QC_PROMPT.format(
            prompt=video_prompt,
            expected_duration_s=expected_duration,
            character_anchors=", ".join(character_anchors) if character_anchors else "Not specified",
            color_palette=color_palette or "Not specified",
            clip_url=clip_url,
        )

        llm_result = await call_llm(
            system="You are a video quality controller.",
            user=prompt,
            temperature=0.3,
            max_tokens=300,
        )

        self.tokens_used = 0

        import json as _json
        score = 0.5
        issues = []
        suggestion = ""
        status_raw = "warning"
        if isinstance(llm_result, str):
            try:
                parsed = _json.loads(llm_result)
                score = parsed.get("score", 0.5)
                issues = parsed.get("issues", [])
                suggestion = parsed.get("suggestion", "")
                status_raw = parsed.get("status", "warning")
            except (_json.JSONDecodeError, AttributeError):
                pass

        if score >= 0.6:
            status = "approved"
        elif score >= 0.3:
            status = "warning"
        else:
            status = "rejected"

        return WorkResult(
            success=True,
            output_data={
                "status": status,
                "score": score,
                "issues": issues,
                "suggestion": suggestion,
            },
            wall_time_ms=self.wall_time_ms,
            tokens_used=self.tokens_used,
        )
