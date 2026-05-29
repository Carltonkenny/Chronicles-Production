import pytest
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from schemas.image_result import ImageResult, ImageOutput
from schemas import WorkOrder
from image.image_api import ImageAPIClient, SETTING_QUALITY, CHARACTER_QUALITY, SETTING_WIDTH, SETTING_HEIGHT, CHARACTER_WIDTH, CHARACTER_HEIGHT


class TestImageSchema:
    def test_image_result_creation(self):
        r = ImageResult(url="http://example.com/img.png", prompt="test", seed=42, variation="full_body", orientation="portrait", character="Bjorn")
        assert r.url == "http://example.com/img.png"
        assert r.seed == 42
        assert r.character == "Bjorn"
        assert r.variation == "full_body"

    def test_image_result_defaults(self):
        r = ImageResult(url="http://example.com/img.png", prompt="test", seed=0)
        assert r.variation == "full_body"
        assert r.orientation == "landscape"
        assert r.source == "generated"
        assert r.character is None

    def test_image_output_empty(self):
        o = ImageOutput(story_hash="abc123")
        assert o.total_count == 0
        assert len(o.portraits) == 0
        assert len(o.scenes) == 0

    def test_image_output_with_data(self):
        p = ImageResult(url="http://ex.com/p.png", prompt="portrait", seed=1, variation="close_up", orientation="portrait", character="Sigrid")
        s = ImageResult(url="http://ex.com/s.png", prompt="scene", seed=2, variation="scene_keyframe", orientation="landscape", scene_id="scene_1")
        o = ImageOutput(story_hash="abc", portraits=[p], scenes=[s], total_count=2, character_map={"Sigrid": [p.model_dump()]})
        assert o.total_count == 2
        assert o.character_map["Sigrid"][0]["seed"] == 1


class TestImageAPIClient:
    @pytest.mark.asyncio
    async def test_compute_seed_deterministic(self):
        api = ImageAPIClient()
        s1 = api.compute_seed("abc123", "_setting")
        s2 = api.compute_seed("abc123", "_setting")
        assert s1 == s2
        assert 0 <= s1 <= 9999

    def test_compute_seed_different_suffix(self):
        api = ImageAPIClient()
        s1 = api.compute_seed("abc123", "_char_bjorn")
        s2 = api.compute_seed("abc123", "_char_sigrid")
        assert s1 != s2

    def test_build_image_url_landscape(self):
        api = ImageAPIClient()
        url = api.build_image_url("test prompt", 42, "landscape")
        assert "width=1344" in url
        assert "height=768" in url
        assert "seed=42" in url
        assert "model=flux" in url
        assert "test%20prompt" in url

    def test_build_image_url_portrait(self):
        api = ImageAPIClient()
        url = api.build_image_url("close up portrait", 99, "portrait")
        assert "width=768" in url
        assert "height=1344" in url
        assert "seed=99" in url

    def test_sanitize_prompt(self):
        api = ImageAPIClient()
        clean = api.sanitize_prompt("**Bold** text; more_text \"quotes\"")
        assert "**" not in clean
        assert "__" not in clean
        assert '"' not in clean
        assert "'" not in clean

    def test_sanitize_prompt_truncates_long(self):
        api = ImageAPIClient()
        long = "word " * 500
        clean = api.sanitize_prompt(long)
        assert len(clean) <= 1200

    @pytest.mark.asyncio
    async def test_build_portrait_urls(self):
        api = ImageAPIClient()
        results = await api.build_portrait_urls("abc123", "Bjorn", "a viking warrior", variations=3)
        assert len(results) == 3
        labels = [r["variation"] for r in results]
        assert "full_body" in labels
        assert "close_up" in labels
        assert "action" in labels
        for r in results:
            assert "seed=" in r["url"]
            assert r["seed"] > 0

    @pytest.mark.asyncio
    async def test_build_portrait_urls_deterministic(self):
        api = ImageAPIClient()
        r1 = await api.build_portrait_urls("abc123", "Bjorn", "prompt", variations=1)
        r2 = await api.build_portrait_urls("abc123", "Bjorn", "prompt", variations=1)
        assert r1[0]["seed"] == r2[0]["seed"]
        assert r1[0]["url"] == r2[0]["url"]

    @pytest.mark.asyncio
    async def test_build_scene_url(self):
        api = ImageAPIClient()
        result = await api.build_scene_url("abc123", "scene_2", "a forge interior")
        assert result["scene_id"] == "scene_2"
        assert result["orientation"] == "landscape"
        assert "seed=" in result["url"]

    @pytest.mark.asyncio
    async def test_build_scene_url_deterministic(self):
        api = ImageAPIClient()
        r1 = await api.build_scene_url("abc123", "scene_2", "a forge interior")
        r2 = await api.build_scene_url("abc123", "scene_2", "a forge interior")
        assert r1["seed"] == r2["seed"]

    def test_quality_strings_present(self):
        assert "photorealistic" in SETTING_QUALITY
        assert "cinematic" in SETTING_QUALITY
        assert "photorealistic" in CHARACTER_QUALITY
        assert "shallow depth of field" in CHARACTER_QUALITY

    def test_dimensions_match(self):
        assert SETTING_WIDTH > SETTING_HEIGHT
        assert CHARACTER_WIDTH < CHARACTER_HEIGHT


