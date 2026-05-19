import logging
import sys
import hashlib
import asyncio
import anyio
import json
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError, BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from chain import generate_story, detect_mode
from schemas import (
    StoryRequest, StoryOutput, StoryGenerationRequest,
    StoryGenerationResponse, Culture, Timeline, Theme
)
from config import CONFIG
from audio import get_voice_for_culture
from audio.edge_tts_service import edge_tts_service
from tasks import generate_audio_background, get_audio_status
from cache import cache_story, get_cached_story, cache_visuals
from utils.wiki_context import get_culture_fallback_data, audit_fallback_coverage, get_wikipedia_summary
from agents.showrunner import ShowrunnerAgent, ProgressEvent
from image import image_api
from logger_config import api_logger as logger

limiter = Limiter(key_func=get_remote_address, default_limits=["100/hour"])

CULTURE_OVERRIDES = {
    "ancient_greek": "Ancient Greece",
    "east_india_company": "East India Company Era",
    "tang_dynasty": "Tang Dynasty China",
    "mali_empire": "Mali Empire",
    "swahili_coast": "Swahili Coast",
}
TIMELINE_OVERRIDES = {
    "post_ww": "Post World War Era",
    "age_of_conflict": "Age of Conflict",
    "classical_antiquity": "Classical Antiquity",
    "age_of_exploration": "Age of Exploration",
}

HISTORICAL_CULTURES = [
    Culture.ROMAN,
    Culture.EGYPTIAN,
    Culture.VIKING,
    Culture.JAPANESE,
    Culture.AZTEC,
    Culture.MAURYAN,
    Culture.CHOLA,
    Culture.MALI_EMPIRE,
    Culture.SWAHILI_COAST,
    Culture.YORUBA,
    Culture.MAYA,
]

MODERN_IDEOLOGICAL_CULTURES = [
    Culture.NAZI_GERMANY,
    Culture.SOVIET_UNION,
    Culture.BRITISH_EMPIRE,
    Culture.SPANISH_EMPIRE,
]

TIMELINE_GROUPS = {
    "Prehistory & Ancient": [
        Timeline.PALEOLITHIC,
        Timeline.EARLY_BRONZE_AGE,
        Timeline.CLASSICAL_ANTIQUITY,
    ],
    "Medieval & Early Modern": [
        Timeline.EARLY_MEDIEVAL,
        Timeline.HIGH_MEDIEVAL,
        Timeline.AGE_OF_EXPLORATION,
    ],
    "Modern": [
        Timeline.WORLD_WAR_ERA,
        Timeline.COLD_WAR,
        Timeline.GLOBALIZATION,
    ],
    "Contemporary": [
        Timeline.POLARIZATION_ERA,
    ],
    "Near Future": [
        Timeline.AI_HEGEMONY,
        Timeline.CLIMATE_MIGRATION,
    ],
    "Collapse": [
        Timeline.SYSTEMIC_COLLAPSE,
        Timeline.POST_COLLAPSE_TRIBAL,
    ],
    "Extreme Scale": [
        Timeline.INTERPLANETARY_FRONTIER,
    ],
}

