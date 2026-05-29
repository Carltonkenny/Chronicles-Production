import pytest
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


# ─── SOLITARY ASTRONAUT — no signature items, futuristic ───

class TestSolitaryCharacter:
    @pytest.mark.asyncio
    async def test_character_designer_no_signature_items(self, monkeypatch):
        async def mock_llm(*args, **kwargs):
            return json.dumps({
                "height_cm": 178,
                "weight_kg": 75,
                "body_type": "lean, athletic, ~8% body fat from nutrient-paste diet",
                "skin_tone": "pale, UV-deprived #E8D5C4",
                "hair_color": "dark brown #2C1E16",
                "hair_style": "regulation buzz cut, slightly grown out",
                "eye_color": "gray-blue #7B8FA1",
                "face_shape": "angular, hollow cheeks, jaw tension",
                "build": "runner's physique, taut from zero-G treadmill",
                "distinguishing_features": "faint surgical scar at left temple — neural interface port",
                "voice_traits": "quiet, deliberate, long pauses between words",
                "turnaround_image_prompt": "Isolated astronaut in a worn EVA suit with carbon-scored patches. Four views on a studio gray backdrop. Front pose: standing, helmet under left arm, neutral floating stance. Back pose: thruster pack visible, patched oxygen line. Side profile: gaunt face, scar visible at temple. Action pose: reaching toward distant light, weightless. Height scale bar in centimeters on left. Photorealistic character turnaround sheet.",
            })

        monkeypatch.setattr("agents.character_designer.call_llm", mock_llm)
        from agents.character_designer import CharacterDesignerAgent
        from schemas import WorkOrder

        agent = CharacterDesignerAgent()
        wo = WorkOrder(
            agent_type="character_designer",
            input_data={
                "character_bible": {
                    "name": "Kai Chen",
                    "role": "Solo Astronaut",
                    "appearance": "Gaunt, hollow-eyed, regulation haircut",
                    "costume": "Worn EVA suit",
                    "signature_items": [],
                    "emotional_range": "profound loneliness, existential wonder",
                },
                "culture": "japanese",
                "timeline": "interplanetary_frontier",
                "theme": "identity",
                "visual_bible": {
                    "film_tone": "Meditative, vast, lonely",
                    "color_palette": {"primary": ["#0A0E27", "#1B2A4A"], "accent": ["#4FC3F7", "#FF6F00"]},
                },
            },
            story_hash="solitary_astro",
            priority=2,
        )
        result = await agent.execute(wo)
        assert result.success is True
        design = result.output_data.get("design", {})
        assert design.get("height_cm") == 178
        assert "astronaut" in design.get("turnaround_image_prompt", "").lower()

    @pytest.mark.asyncio
    async def test_prop_designer_futuristic_era(self, monkeypatch):
        def mock_get_ve(*args, **kwargs):
            return {
                "artifact": [
                    {"name": "plasma_torch", "description": "Handheld plasma cutting tool used for hull repairs", "materials": ["titanium", "ceramic"], "colors": ["#C0C0C0", "#FF4500"]},
                    {"name": "data_chip", "description": "Encrypted data storage crystalline wafer", "materials": ["silicon", "gold"], "colors": ["#000000", "#FFD700"]},
                    {"name": "neural_interface", "description": "Brain-computer connector implant", "materials": ["graphene", "platinum"], "colors": ["#333333", "#E5E4E2"]},
                ],
                "clothing": [
                    {"name": "eva_suit_liner", "description": "Temperature-regulated undergarment for spacesuit", "materials": ["merino", "graphene"], "colors": ["#1C1C1C"]},
                ],
            }

        monkeypatch.setattr("agents.prop_designer.get_visual_elements", mock_get_ve)
        from agents.prop_designer import PropDesignerAgent
        from schemas import WorkOrder

        agent = PropDesignerAgent()
        wo = WorkOrder(
            agent_type="prop_designer",
            input_data={"culture": "japanese", "timeline": "interplanetary_frontier", "visual_bible": {}},
            story_hash="solitary_astro",
            priority=3,
        )
        result = await agent.execute(wo)
        assert result.success is True
        props = result.output_data.get("props", [])
        assert len(props) >= 4
        prop_names = [p.get("name", "") for p in props]
        assert "Plasma Torch" in prop_names
        assert "Data Chip" in prop_names


