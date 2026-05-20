import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional, List
from urllib.parse import quote

import httpx

from config import CONFIG
from logger_config import setup_logger

logger = setup_logger("VideoAPI")

VIDEO_TIMEOUT = 600
POLLINATIONS_VIDEO_URL = "https://gen.pollinations.ai/video"


class VideoClipResult:
    def __init__(self, clip_bytes: Optional[bytes] = None, clip_url: Optional[str] = None,
                 success: bool = True, error: Optional[str] = None,
                 source: str = "unknown"):
        self.clip_bytes = clip_bytes
        self.clip_url = clip_url
        self.success = success
        self.error = error
        self.source = source


class VideoProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, reference_image_url: Optional[str] = None,
                       seed: int = 0, duration_s: int = 8) -> VideoClipResult:
        pass

    async def close(self):
        pass


class CloudGPUProvider(VideoProvider):
    def __init__(self, endpoint: str = "", api_key: str = ""):
        self.endpoint = endpoint or CONFIG.CLOUD_GPU_ENDPOINT
        self.api_key = api_key or CONFIG.CLOUD_GPU_API_KEY
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            headers = {"X-API-Key": self.api_key} if self.api_key else {}
            self._client = httpx.AsyncClient(
                headers=headers, timeout=VIDEO_TIMEOUT
            )
        return self._client

    async def generate(self, prompt: str, reference_image_url: Optional[str] = None,
                       seed: int = 0, duration_s: int = 8) -> VideoClipResult:
        if not self.endpoint:
            return VideoClipResult(
                success=False, error="CloudGPU endpoint not configured",
                source="cloud_gpu"
            )
        try:
            client = await self._get_client()
            resp = await client.post(
                f"{self.endpoint}/generate_clip",
                json={
                    "prompt": prompt,
                    "reference_image_url": reference_image_url,
                    "seed": seed,
                    "duration_s": duration_s,
                },
            )
            if resp.status_code == 200:
                logger.info(f"CloudGPU generated clip ({len(resp.content)} bytes) in {resp.elapsed:.1f}s")
                return VideoClipResult(
                    clip_bytes=resp.content, success=True,
                    source="cloud_gpu"
                )
            return VideoClipResult(
                success=False,
                error=f"CloudGPU returned {resp.status_code}: {resp.text[:200]}",
                source="cloud_gpu"
            )
        except httpx.HTTPError as e:
            logger.warning(f"CloudGPU HTTP error: {e}")
            return VideoClipResult(success=False, error=str(e), source="cloud_gpu")
        except asyncio.TimeoutError:
            logger.warning("CloudGPU timed out")
            return VideoClipResult(success=False, error="timeout", source="cloud_gpu")

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None


class PollinationsProvider(VideoProvider):
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client

    def _build_url(self, prompt: str, seed: int) -> str:
        clean = prompt.replace("**", "").replace("__", "")
        clean = clean.replace('"', "").replace("'", "")
        import re as _re
        clean = _re.sub(r"\s+", " ", clean).strip()
        if len(clean) > 500:
            clean = clean[:500].rsplit(" ", 1)[0]
        encoded = quote(clean, safe="")
        api_key = CONFIG.POLLINATIONS_API_KEY
        url = f"{POLLINATIONS_VIDEO_URL}/{encoded}?seed={seed}&model=flux"
        if api_key:
            url += f"&key={api_key}"
        return url

    async def generate(self, prompt: str, reference_image_url: Optional[str] = None,
                       seed: int = 0, duration_s: int = 8) -> VideoClipResult:
        try:
            url = self._build_url(prompt, seed)
            client = await self._get_client()
            resp = await client.get(url, follow_redirects=True)
            if resp.status_code == 200 and len(resp.content) > 1000:
                logger.info(f"Pollinations generated clip ({len(resp.content)} bytes)")
                return VideoClipResult(
                    clip_url=url, clip_bytes=resp.content,
                    success=True, source="pollinations"
                )
            return VideoClipResult(
                success=False,
                error=f"Pollinations returned {resp.status_code} ({len(resp.content)} bytes)",
                source="pollinations"
            )
        except httpx.HTTPError as e:
            logger.warning(f"Pollinations video error: {e}")
            return VideoClipResult(success=False, error=str(e), source="pollinations")

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None


class KenBurnsDegradation(VideoProvider):
    async def generate(self, prompt: str, reference_image_url: Optional[str] = None,
                       seed: int = 0, duration_s: int = 8) -> VideoClipResult:
        logger.warning(f"Ken Burns fallback for prompt: {prompt[:60]}...")
        return VideoClipResult(
            clip_url=reference_image_url,
            success=True,
            source="ken_burns",
        )