THEME_GROUPS = {
    "Core": [
        Theme.AMBITION,
        Theme.BETRAYAL,
        Theme.LOSS,
        Theme.REDEMPTION,
        Theme.DISCOVERY,
    ],
    "Love & Desire": [
        Theme.FORBIDDEN_LOVE,
        Theme.JEALOUSY,
    ],
    "Power & Morality": [
        Theme.CORRUPTION,
        Theme.JUSTICE,
    ],
    "Psychological": [
        Theme.OBSESSION,
        Theme.DECEPTION,
    ],
    "Survival & Resistance": [
        Theme.SURVIVAL,
    ],
    "Identity & Epistemic": [
        Theme.IDENTITY,
        Theme.TRUTH,
        Theme.MEMORY,
    ],
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Chronicles Production API...")
    logger.info(f"Model: {CONFIG.POLLINATIONS_MODEL}")
    logger.info(f"LLM Provider: {CONFIG.LLM_PROVIDER}")
    logger.info(f"Audio: Edge TTS ({'available' if edge_tts_service.available else 'unavailable'})")

    selected_cultures = [c.value for c in (HISTORICAL_CULTURES + MODERN_IDEOLOGICAL_CULTURES)]
    selected_timelines = [t.value for group in TIMELINE_GROUPS.values() for t in group]
    selected_themes = [th.value for group in THEME_GROUPS.values() for th in group]
    audit = audit_fallback_coverage(selected_cultures, selected_timelines, selected_themes)
    logger.info(
        f"Fallback coverage: missing={len(audit['missing'])}, empty_text={len(audit['empty_text'])}"
    )

    yield

    logger.info("Shutting down Chronicles Production API...")


app = FastAPI(
    title="Chronicles Production API",
    description="AI-native film studio - generate complete short films",
    version="4.0.0",
    lifespan=lifespan
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except Exception:
    pass


@app.get("/", methods=["GET", "HEAD"])
async def root():
    return {
        "status": "healthy",
        "service": "Chronicles Production",
        "version": "4.0.0",
        "endpoints": {
            "health": "GET /",
            "options": "GET /options",
            "generate_story": "POST /generate-story"
        }
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "model": CONFIG.POLLINATIONS_MODEL,
        "api_configured": bool(CONFIG.POLLINATIONS_API_KEY),
        "rate_limit_tier": "anonymous" if not CONFIG.POLLINATIONS_API_KEY else "authenticated"
    }


@app.get("/options")
async def get_options():
    return {
        "cultures": {
            "Historical": [
                {"value": c.value, "label": CULTURE_OVERRIDES.get(c.value, c.value.replace("_", " ").title())}
                for c in HISTORICAL_CULTURES
            ],
            "Modern / Ideological": [
                {"value": c.value, "label": CULTURE_OVERRIDES.get(c.value, c.value.replace("_", " ").title())}
                for c in MODERN_IDEOLOGICAL_CULTURES
            ]
        },
        "timelines": {
            group: [
                {"value": t.value, "label": TIMELINE_OVERRIDES.get(t.value, t.value.replace("_", " ").title())}
                for t in timelines
            ]
            for group, timelines in TIMELINE_GROUPS.items()
        },
        "themes": {
            group: [
                {"value": th.value, "label": th.value.replace("_", " ").title()}
                for th in themes
            ]
            for group, themes in THEME_GROUPS.items()
        }
    }


STORY_GENERATION_LIMIT = anyio.CapacityLimiter(3)


@app.post("/generate-story", response_model=StoryGenerationResponse)
async def create_story(request: StoryGenerationRequest):
    try:
        culture_enum = Culture(request.culture.lower())
        timeline_enum = Timeline(request.timeline.lower())
        theme_enum = Theme(request.theme.lower())

    except ValueError as e:
        logger.warning(f"Invalid parameter in request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid parameter. Use /options to see valid choices. Error: {str(e)}"
        )

    try:
        story_request = StoryRequest(
            seed_idea=request.seed_idea,
            culture=culture_enum,
            timeline=timeline_enum,
            theme=theme_enum
        )

        logger.info(
            f"Generating story: culture={culture_enum.value}, "
            f"timeline={timeline_enum.value}, theme={theme_enum.value}"
        )

        async with STORY_GENERATION_LIMIT:
            result: StoryOutput = await generate_story(story_request)

        story_hash = hashlib.sha256(
            f"{result.story}:{get_voice_for_culture(culture_enum.value)}".encode()
        ).hexdigest()[:16]

        story_data = {
            "title": result.title, "setting": result.setting,
            "characters": result.characters, "story": result.story,
            "theme_reflection": result.theme_reflection,
        }

        fallback_data = get_culture_fallback_data(culture_enum.value)

        response = StoryGenerationResponse(
            success=True,
            title=result.title,
            setting=result.setting,
            characters=result.characters,
            story=result.story,
            theme_reflection=result.theme_reflection,
            stereotypes_flagged=result.stereotypes_flagged,
            word_count=len(result.story.split()),
            metadata={
                "culture": culture_enum.value,
                "timeline": timeline_enum.value,
                "theme": theme_enum.value,
                "culture_display": CULTURE_OVERRIDES.get(culture_enum.value, culture_enum.value.replace("_", " ").title()),
                "timeline_display": TIMELINE_OVERRIDES.get(timeline_enum.value, timeline_enum.value.replace("_", " ").title()),
                "theme_display": theme_enum.value.capitalize(),
                "stereotype_severity": "clean" if not result.stereotypes_flagged else ("warning" if len(result.stereotypes_flagged) <= 2 else "review"),
                "story_hash": story_hash,
                "audio_ready": False,

                "culture_fallback": fallback_data.get("fallback_text", ""),
                "culture_traps": fallback_data.get("traps", []),
                "culture_redirects": fallback_data.get("redirects", []),

                "validation": {
                    "seed_incorporated": result.validation_seed,
                    "theme_clear": result.validation_theme,
                    "quality_score": (result.validation_seed + result.validation_theme) / 2
                }
            }
        )

        logger.info(f"Story generated: {result.title} ({response.word_count} words)")

        cache_story(story_hash, story_data, response.metadata)

        return response

    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation error: {str(e)}"
        )

    except (TimeoutError, RuntimeError) as e:
        logger.error(f"Story generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Story generation failed: {str(e)}"
        )

    except Exception as e:
        logger.exception(f"Unexpected error during story generation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.post("/generate-film")
@limiter.limit("10/hour")
async def generate_film(fastapi_request: Request, body: StoryGenerationRequest):
    try:
        culture_enum = Culture(body.culture.lower())
        timeline_enum = Timeline(body.timeline.lower())
        theme_enum = Theme(body.theme.lower())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid parameter: {e}")

    story_request = StoryRequest(
        seed_idea=body.seed_idea,
        culture=culture_enum,
        timeline=timeline_enum,
        theme=theme_enum,
    )

    async def event_stream():
        wiki_context = await get_wikipedia_summary(
            story_request.culture.value,
            story_request.timeline.value,
            story_request.theme.value,
        )
        mode, bridge = detect_mode(story_request.culture.value, story_request.timeline.value)
        story_hash = hashlib.sha256(
            f"{story_request.culture.value}|{story_request.timeline.value}|{story_request.theme.value}|{story_request.seed_idea}".encode()
        ).hexdigest()[:16]

        showrunner = ShowrunnerAgent()

        async def planner_fn(wo):
            from chain import _run_planner
            blueprint = await _run_planner(story_request, wiki_context, bridge)
            from schemas import WorkResult
            return WorkResult(success=True, output_data=blueprint)

        async def writer_fn(wo):
            from chain import _run_writer
            story_data = await _run_writer(story_request, wo.input_data["blueprint"], wiki_context, bridge)
            from schemas import WorkResult
            return WorkResult(success=True, output_data=story_data)

        async def supervisor_fn(wo):
            from agents.script_supervisor import ScriptSupervisorAgent
            agent = ScriptSupervisorAgent()
            return await agent.execute(wo)

        async def director_fn(wo):
            from agents.director import DirectorAgent
            agent = DirectorAgent()
            return await agent.execute(wo)

        async def pd_fn(wo):
            from agents.production_designer import ProductionDesignerAgent
            agent = ProductionDesignerAgent()
            return await agent.execute(wo)

        async def ad_fn(wo):
            from agents.art_director import ArtDirectorAgent
            agent = ArtDirectorAgent()
            return await agent.execute(wo)

        async def image_swarm_fn(wo):
            from agents.image_swarm_lead import ImageSwarmLead
            agent = ImageSwarmLead()
            return await agent.execute(wo)

        async for event in showrunner.orchestrate(
            planner_fn, writer_fn, supervisor_fn,
            story_request, wiki_context, bridge,
            director_fn, pd_fn, ad_fn,
            image_swarm_fn,
        ):
            if event.phase == "done":
                combined = event.data or {}
                img_data = combined.get("images", {})

                total = img_data.get("total_count", 0)
                portraits = img_data.get("portraits", [])
                scenes = img_data.get("scenes", [])
                char_map = img_data.get("character_map", {})

                images_payload = {
                    "setting": scenes[0]["url"] if scenes else None,
                    "scenes": [s["url"] for s in scenes],
                    "characters": {name: [p["url"] for p in variants] for name, variants in char_map.items()},
                    "total_count": total,
                }
                yield f"event: images\ndata: {json.dumps({'phase': 'images', 'step': 'complete', 'pct': 85, 'message': f'Image swarm: {total} images', 'data': images_payload})}\n\n"
                continue
            yield f"event: {event.phase}\ndata: {json.dumps(event.to_dict())}\n\n"

        yield f"event: post\ndata: {json.dumps({'phase': 'post', 'step': 'audio', 'pct': 90, 'message': 'Generating narration...'})}\n\n"

        audio_url = None
        try:
            audio_bytes = await edge_tts_service.narrate_story(
                title=f"Chronicles: {story_request.seed_idea[:40]}",
                story_text="",
                culture=story_request.culture.value,
                theme=story_request.theme.value,
            )
            if audio_bytes:
                edge_tts_service.cache(story_hash, audio_bytes)
                audio_url = f"/api/audio/{story_hash}"
                yield f"event: post\ndata: {json.dumps({'phase': 'post', 'step': 'audio_complete', 'pct': 95, 'message': 'Narration ready', 'data': {'audio_url': audio_url}})}\n\n"
        except Exception as e:
            logger.warning(f"Audio generation failed: {e}")

        yield f"event: done\ndata: {json.dumps({'phase': 'done', 'pct': 100, 'message': 'Film complete', 'data': {'audio_url': audio_url, 'mode': mode}})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@app.get("/api/audio/status/{story_hash}")
async def get_audio_status_endpoint(story_hash: str):
    status = get_audio_status(story_hash)
    return status


@app.get("/api/audio/{story_hash}")
async def get_audio_file(story_hash: str):
    audio_data = edge_tts_service.get_cached(story_hash)
    if not audio_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio not found"
        )

    return Response(
        content=audio_data,
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": f"inline; filename={story_hash}.mp3",
            "Content-Length": str(len(audio_data)),
            "Accept-Ranges": "bytes"
        }
    )


if __name__ == "__main__":
    import uvicorn
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

    print("=" * 70)
    print("🚀 Chronicles Production - Starting Server")
    print("=" * 70)
    print(f"\n📡 Server: http://localhost:8000")
    print(f"📚 API Docs: http://localhost:8000/docs")
    print(f"🤖 Model: {CONFIG.POLLINATIONS_MODEL}")
    print("\n" + "=" * 70 + "\n")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
