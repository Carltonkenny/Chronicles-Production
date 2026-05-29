import pytest
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from video.video_api import VideoProvider, CloudGPUProvider, KenBurnsDegradation, VideoClipResult
from schemas import WorkOrder
from config import CONFIG


class TestVideoProvider:
    def test_cloud_gpu_no_endpoint(self):
        provider = CloudGPUProvider(endpoint="", api_key="")
        result = asyncio.run(provider.generate("test prompt"))
        assert result.success is False
        err = (result.error or "").lower()
        assert any(x in err for x in ["not configured", "connect", "timeout", "404", "500", "11001", "getaddrinfo"])

    def test_ken_burns_always_succeeds(self):
        provider = KenBurnsDegradation()
        from video.video_api import ImageConditioningInput
        images = [ImageConditioningInput(url="http://example.com/img.png")]
        result = asyncio.run(provider.generate("test", images=images))
        assert result.success is True
        assert result.source == "ken_burns"
        assert result.clip_url == "http://example.com/img.png"

    def test_ken_burns_no_reference(self):
        provider = KenBurnsDegradation()
        result = asyncio.run(provider.generate("test"))
        assert result.success is True
        assert result.clip_url is None

    def test_video_clip_result_defaults(self):
        r = VideoClipResult(clip_bytes=b"data")
        assert r.success is True
        assert r.source == "unknown"
        assert r.clip_bytes == b"data"

    def test_video_clip_result_failure(self):
        r = VideoClipResult(success=False, error="failed")
        assert r.success is False
        assert r.error == "failed"


class TestVideoLeadAgent:
    def test_video_lead_agent_type(self):
        from agents.video_lead import VideoLead
        agent = VideoLead()
        assert agent.agent_type == "video_lead"

    def test_video_lead_empty_scenes(self):
        from agents.video_lead import VideoLead
        agent = VideoLead()
        wo = WorkOrder(
            agent_type="video_lead",
            input_data={
                "scenes": [],
                "visual_bible": {},
                "character_bibles": {},
                "reference_images": {},
                "clip_duration": 10,
            },
            story_hash="test123",
            priority=1,
        )
        result = asyncio.run(agent.execute(wo))
        assert result.success is False

    def test_video_lead_defaults_from_config(self):
        from agents.video_lead import VideoLead
        agent = VideoLead()
        assert agent is not None

    def test_video_lead_provider_override(self):
        from agents.video_lead import VideoLead
        agent = VideoLead(provider="ken_burns")
        assert agent is not None


class TestVideoPromptCrafter:
    def test_prompt_crafter_agent_type(self):
        from agents.video_prompt_crafter import VideoPromptCrafter
        agent = VideoPromptCrafter()
        assert agent.agent_type == "video_prompt_crafter"

    @pytest.mark.asyncio
    async def test_prompt_crafter_empty_scene(self, monkeypatch):
        async def mock_llm(*args, **kwargs):
            return "A cinematic scene at an unknown location."

        monkeypatch.setattr("agents.video_prompt_crafter.call_llm", mock_llm)
        from agents.video_prompt_crafter import VideoPromptCrafter
        agent = VideoPromptCrafter()
        wo = WorkOrder(
            agent_type="video_prompt_crafter",
            input_data={
                "scene": {"id": "test", "summary": "", "location": "", "characters": [], "emotional_beat": "neutral"},
                "visual_bible": {},
                "character_bibles": {},
                "reference_images": {},
                "clip_duration": 10,
            },
            story_hash="test",
            priority=2,
        )
        result = await agent.execute(wo)
        assert result.success is True
        assert "video_prompt" in result.output_data
        assert result.output_data["seed"] > 0

    @pytest.mark.asyncio
    async def test_prompt_crafter_with_character_bible(self, monkeypatch):
        async def mock_llm(*args, **kwargs):
            return "Character is IDENTICAL to reference image. Steel-gray eyes, braided red beard."

        monkeypatch.setattr("agents.video_prompt_crafter.call_llm", mock_llm)
        from agents.video_prompt_crafter import VideoPromptCrafter
        agent = VideoPromptCrafter()
        wo = WorkOrder(
            agent_type="video_prompt_crafter",
            input_data={
                "scene": {
                    "id": "scene_1",
                    "summary": "Bjorn discovers star-metal in the river",
                    "location": "Frozen river at dawn",
                    "characters": ["Bjorn"],
                    "emotional_beat": "wonder",
                },
                "visual_bible": {
                    "color_palette": ["#2C1810", "#D4451A"],
                    "lighting_style": "Cold blue dawn light",
                    "camera_language": "Wide establishing shot",
                },
                "character_bibles": {
                    "Bjorn": {
                        "appearance": "Steel-gray eyes, braided red beard, jagged scar",
                        "signature_items": ["boar-head hammer"],
                    }
                },
                "reference_images": {"Bjorn": "http://example.com/bjorn.png"},
                "clip_duration": 10,
            },
            story_hash="test",
            priority=2,
        )
        result = await agent.execute(wo)
        assert result.success is True
        data = result.output_data
        assert data["scene_id"] == "scene_1"
        assert data["expected_duration_s"] == 10
        assert len(data["character_anchors"]) >= 1
        assert "Bjorn" in data["character_anchors"][0]
        assert data["reference_image_url"] == "http://example.com/bjorn.png"


class TestVideoQC:
    def test_qc_agent_type(self):
        from agents.video_qc import VideoQCAgent
        agent = VideoQCAgent()
        assert agent.agent_type == "video_qc"

    def test_qc_no_clip_url(self):
        from agents.video_qc import VideoQCAgent
        agent = VideoQCAgent()
        wo = WorkOrder(
            agent_type="video_qc",
            input_data={
                "clip_url": "",
                "video_prompt": "test",
                "expected_duration_s": 8,
                "character_anchors": [],
                "color_palette": "",
            },
            story_hash="test",
            priority=3,
        )
        result = asyncio.run(agent.execute(wo))
        assert result.success is True
        assert result.output_data["status"] == "approved"

    def test_qc_with_anchors(self):
        from agents.video_qc import VideoQCAgent
        agent = VideoQCAgent()
        wo = WorkOrder(
            agent_type="video_qc",
            input_data={
                "clip_url": "",
                "video_prompt": "A viking warrior striking an anvil",
                "expected_duration_s": 10,
                "character_anchors": ["steel_gray_eyes", "boar_head_hammer"],
                "color_palette": "#2C1810, #D4451A",
            },
            story_hash="test",
            priority=3,
        )
        result = asyncio.run(agent.execute(wo))
        assert result.success is True


class TestConfig:
    def test_video_config_defaults(self):
        assert CONFIG.CLIP_DURATION_S == 12
        assert CONFIG.VIDEO_CLIP_COUNT == 7
        assert CONFIG.VIDEO_PROVIDER in ("cloud_gpu", "ken_burns")

    def test_video_provider_config_reads_env(self):
        assert isinstance(CONFIG.VIDEO_PROVIDER, str)
        assert isinstance(CONFIG.CLOUD_GPU_ENDPOINT, str)
