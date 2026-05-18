import pytest
import asyncio
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from schemas.enums import Culture, Timeline, Theme
from schemas.story import StoryRequest, StoryOutput
from config import TIMELINE_BUCKETS, BUCKET_ORDER, CULTURE_NATURAL_ERA, SAFETY_CONSTRAINED_CULTURES
from agents.base_agent import BaseAgent
from agents.script_supervisor import ScriptSupervisorAgent


class TestEnumSystem:
    def test_culture_count(self):
        assert len(list(Culture)) == 15

    def test_timeline_count(self):
        assert len(list(Timeline)) == 15

    def test_theme_count(self):
        assert len(list(Theme)) == 15

    def test_all_cultures_have_display_name(self):
        for c in Culture:
            name = c.value.replace("_", " ").title()
            assert len(name) > 0

    def test_all_timelines_have_bucket(self):
        for t in Timeline:
            assert t.value in TIMELINE_BUCKETS, f"Missing bucket for {t.value}"

    def test_all_cultures_have_natural_era(self):
        for c in Culture:
            assert c.value in CULTURE_NATURAL_ERA, f"Missing natural era for {c.value}"

    def test_bucket_order_contains_all_buckets(self):
        for bucket in TIMELINE_BUCKETS.values():
            assert bucket in BUCKET_ORDER

    def test_safety_constrained_cultures(self):
        assert "nazi_germany" in SAFETY_CONSTRAINED_CULTURES
        assert "british_empire" in SAFETY_CONSTRAINED_CULTURES
        assert "spanish_empire" in SAFETY_CONSTRAINED_CULTURES


class TestForceBlending:
    def test_mode_detection_historical(self):
        from chain import detect_mode
        mode, bridge = detect_mode("roman", "classical_antiquity")
        assert mode == "historical"
        assert bridge == {}

    def test_mode_detection_counterfactual(self):
        from chain import detect_mode
        mode, bridge = detect_mode("roman", "ai_hegemony")
        assert mode == "counterfactual_required"
        assert bridge["distance_buckets"] >= 3

    def test_mode_detection_near(self):
        from chain import detect_mode
        mode, bridge = detect_mode("viking", "age_of_exploration")
        assert mode in ("historical", "counterfactual")

    def test_bridge_prompt_fragment(self):
        from chain import build_bridge_prompt_fragment
        bridge = {"mode": "counterfactual", "distance_buckets": 2, "culture_bucket": "ancient", "timeline_bucket": "modern"}
        fragment = build_bridge_prompt_fragment(bridge)
        assert "counterfactual" in fragment.lower()
        assert "framing_label" in fragment
        assert "divergence_point" in fragment
        assert "continuity_rules" in fragment

    def test_safety_appendix(self):
        from chain import build_safety_appendix
        appendix = build_safety_appendix("nazi_germany")
        assert "No heroic Nazis" in appendix
        appendix = build_safety_appendix("roman")
        assert appendix == ""

    def test_writer_bridge_context(self):
        from chain import build_writer_bridge_context
        bridge = {"mode": "counterfactual", "distance_buckets": 2}
        blueprint = {
            "framing_label": "alternate history",
            "divergence_point": "Rome never fell.",
            "continuity_rules": ["Rule 1", "Rule 2", "Rule 3"],
            "diffusion_rules": ["Diff 1", "Diff 2", "Diff 3"],
            "cost": "Everything changed.",
            "integration_notes": ["Note 1", "Note 2", "Note 3"],
        }
        ctx = build_writer_bridge_context(bridge, blueprint)
        assert "alternate history" in ctx
        assert "Rome never fell" in ctx
        assert "Rule 1" in ctx


class TestBaseAgent:
    def test_base_agent_initialization(self):
        agent = ScriptSupervisorAgent(timeout_ms=30000)
        assert agent.timeout_ms == 30000
        assert agent.agent_type == "script_supervisor"

    def test_base_agent_cache_key(self):
        from schemas import WorkOrder
        agent = ScriptSupervisorAgent()
        wo = WorkOrder(agent_type="test", story_hash="abc123")
        key = agent._compute_cache_key(wo)
        assert key is not None
        assert len(key) > 0


class TestScriptSupervisorAgent:
    def test_agent_type(self):
        agent = ScriptSupervisorAgent()
        assert agent.agent_type == "script_supervisor"

    def test_execute_with_empty_story(self):
        agent = ScriptSupervisorAgent()
        from schemas import WorkOrder
        wo = WorkOrder(agent_type="script_supervisor", input_data={"story": "", "title": "Test"})
        result = asyncio.run(agent.execute(wo))
        assert result.success is False
        assert "No story text" in result.error_message


class TestSchemas:
    def test_story_request_validation(self):
        req = StoryRequest(
            seed_idea="A blacksmith forges a blade from fallen star metal",
            culture=Culture.VIKING,
            timeline=Timeline.HIGH_MEDIEVAL,
            theme=Theme.AMBITION,
        )
        assert req.culture == Culture.VIKING

    def test_story_request_invalid_culture(self):
        with pytest.raises(ValueError):
            StoryRequest(
                seed_idea="test",
                culture="nonexistent",
                timeline=Timeline.HIGH_MEDIEVAL,
                theme=Theme.AMBITION,
            )
