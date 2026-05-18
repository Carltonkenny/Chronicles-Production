"""
Background task runner for audio generation.

Handles async audio generation without blocking story responses.
Generates full narration: intro + story + outro.
"""

import asyncio
import logging
import re
from typing import Dict, Set

logger = logging.getLogger("chronicles-tasks")


# Track audio generation status (in-memory, for polling)
_audio_status: Dict[str, bool] = {}  # story_hash → ready
_pending_tasks: Set[str] = set()  # story_hashes currently generating


def build_full_narration_script(
    title: str,
    setting: str,
    characters: list,
    story: str,
    theme_reflection: str,
) -> str:
    """
    Build complete narration script from story data.

    Structure:
    1. INTRO: Title + Setting + Characters (with prosody + pauses)
    2. STORY: Full narrative (as written by Writer agent)
    3. OUTRO: Theme reflection + closing

    Args:
        title: Story title
        setting: Setting description
        characters: List of character descriptions
        story: Full story narrative
        theme_reflection: Theme reflection text

    Returns:
        Complete narration script with SSML-compatible markers
    """
    # === INTRO (with prosody markers for dramatic delivery)
    # Generative engine supports rate + volume (NOT pitch)
    intro = '[prosody-slow-soft]Chronicles Story Engine presents[/prosody][pause: 1.5s] '
    intro += f'[prosody-xslow-loud]{title}[/prosody][pause: 2.0s] '
    intro += f'[prosody-slow-soft]{setting}.[/prosody][pause: 1.0s] '

    if characters:
        char_names = []
        for char in characters[:4]:  # Limit to 4 characters
            if ":" in char:
                name = char.split(":")[0].strip()
                descriptor = char.split(":")[1].strip().split(".")[0]
                char_names.append(f"{name}, {descriptor}")
            else:
                char_names.append(char)

        intro += f"Featuring, {', '.join(char_names)}.[pause: 2.5s] "

    # === STORY (exact as written)
    full_script = intro + story

    # === OUTRO
    if theme_reflection:
        full_script += f'\n\n[pause: 2.5s] [prosody-slow-soft]{theme_reflection}[/prosody] '

    full_script += '[pause: 1.5s] [prosody-slow-soft]Thank you for listening to Chronicles Story Engine.[/prosody]'

    return full_script


def convert_script_to_ssml(script: str) -> str:
    """
    Convert narration script to SSML.

    Replaces [pause: Xs] markers with <break time="Xs"/> tags.
    Replaces [prosody-*] markers with <prosody> tags.
    Strips special characters that Polly reads aloud.
    Wraps in <speak> tags.

    Args:
        script: Narration script with pause/prosody markers

    Returns:
        SSML-formatted text
    """
    ssml = script

    # --- Text sanitization: strip chars Polly reads literally ---
    ssml = ssml.replace("**", "")       # markdown bold
    ssml = ssml.replace("__", "")       # markdown underline
    ssml = ssml.replace("_", " ")       # underscores → spaces
    ssml = ssml.replace("—", ", ")      # em dash → comma pause
    ssml = ssml.replace("–", ", ")      # en dash → comma pause
    ssml = ssml.replace("...", ".")     # ellipsis → single period
    ssml = ssml.replace("*", "")        # stray asterisks
    ssml = re.sub(r'\s+', ' ', ssml)    # collapse whitespace

    # --- Convert pause markers to SSML break tags ---
    ssml = re.sub(r'\[pause:\s*([\d.]+)s\]', r'<break time="\1s"/>', ssml)

    # --- Convert prosody markers to SSML prosody tags ---
    # Generative engine supports rate + volume (NOT pitch)
    prosody_map = {
        '[prosody-slow-soft]': '<prosody rate="slow" volume="soft">',
        '[prosody-xslow-loud]': '<prosody rate="x-slow" volume="loud">',
        '[/prosody]': '</prosody>',
    }
    for marker, tag in prosody_map.items():
        ssml = ssml.replace(marker, tag)

    # Wrap in speak tags if not already wrapped
    ssml = ssml.strip()
    if not ssml.startswith("<speak>"):
        ssml = f"<speak>{ssml}</speak>"

    return ssml


