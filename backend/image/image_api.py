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
MODEL = "flux"
NOLOGO = True
SAFE = True
MAX_PROMPT_LENGTH = 800

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
        return abs(hash(combined)) % 9999

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
        width = CHARACTER_WIDTH if orientation == "portrait" else SETTING_WIDTH
        height = CHARACTER_HEIGHT if orientation == "portrait" else SETTING_HEIGHT
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
        variation_labels = ["full_body", "close_up", "action"]
        for i in range(min(variations, len(variation_labels))):
            vtype = variation_labels[i]
            suffix = f"_char_{character_name.lower().replace(' ', '_')}_{vtype}"
            seed = self.compute_seed(story_hash, suffix)
            orientation = "portrait" if vtype != "action" else "landscape"
            if vtype == "action":
                vprompt = f"{base_prompt}, dynamic action pose, cinematic medium shot"
            elif vtype == "close_up":
                vprompt = f"{base_prompt}, intimate close-up portrait, emotional expression, eyes visible, 85mm lens"
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
