import time
import json
import logging
from collections import OrderedDict
from typing import Optional

from config import CONFIG

logger = logging.getLogger("chronicles-cache")

try:
    import redis.asyncio as redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False
    redis = None

STORY_CACHE: OrderedDict[str, dict] = OrderedDict()
MAX_CACHE_SIZE = 50

_redis: "redis.Redis | None" = None


async def _get_redis():
    global _redis
    if not HAS_REDIS:
        return None
    if _redis is not None:
        return _redis
    try:
        _redis = redis.from_url(CONFIG.REDIS_URL, decode_responses=True, socket_connect_timeout=2)
        await _redis.ping()
        logger.info(f"Redis connected: {CONFIG.REDIS_URL}")
        return _redis
    except Exception as e:
        logger.warning(f"Redis unavailable ({e}), using in-memory fallback")
        _redis = None
        return None


async def cache_story(story_hash: str, story_data: dict, metadata: dict) -> None:
    entry = {
        "story_data": story_data,
        "metadata": metadata,
        "visuals": None,
        "created_at": time.time(),
    }
    r = await _get_redis()
    if r:
        try:
            await r.setex(
                f"story:{story_hash}",
                30 * 24 * 3600,
                json.dumps(entry, default=str),
            )
            logger.debug(f"Redis cached: story:{story_hash[:8]}")
        except Exception as e:
            logger.warning(f"Redis set failed: {e}")
    STORY_CACHE[story_hash] = entry
    while len(STORY_CACHE) > MAX_CACHE_SIZE:
        STORY_CACHE.popitem(last=False)
    logger.info(f"Story cached: {story_hash[:8]}... ({len(STORY_CACHE)} in memory)")


async def get_cached_story(story_hash: str) -> Optional[dict]:
    r = await _get_redis()
    if r:
        try:
            raw = await r.get(f"story:{story_hash}")
            if raw:
                logger.debug(f"Redis hit: story:{story_hash[:8]}")
                return json.loads(raw)
        except Exception as e:
            logger.warning(f"Redis get failed: {e}")
    entry = STORY_CACHE.get(story_hash)
    if entry:
        STORY_CACHE.move_to_end(story_hash)
        return entry
    return None


async def cache_visuals(story_hash: str, visuals: dict) -> None:
    r = await _get_redis()
    if r:
        try:
            raw = await r.get(f"story:{story_hash}")
            if raw:
                entry = json.loads(raw)
                entry["visuals"] = visuals
                await r.setex(
                    f"story:{story_hash}",
                    30 * 24 * 3600,
                    json.dumps(entry, default=str),
                )
        except Exception as e:
            logger.warning(f"Redis visuals update failed: {e}")
    entry = STORY_CACHE.get(story_hash)
    if entry:
        entry["visuals"] = visuals
        logger.debug(f"Visuals cached for story {story_hash[:8]}...")


async def warm_cache(cultures: list[str], timelines: list[str]) -> None:
    r = await _get_redis()
    if not r:
        return
    from utils.wiki_context import get_visual_elements
    for culture in cultures:
        for timeline in timelines:
            key = f"visual:{culture}:{timeline}"
            try:
                existing = await r.get(key)
                if existing:
                    continue
                data = get_visual_elements(culture, timeline)
                await r.setex(key, 7 * 24 * 3600, json.dumps(data, default=str))
            except Exception:
                pass
    logger.info("Cache warm complete")