async def generate_audio_background(
    story_hash: str,
    story_data: dict,
    culture: str,
    theme: str,
    polly_service,
    audio_cache,
) -> None:
    """
    Generate full audio narration in background (fire-and-forget).

    Builds complete script: intro + story + outro.
    This function is called as a background task and does not block
    the main story generation response.

    Args:
        story_hash: Unique hash for this story
        story_data: Full story response dict (title, setting, characters, story, theme_reflection)
        culture: Culture code (e.g., "egyptian", "chola")
        theme: Theme code (e.g., "betrayal", "hope")
        polly_service: PollyService instance
        audio_cache: AudioCache instance
    """
    # Mark as pending
    _pending_tasks.add(story_hash)
    _audio_status[story_hash] = False

    try:
        logger.info(f"Starting background audio generation for story {story_hash[:8]}...")

        # Extract story data
        title = story_data.get("title", "Untitled")
        setting = story_data.get("setting", "")
        characters = story_data.get("characters", [])
        story_text = story_data.get("story", "")
        theme_reflection = story_data.get("theme_reflection", "")

        # Build full narration script (intro + story + outro)
        narration_script = build_full_narration_script(
            title=title,
            setting=setting,
            characters=characters,
            story=story_text,
            theme_reflection=theme_reflection,
        )

        # Convert to SSML
        ssml = convert_script_to_ssml(narration_script)
        logger.info(f"Built full narration script ({len(narration_script)} chars) for story {story_hash[:8]}...")

        # Cache SSML
        if audio_cache and not audio_cache.ssml_exists(story_hash):
            try:
                audio_cache.save_ssml(story_hash, ssml)
                logger.info(f"SSML cached ({len(ssml)} chars) for story {story_hash[:8]}...")
            except Exception as cache_err:
                logger.warning(f"SSML cache save failed (non-fatal): {cache_err}")

        # Check if audio already cached
        if audio_cache.exists(story_hash):
            logger.info(f"Audio already cached for story {story_hash[:8]}...")
            _audio_status[story_hash] = True
            _pending_tasks.discard(story_hash)
            return

        # Synthesize audio with Polly
        logger.info(f"Synthesizing audio for story {story_hash[:8]}...")
        voice_id = polly_service.get_voice_for_culture(culture)
        audio_data = await polly_service.synthesize(ssml, voice_id)
        logger.debug(f"Audio synthesized ({len(audio_data)} bytes) for story {story_hash[:8]}...")

        # Save to cache
        audio_cache.save(story_hash, audio_data)
        logger.info(f"Audio cached successfully for story {story_hash[:8]}...")

        # Mark as ready
        _audio_status[story_hash] = True

    except Exception as e:
        logger.error(f"Background audio generation failed for story {story_hash[:8]}...: {e}")
        _audio_status[story_hash] = False  # Mark as failed

    finally:
        _pending_tasks.discard(story_hash)


def get_audio_status(story_hash: str) -> dict:
    """
    Get audio generation status for a story.
    
    Args:
        story_hash: Story hash to check
    
    Returns:
        Dict with status info:
        - "ready": bool (True if audio is ready)
        - "pending": bool (True if currently generating)
    """
    return {
        "ready": _audio_status.get(story_hash, False),
        "pending": story_hash in _pending_tasks,
    }


def cleanup_status(story_hash: str) -> None:
    """
    Clean up status tracking for a story.
    
    Call this after frontend has retrieved the audio.
    
    Args:
        story_hash: Story hash to clean up
    """
    _audio_status.pop(story_hash, None)
    _pending_tasks.discard(story_hash)