# ─── ROMAN MERCHANT — ancient, many props ───

class TestRomanMerchant:
    def test_prop_type_classification(self):
        from agents.prop_designer import _classify_prop_type
        assert _classify_prop_type("bronze gladius", "short stabbing sword") == "weapon"
        assert _classify_prop_type("golden torc", "neck ring of office") == "jewelry"
        assert _classify_prop_type("war chariot", "two-wheeled battle vehicle") == "vehicle"
        assert _classify_prop_type("granite quern", "hand-operated grain mill") == "tool"
        assert _classify_prop_type("ritual staff", "ceremonial wooden staff") == "religious"
        assert _classify_prop_type("linen tunic", "simple body garment") == "accessory"
        assert _classify_prop_type("unknown trinket", "mysterious object") == "accessory"

    @pytest.mark.asyncio
    async def test_prop_designer_ancient_artifacts(self, monkeypatch):
        def mock_get_ve(*args, **kwargs):
            return {
                "artifact": [
                    {"name": "bronze_gladius", "description": "Short double-edged sword", "materials": ["bronze", "oak"], "colors": ["#8B4513", "#DAA520"]},
                    {"name": "terracotta_amphora", "description": "Two-handled storage jar for olive oil", "materials": ["terracotta", "slip"], "colors": ["#CC5500", "#8B0000"]},
                    {"name": "wax_tablet", "description": "Writing surface for trade records", "materials": ["beeswax", "beech"], "colors": ["#F5DEB3", "#8B4513"]},
                    {"name": "bronze_stylus", "description": "Pointed writing instrument", "materials": ["bronze"], "colors": ["#CD7F32"]},
                ],
                "clothing": [
                    {"name": "woolen_toga", "description": "Formal draped garment of Roman citizen", "materials": ["wool"], "colors": ["#FFFFF0"]},
                ],
            }

        monkeypatch.setattr("agents.prop_designer.get_visual_elements", mock_get_ve)
        from agents.prop_designer import PropDesignerAgent
        from schemas import WorkOrder

        agent = PropDesignerAgent()
        wo = WorkOrder(
            agent_type="prop_designer",
            input_data={
                "culture": "roman",
                "timeline": "classical_antiquity",
                "visual_bible": {
                    "character_bibles": [
                        {"name": "Marcus Varro", "appearance": "Roman merchant", "signature_items": ["bronze scales", "signet ring"]},
                    ],
                },
            },
            story_hash="roman_merchant",
            priority=3,
        )
        result = await agent.execute(wo)
        assert result.success is True
        props = result.output_data.get("props", [])
        assert len(props) >= 5
        names = [p.get("name", "") for p in props]
        assert "Bronze Gladius" in names
        assert "Bronze Scales" in names
        assert "Signet Ring" in names


# ─── VIKING BROTHERS — multi-character, dialogue ───

