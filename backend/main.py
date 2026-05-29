import logging
import sys
import hashlib
import asyncio
import anyio
import json
import sqlite3
from pathlib import Path
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
    StoryGenerationResponse, Culture, Timeline, Theme, WorkOrder,
    FilmSummary, CatalogRow, CatalogResponse, FilmDetail,
)
from config import CONFIG
from audio import get_voice_for_culture
from audio.edge_tts_service import edge_tts_service
from tasks import generate_audio_background, get_audio_status
from cache import cache_story, get_cached_story, cache_visuals
from utils.wiki_context import get_culture_fallback_data, audit_fallback_coverage, get_wikipedia_summary
from agents.showrunner import ShowrunnerAgent, ProgressEvent

FILMS_DIR = Path(__file__).parent / "generated"
DB_PATH = Path(__file__).parent / "chronicles.db"


def _save_film_to_catalog(
    story_hash: str, title: str, seed_idea: str,
    culture: str, timeline: str, theme: str, mode: str,
    setting: str = "", narrative: str = "",
    thumbnail_url: str | None = None,
    scene_images: list[str] | None = None,
    character_portraits: list[str] | None = None,
    video_path: str | None = None,
    narration_path: str | None = None,
    agent_count: int = 0,
    generation_time_ms: int = 0,
):
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS films (
                story_hash TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                seed_idea TEXT NOT NULL,
                culture TEXT NOT NULL,
                timeline TEXT NOT NULL,
                theme TEXT NOT NULL,
                mode TEXT NOT NULL DEFAULT 'historical',
                setting TEXT,
                narrative TEXT,
                theme_reflection TEXT,
                word_count INTEGER,
                thumbnail_url TEXT,
                scene_images TEXT,
                character_portraits TEXT,
                video_path TEXT,
                narration_path TEXT,
                agent_count INTEGER,
                generation_time_ms INTEGER,
                status TEXT DEFAULT 'completed',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT
            )
        """)
        conn.execute("""
            INSERT OR REPLACE INTO films
                (story_hash, title, seed_idea, culture, timeline, theme, mode,
                 setting, narrative, word_count, thumbnail_url, scene_images,
                 character_portraits, video_path, narration_path,
                 agent_count, generation_time_ms, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'completed')
        """, (
            story_hash, title, seed_idea, culture, timeline, theme, mode,
            setting, narrative, len(narrative.split()) if narrative else 0,
            thumbnail_url,
            json.dumps(scene_images or []),
            json.dumps(character_portraits or []),
            video_path, narration_path,
            agent_count, generation_time_ms,
        ))
        conn.commit()
        conn.close()
        logger.info(f"Film {story_hash[:8]} saved to catalog")
    except Exception as e:
        logger.warning(f"Failed to save film to catalog: {e}")
from agents.video_lead import VideoLead
from agents.editor import EditorAgent
from agents.sound_designer import SoundDesignerAgent
from post.assembler import FFmpegAssembler
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

STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")


@app.get("/")
async def root():
    index = STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index), media_type="text/html")
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
        "rate_limit_tier": "anonymous" if not CONFIG.POLLINATIONS_API_KEY else "authenticated",
        "video_provider": CONFIG.VIDEO_PROVIDER,
        "cloud_gpu_configured": bool(CONFIG.CLOUD_GPU_ENDPOINT),
        "gpu_endpoint": CONFIG.CLOUD_GPU_ENDPOINT or "NOT SET"
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
            f"{story_request.culture.value}|{story_request.timeline.value}|{story_request.theme.value}|{story_request.seed_idea}".encode()
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

        await cache_story(story_hash, story_data, response.metadata)

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
async def generate_film(request: Request, body: StoryGenerationRequest):
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
        combined = {}
        char_map = {}
        images_payload = {}
        showrunner_completed = False

        showrunner = ShowrunnerAgent()

        async def planner_fn(wo):
            from chain import _run_planner
            blueprint = await _run_planner(story_request, wiki_context, bridge)
            from schemas import WorkResult
            return WorkResult(success=True, output_data=blueprint)

        async def writer_fn(wo):
            from agents.writer_scene import WriterSceneAgent
            agent = WriterSceneAgent()
            return await agent.execute(wo)

        async def director_fn(wo):
            from agents.visual_bible_architect import VisualBibleArchitect
            agent = VisualBibleArchitect()
            return await agent.execute(wo)

        async def image_swarm_fn(wo):
            from agents.image_swarm_lead import ImageSwarmLead
            agent = ImageSwarmLead()
            return await agent.execute(wo)

        async def video_swarm_fn(wo):
            agent = VideoLead()
            return await agent.execute(wo)

        async for event in showrunner.orchestrate(
            planner_fn, writer_fn, supervisor_fn=None,
            story_request=story_request, wiki_context=wiki_context, bridge=bridge,
            director_fn=director_fn,
            image_swarm_fn=image_swarm_fn,
            story_hash=story_hash,
        ):
            if event.phase == "pipeline_complete":
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
                showrunner_completed = True
                yield f"event: images\ndata: {json.dumps({'phase': 'images', 'step': 'complete', 'pct': 85, 'message': f'Image swarm: {total} images', 'data': images_payload})}\n\n"
                continue
            if event.phase == "images" and event.step == "complete":
                continue
            yield f"event: {event.phase}\ndata: {json.dumps(event.to_dict())}\n\n"

        if not showrunner_completed:
            yield f"event: error\ndata: {json.dumps({'phase': 'error', 'step': 'pipeline_failed', 'pct': 100, 'message': 'Film pipeline stopped before final story package was produced', 'data': {}, 'error': True})}\n\n"
            return

        yield f"event: video\ndata: {json.dumps({'phase': 'video', 'step': 'crafting', 'pct': 87, 'message': 'Crafting video prompts...', 'data': {}, 'error': False})}\n\n"

        video_result = None
        try:
            scene_list = combined.get("scenes", {}).get("scenes", []) if combined else []
            if not scene_list:
                scene_list = combined.get("supervisor", {}).get("scenes", [])
            vb_data = combined.get("visual_bible", {}) if combined else {}
            char_bibles = {}
            if vb_data:
                char_bibles = (
                    vb_data.get("director", {}).get("character_bibles", {})
                    or vb_data.get("character_bibles", {})
                )
            ref_images = {}
            if char_map:
                for ch_name, portraits_list in char_map.items():
                    if portraits_list and len(portraits_list) > 0:
                        ref_images[ch_name] = portraits_list[0].get("url", "")

            scenes_for_video = []
            for i in range(CONFIG.VIDEO_CLIP_COUNT):
                if i < len(scene_list):
                    scenes_for_video.append(scene_list[i])
                elif scene_list:
                    scenes_for_video.append(scene_list[i % len(scene_list)])

            video_wo = WorkOrder(
                agent_type="video_lead",
                input_data={
                    "scenes": scenes_for_video,
                    "visual_bible": vb_data,
                    "character_bibles": char_bibles,
                    "reference_images": ref_images,
                    "clip_duration": CONFIG.CLIP_DURATION_S,
                },
                story_hash=story_hash,
                priority=1,
            )
            video_agent = VideoLead()
            video_result = await video_agent.execute(video_wo)
            yield f"event: video\ndata: {json.dumps({'phase': 'video', 'step': 'generation', 'pct': 95, 'message': 'Video generation complete', 'data': video_result.output_data if video_result and video_result.success else {}})}\n\n"
        except Exception as e:
            logger.warning(f"Video generation failed: {e}")
            yield f"event: video\ndata: {json.dumps({'phase': 'video', 'step': 'failed', 'pct': 95, 'message': f'Video generation failed: {e}', 'data': {}, 'error': True})}\n\n"

        yield f"event: post\ndata: {json.dumps({'phase': 'post', 'step': 'audio', 'pct': 96, 'message': 'Generating narration...', 'data': {}, 'error': False})}\n\n"

        audio_url = None
        narration_path = ""

        story_data = combined.get("story", {}) if combined else {}
        story_text_content = story_data.get("story", "")
        scenes_raw = combined.get("scenes", {}).get("scenes", []) if combined else []
        vb_data = combined.get("visual_bible", {}) if combined else {}

        try:
            audio_bytes = await edge_tts_service.narrate_story(
                title=f"Chronicles: {story_request.seed_idea[:40]}",
                story_text=story_text_content,
                culture=story_request.culture.value,
                theme=story_request.theme.value,
            )
            if audio_bytes:
                edge_tts_service.cache(story_hash, audio_bytes)
                audio_url = f"/api/audio/{story_hash}"
                from audio.edge_tts_service import CACHE_DIR
                narration_path = str(CACHE_DIR / f"{story_hash}.mp3")
                yield f"event: post\ndata: {json.dumps({'phase': 'post', 'step': 'audio_complete', 'pct': 98, 'message': 'Narration ready', 'data': {'audio_url': audio_url}})}\n\n"
        except Exception as e:
            logger.warning(f"Audio generation failed: {e}")

        clips = []
        if video_result and video_result.success:
            clips = video_result.output_data.get("clips", [])

        story_title = story_data.get("title", story_request.seed_idea[:40])

        # Phase 5: Post-Production
        yield f"event: post\ndata: {json.dumps({'phase': 'post', 'step': 'editing', 'pct': 96, 'message': 'Creating assembly timeline...', 'data': {}, 'error': False})}\n\n"

        try:
            editor = EditorAgent()
            editor_wo = WorkOrder(
                agent_type="editor",
                input_data={
                    "title": story_title,
                    "culture": story_request.culture.value,
                    "timeline": story_request.timeline.value,
                    "theme": story_request.theme.value,
                    "scenes": scenes_raw,
                    "clip_data": clips,
                    "target_duration_s": CONFIG.TARGET_FILM_DURATION_S,
                },
                story_hash=story_hash,
                priority=1,
            )
            editor_result = await editor.execute(editor_wo)
            assembly_timeline = editor_result.output_data.get("assembly_timeline", {}) if editor_result.success else {}
        except Exception as e:
            logger.warning(f"Editor failed: {e}")
            assembly_timeline = {}

        yield f"event: post\ndata: {json.dumps({'phase': 'post', 'step': 'sound', 'pct': 97, 'message': 'Designing audio...', 'data': {}, 'error': False})}\n\n"

        try:
            sound = SoundDesignerAgent()
            sound_wo = WorkOrder(
                agent_type="sound_designer",
                input_data={
                    "narration_path": narration_path,
                    "culture": story_request.culture.value,
                    "scenes": scenes_raw,
                },
                story_hash=story_hash,
                priority=2,
            )
            sound_result = await sound.execute(sound_wo)
            audio_timeline = sound_result.output_data.get("audio_timeline", {}) if sound_result.success else {}
        except Exception as e:
            logger.warning(f"Sound designer failed: {e}")
            audio_timeline = {}

        yield f"event: post\ndata: {json.dumps({'phase': 'post', 'step': 'color', 'pct': 98, 'message': 'Color grading...', 'data': {}, 'error': False})}\n\n"

        from utils.color_grade import compute_grading_spec
        grading_spec = compute_grading_spec(
            color_palette=vb_data.get("color_palette", {}) if vb_data else {},
            film_tone=vb_data.get("film_tone", "") if vb_data else "",
            lighting_style=vb_data.get("lighting_style", "") if vb_data else "",
        )

        yield f"event: post\ndata: {json.dumps({'phase': 'post', 'step': 'assembly', 'pct': 99, 'message': 'Assembling final MP4...', 'data': {}, 'error': False})}\n\n"

        if narration_path and Path(narration_path).exists():
            if not audio_timeline:
                audio_timeline = {}
            if "narration" not in audio_timeline:
                audio_timeline["narration"] = {}
            audio_timeline["narration"]["audio_path"] = narration_path

        mp4_path = None
        try:
            assembler = FFmpegAssembler()
            mp4_path = assembler.assemble(
                story_hash=story_hash,
                assembly_timeline=assembly_timeline,
                audio_timeline=audio_timeline,
                grading_spec=grading_spec,
                clip_data=clips,
            )
        except Exception as e:
            logger.warning(f"Assembly failed: {e}")

        mp4_url = f"/films/chronicles_{story_hash}.mp4" if mp4_path and mp4_path.exists() else None

        _save_film_to_catalog(
            story_hash=story_hash,
            title=story_title,
            seed_idea=story_request.seed_idea,
            culture=story_request.culture.value,
            timeline=story_request.timeline.value,
            theme=story_request.theme.value,
            mode=mode,
            setting=story_data.get("setting", ""),
            narrative=story_text_content,
            thumbnail_url=images_payload.get("setting"),
            scene_images=images_payload.get("scenes", []),
            character_portraits=[
                url_obj.get("url", "")
                for urls in images_payload.get("characters", {}).values()
                if isinstance(urls, list)
                for url_obj in urls
                if isinstance(url_obj, dict)
            ],
            video_path=mp4_url,
            narration_path=audio_url,
            agent_count=35,
            generation_time_ms=0,
        )

        yield f"event: done\ndata: {json.dumps({'phase': 'done', 'pct': 100, 'message': 'Film complete', 'data': {'audio_url': audio_url, 'mode': mode, 'video_clips': clips, 'total_clips': len(clips), 'mp4_url': mp4_url}, 'error': False})}\n\n"

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


@app.get("/films/{filename}")
async def serve_film(filename: str):
    file_path = FILMS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Film not found")
    return FileResponse(str(file_path), media_type="video/mp4")


@app.get("/clips/{filename}")
async def serve_clip(filename: str):
    file_path = FILMS_DIR / "clips" / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Clip not found")
    return FileResponse(str(file_path), media_type="video/mp4")


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


@app.get("/api/catalog", response_model=CatalogResponse)
async def get_catalog(
    culture: Optional[str] = None,
    timeline: Optional[str] = None,
    theme: Optional[str] = None,
    query: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
):
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    conditions = ["status = 'completed'"]
    params = []
    if culture:
        conditions.append("culture = ?")
        params.append(culture)
    if timeline:
        conditions.append("timeline = ?")
        params.append(timeline)
    if theme:
        conditions.append("theme = ?")
        params.append(theme)
    if query:
        conditions.append("(title LIKE ? OR seed_idea LIKE ?)")
        params.extend([f"%{query}%", f"%{query}%"])

    where = " AND ".join(conditions)

    cursor.execute(f"SELECT * FROM films WHERE {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
                   [*params, limit, (page - 1) * limit])
    film_rows = [dict(row) for row in cursor.fetchall()]

    rows = []

    cursor.execute("SELECT * FROM films WHERE status='completed' ORDER BY created_at DESC LIMIT 10")
    staff_picks = [dict(row) for row in cursor.fetchall()]
    if staff_picks:
        rows.append(CatalogRow(
            id="staff_picks",
            title="Staff Picks",
            type="staff_picks",
            films=[_row_to_summary(r) for r in staff_picks],
        ))

    cursor.execute("SELECT DISTINCT culture FROM films WHERE status='completed' ORDER BY culture")
    cultures = [row[0] for row in cursor.fetchall()]
    for c in cultures:
        cursor.execute(
            "SELECT * FROM films WHERE status='completed' AND culture=? ORDER BY created_at DESC LIMIT 10",
            [c]
        )
        c_films = [dict(row) for row in cursor.fetchall()]
        if c_films:
            display = c.replace("_", " ").title()
            rows.append(CatalogRow(
                id=f"culture_{c}",
                title=f"{display} Stories",
                type="culture",
                films=[_row_to_summary(r) for r in c_films],
            ))

    THEME_GROUPS = {
        "Power & Corruption": ["corruption", "justice"],
        "Love & Desire": ["forbidden_love", "jealousy"],
        "Survival & Identity": ["survival", "identity", "truth", "memory"],
        "Psychological": ["ambition", "betrayal", "loss", "redemption", "discovery", "obsession", "deception"],
    }
    for group_title, theme_values in THEME_GROUPS.items():
        placeholders = ",".join("?" * len(theme_values))
        cursor.execute(
            f"SELECT * FROM films WHERE status='completed' AND theme IN ({placeholders}) ORDER BY created_at DESC LIMIT 10",
            theme_values
        )
        t_films = [dict(row) for row in cursor.fetchall()]
        if t_films:
            rows.append(CatalogRow(
                id=f"theme_{group_title.lower().replace(' ', '_').replace('&', 'and')}",
                title=group_title,
                type="theme",
                films=[_row_to_summary(r) for r in t_films],
            ))

    conn.close()

    films = [_row_to_summary(r) for r in film_rows]
    return CatalogResponse(films=films, rows=rows)


def _row_to_summary(row: dict) -> FilmSummary:
    return FilmSummary(
        story_hash=row.get("story_hash", ""),
        title=row.get("title", ""),
        culture=row.get("culture", ""),
        timeline=row.get("timeline", ""),
        theme=row.get("theme", ""),
        mode=row.get("mode", "historical"),
        thumbnail_url=row.get("thumbnail_url"),
        created_at=row.get("created_at", ""),
    )


@app.get("/api/films/{story_hash}", response_model=FilmDetail)
async def get_film_detail(story_hash: str):
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM films WHERE story_hash=?", [story_hash])
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Film not found")

    film = dict(row)
    film["character_portraits"] = json.loads(film.get("character_portraits", "[]"))
    film["scene_images"] = json.loads(film.get("scene_images", "[]"))
    film["video_url"] = film.get("video_path")
    film["narration_url"] = film.get("narration_path")

    return FilmDetail(**{k: v for k, v in film.items() if k in FilmDetail.model_fields})


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