class TestAgentSwarm:
    @pytest.mark.asyncio
    async def test_character_portrait_gen_requires_all_variations(self):
        from image.image_api import ImageAPIClient
        api = ImageAPIClient()
        results = await api.build_portrait_urls("test_hash", "Ragnar", "Norse warrior with steel-gray eyes", variations=3)
        assert len(results) == 3
        assert all(r["url"].startswith("https://") for r in results)

    @pytest.mark.asyncio
    async def test_different_characters_different_seeds(self):
        api = ImageAPIClient()
        r1 = await api.build_portrait_urls("hash1", "Bjorn", "smith", variations=1)
        r2 = await api.build_portrait_urls("hash1", "Sigrid", "wife", variations=1)
        assert r1[0]["seed"] != r2[0]["seed"]

    @pytest.mark.asyncio
    async def test_same_hash_same_images(self):
        api = ImageAPIClient()
        r1 = await api.build_scene_url("ABC", "scene_1", "test prompt")
        r2 = await api.build_scene_url("ABC", "scene_1", "test prompt")
        assert r1["url"] == r2["url"]
        assert r1["seed"] == r2["seed"]

    def test_image_output_model_validation(self):
        img = ImageResult(url="http://ex.com/img.png", prompt="portrait", seed=123, variation="action", orientation="landscape", character="Bjorn")
        dumped = img.model_dump()
        assert dumped["url"] == "http://ex.com/img.png"
        assert dumped["seed"] == 123
        assert dumped["character"] == "Bjorn"

    def test_image_output_aggregation(self):
        portraits = [
            ImageResult(url=f"http://ex.com/char{i}.png", prompt=f"portrait{i}", seed=i, variation="full_body", orientation="portrait", character="Bjorn")
            for i in range(3)
        ]
        scenes = [
            ImageResult(url=f"http://ex.com/scene{i}.png", prompt=f"scene{i}", seed=i+10, variation="scene_keyframe", orientation="landscape", scene_id=f"scene_{i}")
            for i in range(7)
        ]
        output = ImageOutput(
            story_hash="test_hash",
            portraits=portraits,
            scenes=scenes,
            total_count=len(portraits) + len(scenes),
        )
        assert output.total_count == 10
        assert len(output.portraits) == 3
        assert len(output.scenes) == 7


class TestEdgeCases:
    def test_empty_prompt_sanitized(self):
        api = ImageAPIClient()
        assert api.sanitize_prompt("") == ""

    def test_special_chars_in_prompt(self):
        api = ImageAPIClient()
        inp = 'Test "with" quotes; semi_colons; underscores __ and **bold**'
        clean = api.sanitize_prompt(inp)
        assert '"' not in clean
        assert ";" not in clean
        assert "**" not in clean

    def test_seed_zero_hash(self):
        api = ImageAPIClient()
        seed = api.compute_seed("", "")
        assert 0 <= seed <= 9999

    @pytest.mark.asyncio
    async def test_portrait_urls_same_hash_diff_variations(self):
        api = ImageAPIClient()
        results = await api.build_portrait_urls("hash", "Char", "desc", variations=3)
        seeds = [r["seed"] for r in results]
        assert len(set(seeds)) == 3

    @pytest.mark.asyncio
    async def test_scene_url_unique_per_hash(self):
        api = ImageAPIClient()
        r1 = await api.build_scene_url("hash_x", "scene_1", "desc")
        r2 = await api.build_scene_url("hash_y", "scene_1", "desc")
        assert r1["seed"] != r2["seed"]