class TestVikingBrothers:
    @pytest.mark.asyncio
    async def test_writer_scene_with_dialogues(self, monkeypatch):
        async def mock_llm(*args, **kwargs):
            return json.dumps({
                "title": "The Longship's Bow",
                "setting": "A smoky Norse longhouse in winter, 890 AD",
                "characters": ["Bjorn Eriksson: elder brother, cautious chieftain", "Hakon Eriksson: younger brother, reckless warrior"],
                "story": "The longhouse fire crackled as Bjorn traced the coast on a worn deerskin map. Hakon paced behind him, axe restless in his grip. 'The monks at Lindisfarne grow fat on silver,' Hakon growled. Bjorn did not look up. 'And their king grows fat on Frankish steel. We've lost twelve men this season.' Hakon slammed the table. 'Then fight harder, brother. Glory does not come to those who count losses.' Bjorn finally met his eyes. 'I count lives, not losses. Father's last raid cost him thirty men and his sword arm.' Silence fell between them. Outside, a raven called. Hakon's jaw tightened. 'You are not father.' 'No.' Bjorn stood. 'But I am chieftain.' The fire popped, sending sparks spiraling into the smoke-blackened rafters.",
                "scenes": [
                    {"id": 1, "summary": "The brothers argue over a raid in the longhouse", "location": "Longhouse interior", "characters": ["Bjorn Eriksson", "Hakon Eriksson"], "emotional_beat": "tension", "narration_text": "Two brothers. One fire. A decision that would split their clan.", "duration_estimate": 12},
                    {"id": 2, "summary": "Hakon prepares his ship alone", "location": "Fjord docks at dawn", "characters": ["Hakon Eriksson"], "emotional_beat": "defiance", "narration_text": "", "duration_estimate": 8},
                ],
                "dialogues": {
                    "1": [
                        "Hakon Eriksson (impatient, sharp): 'The monks at Lindisfarne grow fat on silver.'",
                        "Bjorn Eriksson (measured, heavy): 'I count lives, not losses.'",
                        "Hakon Eriksson (bitter, low): 'You are not father.'",
                    ],
                    "2": [],
                },
            })

        monkeypatch.setattr("agents.writer_scene.call_llm", mock_llm)
        from agents.writer_scene import WriterSceneAgent
        from schemas import WorkOrder

        agent = WriterSceneAgent()
        wo = WorkOrder(
            agent_type="writer_scene",
            input_data={
                "blueprint": {
                    "title": "The Longship's Bow",
                    "plot_outline": "Two brothers argue over a raid",
                    "characters": ["Bjorn", "Hakon"],
                },
                "seed_idea": "Two brothers argue over leading the raid",
                "culture": "viking",
                "timeline": "early_medieval",
                "theme": "jealousy",
                "wiki_context": "Vikings raided Lindisfarne in 793 AD.",
            },
            story_hash="viking_bros",
            priority=2,
        )
        result = await agent.execute(wo)
        assert result.success is True
        story_data = result.output_data
        assert len(story_data.get("story", "").split()) > 100
        scenes = story_data.get("scenes", [])
        assert len(scenes) >= 2
        dialogues = story_data.get("dialogues", {})
        assert len(dialogues.get("1", [])) >= 2

    @pytest.mark.asyncio
    async def test_character_designer_with_full_bible(self, monkeypatch):
        async def mock_llm(*args, **kwargs):
            return json.dumps({
                "height_cm": 182,
                "weight_kg": 92,
                "body_type": "muscular, broad-shouldered, warrior's frame",
                "skin_tone": "weathered fair #D4A574, windburned cheeks",
                "hair_color": "dark blond #8B7355 with gray at temples",
                "hair_style": "shoulder-length, braided on one side, shaved on other",
                "eye_color": "ice blue #87CEEB",
                "face_shape": "square jaw, broken nose healed crooked, brow ridge prominent",
                "build": "barrel-chested, thick neck, arms scarred from shield work",
                "distinguishing_features": "three-finger ritual scar on left cheek, missing tip of right ear, runic tattoo around left bicep",
                "voice_traits": "gravelly baritone, commands attention, speaks with weight",
                "turnaround_image_prompt": "Character model sheet of Bjorn the Viking chieftain. Four views on a studio gray backdrop. LEFT: front standing pose,  182cm height scale bar on left labeled in cm and feet, full body showing wolf-pelt cloak and hammer amulet, arms slightly out. CENTER-LEFT: back view showing braided hair and cloak clasp. CENTER-RIGHT: profile view showing broken nose and missing ear tip. RIGHT: action pose holding bearded axe, battle stance. Photorealistic character turnaround sheet, 8K.",
            })

        monkeypatch.setattr("agents.character_designer.call_llm", mock_llm)
        from agents.character_designer import CharacterDesignerAgent
        from schemas import WorkOrder

        agent = CharacterDesignerAgent()
        wo = WorkOrder(
            agent_type="character_designer",
            input_data={
                "character_bible": {
                    "name": "Bjorn Eriksson",
                    "role": "Viking Chieftain",
                    "appearance": "Tall, battle-scarred, graying blond hair, ice-blue eyes",
                    "costume": "Wolf-pelt cloak, leather bracers, iron-studded belt",
                    "signature_items": ["bearded axe", "hammer amulet"],
                    "emotional_range": "stoic, explosive rage, deep love for his brother",
                },
                "culture": "viking",
                "timeline": "early_medieval",
                "theme": "jealousy",
                "visual_bible": {"film_tone": "Gritty, intimate, fire-lit", "color_palette": {"primary": ["#2B1B17", "#8B0000"], "accent": ["#DAA520", "#4682B4"]}},
            },
            story_hash="viking_bros",
            priority=2,
        )
        result = await agent.execute(wo)
        assert result.success is True
        design = result.output_data.get("design", {})
        assert design.get("height_cm") == 182
        assert design.get("weight_kg") == 92
        assert "scarred" in design.get("body_type", "").lower() or "warrior" in design.get("body_type", "").lower()
        tp = result.output_data.get("turnaround_prompt", "")
        assert "Bjorn" in tp or "front" in tp.lower()


