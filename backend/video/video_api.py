import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional, List

import httpx

from config import CONFIG
from logger_config import setup_logger

logger = setup_logger("VideoAPI")

VIDEO_TIMEOUT = 600


class ImageConditioningInput:
    def __init__(self, url: str, frame_idx: int = 0, strength: float = 1.0):
        self.url = url
        self.frame_idx = frame_idx
        self.strength = strength


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
    async def generate(self, prompt: str,
                       images: Optional[List[ImageConditioningInput]] = None,
                       audio_prompt: Optional[str] = None,
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

    async def generate(self, prompt: str,
                       images: Optional[List[ImageConditioningInput]] = None,
                       audio_prompt: Optional[str] = None,
                       seed: int = 0, duration_s: int = 8) -> VideoClipResult:
        if not self.endpoint:
            return VideoClipResult(
                success=False, error="CloudGPU endpoint not configured. Set CLOUD_GPU_ENDPOINT in .env",
                source="cloud_gpu"
            )
        try:
            client = await self._get_client()
            body: dict = {
                "prompt": prompt,
                "seed": seed,
                "duration_s": duration_s,
            }
            if images:
                body["images"] = [
                    {"url": img.url, "frame_idx": img.frame_idx, "strength": img.strength}
                    for img in images
                ]
            if audio_prompt:
                body["audio_prompt"] = audio_prompt
                body["generate_audio"] = True

            resp = await client.post(
                f"{self.endpoint}/generate_clip",
                json=body,
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


class KenBurnsDegradation(VideoProvider):
    async def generate(self, prompt: str,
                       images: Optional[List[ImageConditioningInput]] = None,
                       audio_prompt: Optional[str] = None,
                       seed: int = 0, duration_s: int = 8) -> VideoClipResult:
        logger.warning(f"Ken Burns fallback for prompt: {prompt[:60]}...")
        ref_url = None
        if images:
            first = images[0]
            ref_url = first.url if isinstance(first, ImageConditioningInput) else str(first)
        return VideoClipResult(
            clip_url=ref_url,
            success=True,
            source="ken_burns",
        )
