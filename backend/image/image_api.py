import hashlib
import asyncio
import re
from typing import Optional, List
from urllib.parse import quote

import httpx

from config import CONFIG
from logger_config import setup_logger

logger = setup_logger("ImageAPI")

SETTING_WIDTH = 1344
SETTING_HEIGHT = 768
CHARACTER_WIDTH = 768
CHARACTER_HEIGHT = 1344
SQUARE_SIZE = 1024
MODEL = "flux"
NOLOGO = True
SAFE = True
MAX_PROMPT_LENGTH = 1200

SETTING_QUALITY = (
    "cinematic wide-angle photograph, anamorphic lens, "
    "golden hour lighting, detailed textures, photorealistic, "
    "atmospheric haze, color grading like a historical epic film, "
    "8K resolution, no text, no watermark, no frame"
)

CHARACTER_QUALITY = (
    "hyperrealistic portrait photograph, 85mm lens, shallow depth of field, "
    "studio lighting with warm rim light, sharp focus on face, "
    "detailed skin texture, photorealistic, 8K resolution, "
    "no text, no watermark, no cartoon, no anime, no deformed features"
)


class ImageAPIClient:
    BASE_URL = "https://gen.pollinations.ai/image"

    def __init__(self, semaphore_limit: int = 8):
        self._semaphore = asyncio.Semaphore(semaphore_limit)
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    def compute_seed(self, story_hash: str, suffix: str = "") -> int:
        combined = f"{story_hash}{suffix}"
        digest = hashlib.sha256(combined.encode()).hexdigest()
        return int(digest, 16) % 9999

    @staticmethod
    def sanitize_prompt(prompt: str) -> str:
        prompt = prompt.replace("**", "").replace("__", "")
        prompt = prompt.replace("_", " ").replace(";", ",")
        prompt = prompt.replace('"', "").replace("'", "")
        prompt = re.sub(r"\s+", " ", prompt).strip()
        if len(prompt) > MAX_PROMPT_LENGTH:
            prompt = prompt[:MAX_PROMPT_LENGTH].rsplit(" ", 1)[0]
        return prompt

    def build_image_url(
        self, prompt: str, seed: int, orientation: str = "landscape"
    ) -> str:
        clean = self.sanitize_prompt(prompt)
        encoded = quote(clean, safe="")
        if orientation == "portrait":
            width, height = CHARACTER_WIDTH, CHARACTER_HEIGHT
        elif orientation == "square":
            width = height = SQUARE_SIZE
        else:
            width, height = SETTING_WIDTH, SETTING_HEIGHT
        api_key = CONFIG.POLLINATIONS_API_KEY
        url = (
            f"{self.BASE_URL}/{encoded}"
            f"?width={width}&height={height}"
            f"&model={MODEL}"
            f"&nologo={str(NOLOGO).lower()}"
            f"&safe={str(SAFE).lower()}"
            f"&seed={seed}"
        )
        if api_key:
            url += f"&key={api_key}"
        return url

    async def download_image(self, url: str) -> Optional[bytes]:
        async with self._semaphore:
            try:
                client = await self._get_client()
                resp = await client.get(url, follow_redirects=True, timeout=20.0)
                if resp.status_code == 200:
                    logger.debug(f"Downloaded image ({len(resp.content)} bytes): {url[:60]}...")
                    return resp.content
                logger.warning(f"Image download returned {resp.status_code}: {url[:60]}...")
                return None
            except (httpx.HTTPError, asyncio.TimeoutError) as e:
                logger.warning(f"Image download failed: {e}")
                return None

    async def build_portrait_urls(
        self, story_hash: str, character_name: str, base_prompt: str, variations: int = 3
    ) -> List[dict]:
        results = []
        variation_labels = ["full_body", "close_up", "action", "mugshot", "physique_chart", "feature_closeup"]
        for i in range(min(variations, len(variation_labels))):
            vtype = variation_labels[i]
            suffix = f"_char_{character_name.lower().replace(' ', '_')}_{vtype}"
            seed = self.compute_seed(story_hash, suffix)
            if vtype in ("full_body", "close_up", "mugshot", "physique_chart", "feature_closeup"):
                orientation = "portrait"
            elif vtype == "character_sheet":
                orientation = "square"
            else:
                orientation = "landscape"
            if vtype == "close_up":
                vprompt = f"{base_prompt}, intimate close-up portrait, emotional expression, eyes visible, 85mm lens"
            elif vtype == "mugshot":
                vprompt = f"{base_prompt}, front-facing identification photograph, neutral expression, even lighting, plain background, reference photo style"
            elif vtype == "physique_chart":
                vprompt = f"{base_prompt}, full body against measurement scale with height markings in feet and metric, anatomical reference pose, clinical lighting, museum archive style"
            elif vtype == "feature_closeup":
                vprompt = f"{base_prompt}, extreme close-up of distinguishing features, macro photography, sharp detail on defining characteristics, medical illustration quality"
            elif vtype == "action":
                vprompt = f"{base_prompt}, dynamic action pose, cinematic medium shot"
            else:
                vprompt = f"{base_prompt}, full body standing pose, shows complete costume and signature items, neutral expression"
            url = self.build_image_url(vprompt, seed, orientation)
            results.append({
                "url": url,
                "prompt": vprompt,
                "seed": seed,
                "variation": vtype,
                "orientation": orientation,
            })
        return results

    async def build_turnaround_url(
        self, story_hash: str, character_name: str, prompt: str
    ) -> dict:
        suffix = f"_char_{character_name.lower().replace(' ', '_')}_turnaround"
        seed = self.compute_seed(story_hash, suffix)
        url = self.build_image_url(prompt, seed, "landscape")
        return {
            "url": url,
            "prompt": prompt,
            "seed": seed,
            "variation": "turnaround_sheet",
            "orientation": "landscape",
        }

    async def build_character_sheet_url(
        self, story_hash: str, character_name: str, prompt: str
    ) -> dict:
        suffix = f"_char_{character_name.lower().replace(' ', '_')}_sheet"
        seed = self.compute_seed(story_hash, suffix)
        url = self.build_image_url(prompt, seed, "square")
        return {
            "url": url,
            "prompt": prompt,
            "seed": seed,
            "variation": "character_sheet",
            "orientation": "square",
        }

    async def build_scene_url(
        self, story_hash: str, scene_id: str, base_prompt: str
    ) -> dict:
        suffix = f"_scene_{scene_id}"
        seed = self.compute_seed(story_hash, suffix)
        url = self.build_image_url(base_prompt, seed, "landscape")
        return {
            "url": url,
            "prompt": base_prompt,
            "seed": seed,
            "scene_id": scene_id,
            "orientation": "landscape",
        }

    async def build_scene_variation_urls(
        self, story_hash: str, scene_id: str, base_prompt: str
    ) -> List[dict]:
        variations = [
            ("establishing_shot", "wide establishing shot, full location visible, architecture and environment emphasized, cinematic landscape"),
            ("action_shot", "medium action shot, characters in motion, dynamic composition, the main beat of the scene"),
            ("emotional_closeup", "tight emotional shot, close-up on key character expression, shallow depth of field, intimate framing"),
            ("world_detail", "detail shot of environment or prop, texture and atmosphere, world-building visual, macro or medium focus"),
        ]
        results = []
        for vtype, v_suffix in variations:
            suffix = f"_scene_{scene_id}_{vtype}"
            seed = self.compute_seed(story_hash, suffix)
            vprompt = f"{base_prompt}, {v_suffix}"
            url = self.build_image_url(vprompt, seed, "landscape")
            results.append({
                "url": url,
                "prompt": vprompt,
                "seed": seed,
                "variation": vtype,
                "scene_id": scene_id,
                "orientation": "landscape",
            })
        return results

    async def download_images_batch(self, items: List[dict]) -> List[dict]:
        tasks = []
        for item in items:
            tasks.append(self._download_single(item))
        results = await asyncio.gather(*tasks)
        return [r for r in results if r is not None]

    async def _download_single(self, item: dict) -> Optional[dict]:
        data = await self.download_image(item["url"])
        if data:
            item["bytes"] = data
        return item