# ─── COLOR GRADING ───

class TestColorGrading:
    def test_warm_palette_dark_tone(self):
        from utils.color_grade import compute_grading_spec
        spec = compute_grading_spec(
            {"primary": ["dark amber", "crimson"], "accent": ["gold"]},
            film_tone="dark, gritty, noir",
        )
        assert spec["temperature_offset"] > 0
        assert spec["contrast"] > 1.03
        assert spec["saturation"] < 1.0

    def test_cool_palette_bright_tone(self):
        from utils.color_grade import compute_grading_spec
        spec = compute_grading_spec(
            {"primary": ["navy blue", "steel"], "accent": ["ice cyan"]},
            film_tone="hopeful, epic adventure",
        )
        assert spec["temperature_offset"] < 0
        assert spec["contrast"] > 1.01
        assert spec["saturation"] > 1.0

    def test_empty_palette_defaults(self):
        from utils.color_grade import compute_grading_spec
        spec = compute_grading_spec({}, film_tone="", lighting_style="")
        assert spec["temperature_offset"] == 0
        assert spec["contrast"] > 1.0
        assert "vignette" in spec


# ─── SOUND DESIGNER — edge inputs ───

class TestSoundDesignerEdge:
    @pytest.mark.asyncio
    async def test_empty_scenes_graceful(self, monkeypatch):
        async def mock_llm(*args, **kwargs):
            return "{}"

        monkeypatch.setattr("agents.sound_designer.call_llm", mock_llm)
        from agents.sound_designer import SoundDesignerAgent
        from schemas import WorkOrder

        agent = SoundDesignerAgent()
        wo = WorkOrder(
            agent_type="sound_designer",
            input_data={"culture": "roman", "timeline": "classical_antiquity", "scenes": [], "characters": []},
            story_hash="empty_test",
            priority=3,
        )
        result = await agent.execute(wo)
        assert result.success is True
        assert result.output_data.get("audio_prompts", {}) == {}

    @pytest.mark.asyncio
    async def test_single_scene_minimal_prompt(self, monkeypatch):
        async def mock_llm(*args, **kwargs):
            return json.dumps({"1": "Roman forum ambience. Distant crowd murmur. Marble steps echoing."})

        monkeypatch.setattr("agents.sound_designer.call_llm", mock_llm)
        from agents.sound_designer import SoundDesignerAgent
        from schemas import WorkOrder

        agent = SoundDesignerAgent()
        wo = WorkOrder(
            agent_type="sound_designer",
            input_data={
                "culture": "roman",
                "timeline": "classical_antiquity",
                "scenes": [{"id": 1, "summary": "Entering the Senate", "location": "Roman Senate", "emotional_beat": "awe", "characters": ["Marcus"]}],
                "characters": [{"name": "Marcus", "role": "Senator"}],
            },
            story_hash="single_scene",
            priority=3,
        )
        result = await agent.execute(wo)
        assert result.success is True
        prompts = result.output_data.get("audio_prompts", {})
        assert "1" in prompts
        assert len(prompts["1"]) > 20


# ─── IMAGE SWARM — empty input ───

