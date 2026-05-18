import pytest
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from schemas.visual_bible import VisualBible, VisualElementsDict, VisualElement, CharacterBible, ShotVariation, EmotionCameraMap, LocationDescription
from schemas import WorkOrder
from agents.director import DirectorAgent
from agents.production_designer import ProductionDesignerAgent
from agents.art_director import ArtDirectorAgent
from utils.visual_engine import VisualElementsEngine, total_items, BUCKET_MATERIAL_MAP


class TestVisualBibleSchema:
    def test_visual_bible_creation(self):
        vb = VisualBible(
            story_hash="abc123",
            film_tone="Dark and brooding",
            pacing="Slow build to frantic climax",
            character_bibles=[
                CharacterBible(name="Bjorn", role="Blacksmith", appearance="Steel-gray eyes, braided beard",
                               costume="Leather tunic", signature_items=["boar-head hammer"],
                               emotional_range="wonder→obsession")
            ],
            location_descriptions=[
                LocationDescription(name="forge", description="Smoke-filled timber building",
                                    materials=["oak", "iron"], lighting="Firelight warm orange", time_of_day="night")
            ],
            shot_variation_matrix={
                "scene_1": [ShotVariation(shot_id="s1_1", shot_type="wide", focal_length="35mm", movement="static",
                                          description="Establishing forge")]
            },
            emotion_camera_map=[
                EmotionCameraMap(emotion="wonder", camera_style="slow push-in shallow DOF")
            ],
        )
        assert vb.story_hash == "abc123"
        assert len(vb.character_bibles) == 1
        assert vb.character_bibles[0].signature_items == ["boar-head hammer"]

    def test_character_bible_requires_name(self):
        with pytest.raises(Exception):
            CharacterBible(role="test", appearance="test", costume="test")

    def test_shot_variation_fields(self):
        shot = ShotVariation(shot_id="s1_2", shot_type="close-up", focal_length="85mm", movement="dutch angle")
        assert shot.focal_length == "85mm"
        assert shot.shot_type == "close-up"

    def test_visual_element_structure(self):
        ve = VisualElement(category="clothing", name="wool tunic",
                           description="Undyed wool tunic with leather reinforcements",
                           materials=["wool", "leather"], colors=["#8B7355", "#4A3728"])
        assert ve.category == "clothing"
        assert len(ve.colors) == 2

    def test_visual_elements_dict_structure(self):
        ved = VisualElementsDict(culture="viking", timeline="high_medieval")
        assert ved.culture == "viking"
        assert ved.generated_by == "llm"


class TestDirectorAgent:
    def test_agent_type(self):
        agent = DirectorAgent()
        assert agent.agent_type == "director"

    def test_execute_empty_story(self):
        agent = DirectorAgent()
        wo = WorkOrder(agent_type="director", input_data={"story": ""})
        result = asyncio.run(agent.execute(wo))
        assert result.success is False
        assert "No story text" in result.error_message


class TestProductionDesignerAgent:
    def test_agent_type(self):
        agent = ProductionDesignerAgent()
        assert agent.agent_type == "production_designer"


class TestArtDirectorAgent:
    def test_agent_type(self):
        agent = ArtDirectorAgent()
        assert agent.agent_type == "art_director"


class TestVisualElementsEngine:
    def test_total_items_count(self):
        data = {"clothing": [1, 2], "architecture": [], "artifact": [3]}
        assert total_items(data) == 3

    def test_bucket_material_map_coverage(self):
        for bucket in ["ancient", "medieval", "modern", "near_future", "space"]:
            assert bucket in BUCKET_MATERIAL_MAP
            assert len(BUCKET_MATERIAL_MAP[bucket]) >= 3

    def test_engine_initialization(self):
        engine = VisualElementsEngine()
        assert engine is not None

    def test_is_valid_hex(self):
        engine = VisualElementsEngine()
        assert engine._is_valid_hex("#2C1810") is True
        assert engine._is_valid_hex("#GGG") is False
        assert engine._is_valid_hex("blue") is False

    def test_has_stereotype_detection(self):
        engine = VisualElementsEngine()
        assert engine._has_stereotype("horned helmet savage") is True
        assert engine._has_stereotype("detailed wool tunic with bronze brooch") is False

    def test_merge_merges_correctly(self):
        engine = VisualElementsEngine()
        existing = {"clothing": [{"name": "wool tunic", "description": "test"}], "architecture": [],
                     "artifact": [], "lighting": [], "hairstyle": [], "color_palette": []}
        generated = {"clothing": [{"name": "leather bracers", "description": "test"}], "architecture": [],
                      "artifact": [], "lighting": [], "hairstyle": [], "color_palette": []}
        merged = engine._merge(existing, generated)
        assert len(merged["clothing"]) >= 1