class TestImageSwarmEdge:
    @pytest.mark.asyncio
    async def test_empty_characters_and_scenes(self, monkeypatch):
        def mock_get_ve(*args, **kwargs):
            return {"artifact": [], "clothing": []}

        monkeypatch.setattr("agents.prop_designer.get_visual_elements", mock_get_ve)
        from agents.image_swarm_lead import ImageSwarmLead
        from schemas import WorkOrder

        agent = ImageSwarmLead()
        wo = WorkOrder(
            agent_type="image_swarm_lead",
            input_data={
                "culture": "egyptian",
                "timeline": "classical_antiquity",
                "theme": "memory",
                "characters": [],
                "scenes": [],
                "visual_bible": {},
            },
            story_hash="empty_swarm",
            priority=2,
        )
        result = await agent.execute(wo)
        assert result.success is True
        output = result.output_data
        assert output.get("total_count", -1) >= 0


# ─── VISUAL BIBLE ARCHITECT — minimal input ───

class TestVisualBibleArchitect:
    @pytest.mark.asyncio
    async def test_minimal_input_produces_vb(self, monkeypatch):
        async def mock_llm(*args, **kwargs):
            return json.dumps({
                "film_tone": "Mysterious, ancient, reverent",
                "color_palette": {"primary": ["#D4AF37", "#8B4513"], "accent": ["#2F4F4F", "#4682B4"]},
                "lighting_style": "Torch-lit interiors, harsh desert sun",
                "character_bibles": [{"name": "Nebet", "appearance": "Egyptian scribe", "costume": "Linen kalasiris", "signature_items": ["reed pen", "papyrus scroll"], "emotional_range": "curious, fearful", "voice_traits": "soft, precise"}],
                "location_descriptions": [{"name": "Temple of Thoth", "description": "limestone temple with hieroglyph-covered columns", "materials": ["limestone", "gold leaf"], "lighting": "oil lamp", "time_of_day": "midnight"}],
                "material_inventory": ["limestone", "gold leaf", "linen", "papyrus", "cedar"],
                "scene_props": {},
                "cultural_symbols": ["ankh", "scarab", "ibis"],
                "signature_item_placement": {},
                "motif_arc": "The reed pen writes the truth that papyrus keeps forever",
                "camera_language": "Slow, deliberate pans. Shallow focus on writing surfaces.",
            })

        def mock_get_ve(*args, **kwargs):
            return {"artifact": [], "clothing": [], "architecture": [], "lighting": [], "hairstyle": [], "color_palette": []}

        monkeypatch.setattr("agents.visual_bible_architect.call_llm", mock_llm)
        monkeypatch.setattr("agents.visual_bible_architect.get_visual_elements", mock_get_ve)
        from agents.visual_bible_architect import VisualBibleArchitect
        from schemas import WorkOrder

        agent = VisualBibleArchitect()
        wo = WorkOrder(
            agent_type="visual_bible_architect",
            input_data={
                "title": "The Last Scroll",
                "culture": "egyptian",
                "timeline": "classical_antiquity",
                "theme": "memory",
                "story": "Nebet the scribe records the final days of her temple.",
                "characters": ["Nebet: temple scribe"],
                "scenes": [{"id": 1, "summary": "Nebet writes by lamplight", "location": "Temple of Thoth", "emotional_beat": "wonder"}],
            },
            story_hash="last_scroll",
            priority=2,
        )
        result = await agent.execute(wo)
        assert result.success is True
        vb = result.output_data
        assert vb.get("film_tone")
        assert vb.get("character_bibles")
        assert len(vb.get("character_bibles", [])) >= 1


# ─── FULL PIPELINE SIMULATION — all agents in sequence ───

class TestFullPipelineEdge:
    @pytest.mark.asyncio
    async def test_japanese_ai_hegemony_obsession(self, monkeypatch):
        futuristic_props = {
            "artifact": [
                {"name": "data_blade", "description": "Concealed ceramic blade with encrypted data core", "materials": ["ceramic", "graphene"], "colors": ["#000000", "#00FFFF"]},
                {"name": "neural_dampener", "description": "Wrist-mounted EMP emitter to disable neural interfaces", "materials": ["titanium", "polymer"], "colors": ["#C0C0C0", "#FF0000"]},
            ],
            "clothing": [
                {"name": "adaptive_hardsuit", "description": "Smart-fabric armor that hardens on impact", "materials": ["carbon-fiber", "liquid-crystal"], "colors": ["#1A1A2E", "#E94560"]},
            ],
        }

        async def mock_llm(*args, **kwargs):
            prompt = str(kwargs.get("user", ""))
            system = str(kwargs.get("system", ""))
            if "character" in prompt.lower() and "height" in system.lower():
                return json.dumps({
                    "height_cm": 165,
                    "weight_kg": 58,
                    "body_type": "wiry, augmented, cybernetic spine implant visible",
                    "skin_tone": "pale olive #D4C5A9 with neon synth-skin patches",
                    "hair_color": "black with cyan fiber-optic strands #0A0A0A",
                    "hair_style": "asymmetric cut, partially shaved with data-port visible",
                    "eye_color": "augmented cyan #00FFFF, left eye has HUD overlay scarring",
                    "face_shape": "sharp, angular, high cheekbones",
                    "build": "runner's build, left arm fully prosthetic (carbon-fiber black)",
                    "distinguishing_features": "full left arm prosthetic, spine cybernetic nodes, neck data-port",
                    "voice_traits": "low, modulated, slight digital reverb",
                    "turnaround_image_prompt": "Hacker character model sheet. Four views. Front: full body with prosthetic arm visible, neon-lit suit. Back: spine implants. Side: augmented eye. Action: data-blade drawn. Height scale bar. Cyberpunk photorealistic.",
                })
            return "{}"

        def mock_get_ve(*args, **kwargs):
            return futuristic_props

        monkeypatch.setattr("agents.character_designer.call_llm", mock_llm)
        monkeypatch.setattr("agents.prop_designer.get_visual_elements", mock_get_ve)

        from agents.character_designer import CharacterDesignerAgent
        from agents.prop_designer import PropDesignerAgent
        from schemas import WorkOrder

        char_agent = CharacterDesignerAgent()
        char_result = await char_agent.execute(WorkOrder(
            agent_type="character_designer",
            input_data={
                "character_bible": {
                    "name": "Koharu",
                    "role": "Resistance Hacker",
                    "appearance": "Augmented eyes, prosthetic arm, wiry build",
                    "costume": "Adaptive carbon-fiber hardsuit, neon synth-patches",
                    "signature_items": ["data-blade", "neural dampener"],
                    "emotional_range": "obsessive focus, cold fury, hidden vulnerability",
                },
                "culture": "japanese",
                "timeline": "ai_hegemony",
                "theme": "obsession",
                "visual_bible": {"film_tone": "Neon-noir, oppressive, electric", "color_palette": {"primary": ["#1A1A2E", "#E94560"], "accent": ["#00FFFF", "#16213E"]}},
            },
            story_hash="neon_tokyo",
            priority=2,
        ))
        assert char_result.success
        design = char_result.output_data.get("design", {})
        assert design.get("height_cm") == 165
        assert "prosthetic" in str(design).lower() or "augmented" in str(design).lower()

        prop_agent = PropDesignerAgent()
        prop_result = await prop_agent.execute(WorkOrder(
            agent_type="prop_designer",
            input_data={
                "culture": "japanese",
                "timeline": "ai_hegemony",
                "visual_bible": {
                    "character_bibles": [{
                        "name": "Koharu",
                        "signature_items": ["data-blade", "neural dampener"],
                    }],
                },
            },
            story_hash="neon_tokyo",
            priority=3,
        ))
        assert prop_result.success
        props = prop_result.output_data.get("props", [])
        names = [p.get("name", "") for p in props]
        assert "Data-Blade" in names or "Data Blade" in names


# ─── EXTREME EDGE CASES ───

class TestExtremeEdgeCases:
    def test_sha256_deterministic_seed(self):
        from image.image_api import ImageAPIClient
        api = ImageAPIClient()
        s1 = api.compute_seed("same_hash_test", "")
        s2 = api.compute_seed("same_hash_test", "")
        s3 = api.compute_seed("different_hash", "")
        assert s1 == s2, "Same hash must produce same seed"
        assert s1 != s3, "Different hash must produce different seed"

    def test_max_characters_no_crash(self):
        from agents.prop_designer import PropDesignerAgent, _classify_prop_type
        assert _classify_prop_type("", "") == "accessory"
        assert _classify_prop_type("a" * 100, "b" * 200) == "accessory"

    def test_color_grade_all_tones(self):
        from utils.color_grade import compute_grading_spec
        tones = ["dark, gritty, noir", "bright, hopeful, epic", "tragic, somber", "heroic, vibrant", "intimate, romantic"]
        for tone in tones:
            spec = compute_grading_spec({}, film_tone=tone)
            assert "brightness" in spec
            assert "contrast" in spec
            assert isinstance(spec["vignette"], float)

    def test_empty_prop_pipeline_handles_none(self, monkeypatch):
        def mock_get_ve(*args, **kwargs):
            return {"artifact": [], "clothing": []}
        monkeypatch.setattr("agents.prop_designer.get_visual_elements", mock_get_ve)
        from agents.prop_designer import PropDesignerAgent
        from schemas import WorkOrder
        agent = PropDesignerAgent()
        wo = WorkOrder(agent_type="prop_designer", input_data={"culture": "unknown_culture", "timeline": "unknown_timeline", "visual_bible": {}}, story_hash="empty_props", priority=3)
        import asyncio
        result = asyncio.run(agent.execute(wo))
        assert result.success
        assert result.output_data.get("props", []) == []

    @pytest.mark.asyncio
    async def test_writer_scene_minimal_blueprint(self, monkeypatch):
        async def mock_llm(*args, **kwargs):
            import json
            return json.dumps({"title": "Minimal", "story": "A brief moment.", "scenes": [{"id": 1, "summary": "test", "location": "void", "characters": [], "emotional_beat": "neutral", "narration_text": "", "duration_estimate": 5}], "dialogues": {}})
        monkeypatch.setattr("agents.writer_scene.call_llm", mock_llm)
        from agents.writer_scene import WriterSceneAgent
        from schemas import WorkOrder
        agent = WriterSceneAgent()
        wo = WorkOrder(agent_type="writer_scene", input_data={"blueprint": {}, "seed_idea": "", "culture": "", "timeline": "", "theme": "", "wiki_context": ""}, story_hash="minimal", priority=2)
        result = await agent.execute(wo)
        assert result.success
        assert len(result.output_data.get("scenes", [])) == 1
        assert result.output_data["title"] == "Minimal"

    @pytest.mark.asyncio
    async def test_character_design_broken_llm_fallback(self, monkeypatch):
        async def mock_llm(*args, **kwargs):
            raise RuntimeError("LLM down")
        monkeypatch.setattr("agents.character_designer.call_llm", mock_llm)
        from agents.character_designer import CharacterDesignerAgent
        from schemas import WorkOrder
        agent = CharacterDesignerAgent()
        wo = WorkOrder(agent_type="character_designer", input_data={"character_bible": {"name": "Test"}, "culture": "viking", "timeline": "medieval", "theme": "loss", "visual_bible": {}}, story_hash="broken", priority=2)
        result = await agent.execute(wo)
        assert result.success
        design = result.output_data.get("design", {})
        assert design.get("height_cm") == 170
        assert design.get("turnaround_image_prompt") or result.output_data.get("turnaround_prompt")

    def test_all_schemas_importable(self):
        from schemas.image_result import ImageResult, ImageOutput, PropImageResult
        from schemas.props import PropDetail
        from schemas.enums import Culture, Timeline, Theme
        from schemas.work_order import WorkOrder, WorkResult
        assert len(list(Culture)) == 15
        assert len(list(Timeline)) == 15
        assert len(list(Theme)) == 15
        r = ImageResult(url="u", prompt="p", seed=1, variation="mugshot", source="test")
        assert r.variation == "mugshot"

    def test_video_prompt_crafter_all_variation_seeds(self, monkeypatch):
        import hashlib
        seeds = set()
        for i in range(100):
            s = int(hashlib.sha256(f"hash_test_scene_{i}".encode()).hexdigest(), 16) % 99999
            seeds.add(s)
        assert len(seeds) > 90, "Seeds should be well-distributed across 100 hashes"
