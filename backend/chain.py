"""
Chronicles Story Engine - Story Generation Pipeline
====================================================
Two-agent pipeline: Planner → Writer.
No refiner. Prompts are strong enough to not need a cleanup pass.
"""

import json
import logging
import re
import hashlib
import httpx
import asyncio

from config import CONFIG, TIMELINE_BUCKETS, BUCKET_ORDER, CULTURE_NATURAL_ERA, SAFETY_CONSTRAINED_CULTURES
from prompts import STORY_PLANNER_PROMPT, STORY_WRITER_PROMPT, LLM_OUTPUT_INSTRUCTION, get_culture_traps
from schemas import StoryRequest, StoryOutput
from utils import get_wikipedia_summary, scan_for_stereotypes, extract_and_repair_json
from utils.llm_client import call_llm as _call_llm
from db_service import db_service
from cache import cache_story, get_cached_story

from logger_config import chain_logger as logger

# Token budgets are now in config.py:
# - PLANNER_MAX_TOKENS = 2800 (enough for complete blueprint JSON)
# - WRITER_MAX_TOKENS = 3000 (enough for 500-1200 word story)


# ---------------------------------------------------------------------------
# VALIDATION FUNCTIONS (Phase 1: Log-only)
# ---------------------------------------------------------------------------

def validate_seed_in_blueprint(seed_idea: str, blueprint: dict) -> bool:
    """
    Check if seed idea is incorporated in blueprint.
    Returns True if seed keywords appear in plot_outline or title.
    
    Args:
        seed_idea: Original seed idea from user
        blueprint: Planner output dict
        
    Returns:
        True if seed is incorporated, False otherwise
    """
    if not seed_idea or not blueprint:
        return False
    
    # Extract keywords from seed (words > 3 chars)
    seed_keywords = [w.lower() for w in seed_idea.split() if len(w) > 3]
    
    if not seed_keywords:
        return False
    
    # Check title
    title = blueprint.get('title', '').lower()
    title_match = sum(1 for kw in seed_keywords if kw in title)
    
    # Check plot_outline
    plot_outline = blueprint.get('plot_outline', {})
    plot_text = str(plot_outline).lower()
    plot_match = sum(1 for kw in seed_keywords if kw in plot_text)
    
    # Check inciting_incident specifically
    inciting = blueprint.get('inciting_incident', '').lower()
    inciting_match = sum(1 for kw in seed_keywords if kw in inciting)
    
    # Require at least 40% keyword match across all fields
    total_matches = title_match + plot_match + inciting_match
    required = max(1, int(len(seed_keywords) * 0.4))
    
    return total_matches >= required


def validate_theme(theme: str, story_text: str, theme_reflection: str) -> bool:
    """
    Check if theme is demonstrated in story.
    Returns True if theme word or related concepts appear.
    
    Args:
        theme: Theme enum value (e.g., "corruption", "resistance")
        story_text: Full story narrative
        theme_reflection: Theme explanation from story output
        
    Returns:
        True if theme is present, False otherwise
    """
    if not theme or not story_text:
        return False
    
    # Theme synonyms for matching
    theme_synonyms = {
        "ambition": ["ambition", "ambitious", "power", "drive", "desire", "reach", "climb"],
        "betrayal": ["betray", "betrayal", "traitor", "deceive", "deception", "lie", "backstab", "trust"],
        "forgiveness": ["forgive", "forgiveness", "pardon", "mercy", "absolve", "let go"],
        "growth": ["grow", "growth", "change", "transform", "learn", "become", "evolve"],
        "loss": ["loss", "lose", "lost", "grief", "mourn", "death", "gone"],
        "redemption": ["redeem", "redemption", "atonement", "save", "salvation", "make right"],
        "rivalry": ["rival", "rivalry", "compete", "competition", "enemy", "foe"],
        "sacrifice": ["sacrifice", "sacrifices", "give up", "surrender", "cost", "price"],
        "discovery": ["discover", "discovery", "find", "uncover", "reveal", "learn", "truth"],
        "endurance": ["endure", "endurance", "survive", "persist", "last", "withstand"],
        "hope": ["hope", "hopeful", "dream", "wish", "believe", "faith"],
        "regret": ["regret", "regretful", "sorry", "wish", "should have", "could have"],
        "love": ["love", "loved", "lover", "beloved", "heart", "affection"],
        "desire": ["desire", "desired", "want", "crave", "longing", "yearn"],
        "forbidden_love": ["forbidden", "forbidden love", "taboo", "secret love", "hidden"],
        "jealousy": ["jealous", "jealousy", "envy", "envious", "covet"],
        "heartbreak": ["heartbreak", "heartbroken", "broken heart", "shattered"],
        "power": ["power", "powerful", "control", "dominate", "rule", "authority"],
        "corruption": ["corrupt", "corruption", "corrupted", "bribe", "manipulate", "abuse", "rotten"],
        "justice": ["justice", "just", "fair", "righteous", "judge", "judgment"],
        "loyalty": ["loyal", "loyalty", "faithful", "devoted", "allegiance"],
        "duty": ["duty", "duty-bound", "obligation", "responsibility", "owe"],
        "obsession": ["obsess", "obsession", "obsessed", "fixate", "consume"],
        "revenge": ["revenge", "avenge", "vengeance", "retaliate", "payback"],
        "deception": ["deceive", "deception", "deceptive", "lie", "false", "mask"],
        "faith": ["faith", "faithful", "believe", "belief", "trust", "god", "divine"],
        "hubris": ["hubris", "pride", "arrogant", "arrogance", "prideful", "overconfident"],
        "survival": ["survive", "survival", "live", "stay alive", "endure"],
        "resistance": ["resist", "resistance", "rebel", "rebellion", "defy", "fight", "oppose"],
        "freedom": ["freedom", "free", "liberty", "liberate", "unbound", "chains"],
        "exile": ["exile", "exiled", "banish", "outcast", "cast out", "homeland"],
        "identity": ["identity", "who am i", "self", "know thyself", "become"],
        "legacy": ["legacy", "inherit", "ancestors", "descendants", "remember", "memory"],
        "truth": ["truth", "true", "lie", "false", "honest", "deceive", "reveal"],
        "memory": ["memory", "memories", "remember", "forget", "recall", "past"],
        "ignorance": ["ignorance", "ignorant", "unknowing", "blind", "unaware"],
        "wonder": ["wonder", "wondrous", "amazement", "awe", "marvel"]
    }
    
    keywords = theme_synonyms.get(theme.lower(), [theme.lower()])
    story_lower = story_text.lower()
    reflection_lower = theme_reflection.lower() if theme_reflection else ""
    
    # Check if any theme keyword appears in story or reflection
    match_count = sum(1 for kw in keywords if kw in story_lower or kw in reflection_lower)
    
    # Require at least 1 match in story OR reflection
    return match_count >= 1


def detect_mode(culture: str, timeline: str) -> tuple[str, dict]:
    culture_bucket = CULTURE_NATURAL_ERA.get(culture, "ancient")
    timeline_bucket = TIMELINE_BUCKETS.get(timeline, "ancient")
    culture_idx = BUCKET_ORDER.index(culture_bucket) if culture_bucket in BUCKET_ORDER else 0
    timeline_idx = BUCKET_ORDER.index(timeline_bucket) if timeline_bucket in BUCKET_ORDER else 0
    distance = abs(timeline_idx - culture_idx)
    if distance <= 1:
        return "historical", {}
    bridge = {
        "mode": "counterfactual_required" if distance >= 3 else "counterfactual",
        "distance_buckets": distance,
        "culture_bucket": culture_bucket,
        "timeline_bucket": timeline_bucket,
    }
    return bridge["mode"], bridge


def build_bridge_prompt_fragment(bridge: dict) -> str:
    if not bridge:
        return ""
    return (
        f"\n\n## COUNTERFACTUAL BRIDGE (MANDATORY — distance: {bridge['distance_buckets']} buckets apart)\n\n"
        f"Your story combines a **{bridge['culture_bucket']}-era culture** with a **{bridge['timeline_bucket']}-era timeline**. "
        f"This is a counterfactual/alternate-history scenario. The bridge between these eras must feel INTENTIONAL, not random.\n\n"
        f"### Required Output Fields\n\n"
        f"Add these fields to your JSON output:\n\n"
        f'1. **framing_label**: One of ["alternate history", "speculative", "surreal allegory"] — declares the story genre\n'
        f'2. **divergence_point**: 1-2 sentences explaining what changed to make this combo possible\n'
        f'3. **continuity_rules**: 3 bullets listing what remains culturally true (social texture, speech, institutions)\n'
        f'4. **diffusion_rules**: 3 bullets listing how tech/ideas spread and who controls them\n'
        f'5. **cost**: 1-2 sentences describing what breaks, the stakes, what is lost\n'
        f'6. **integration_notes**: 3 bullets mapping how the bridge appears in specific story beats\n\n'
        f"### Bridge Quality Standard\n"
        f"- The divergence_point must be specific and plausible\n"
        f"- continuity_rules must ground the story in authentic culture, not generic tropes\n"
        f"- diffusion_rules must prevent modern-tech vibes from leaking into ancient settings\n"
        f"- The cost must create genuine dramatic tension\n"
    )


def build_safety_appendix(culture: str) -> str:
    constraint = SAFETY_CONSTRAINED_CULTURES.get(culture)
    if not constraint:
        return ""
    return f"\n\n## SAFETY CONSTRAINT (MANDATORY)\n\n{constraint}\n"


def build_writer_bridge_context(bridge: dict, blueprint: dict) -> str:
    if not bridge:
        return ""
    fields = {}
    for key in ("framing_label", "divergence_point", "continuity_rules",
                 "diffusion_rules", "cost", "integration_notes"):
        if key in blueprint:
            fields[key] = blueprint[key]
    if not fields:
        return ""
    lines = [
        "\n\n## COUNTERFACTUAL BRIDGE CONTEXT (use these to maintain coherence)",
        f"Framing: {fields.get('framing_label', 'speculative')}",
    ]
    if "divergence_point" in fields:
        lines.append(f"Divergence: {fields['divergence_point']}")
    if "continuity_rules" in fields:
        rules = fields["continuity_rules"]
        rules_str = "; ".join(rules) if isinstance(rules, list) else str(rules)
        lines.append(f"Continuity: {rules_str}")
    if "diffusion_rules" in fields:
        rules = fields["diffusion_rules"]
        rules_str = "; ".join(rules) if isinstance(rules, list) else str(rules)
        lines.append(f"Diffusion: {rules_str}")
    if "cost" in fields:
        lines.append(f"Cost: {fields['cost']}")
    if "integration_notes" in fields:
        notes = fields["integration_notes"]
        notes_str = "; ".join(notes) if isinstance(notes, list) else str(notes)
        lines.append(f"Integration: {notes_str}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Agent 1: Planner
# ---------------------------------------------------------------------------

async def _run_planner(request: StoryRequest, wiki_context: str, bridge: dict = None) -> dict:
    bridge_fragment = build_bridge_prompt_fragment(bridge) if bridge else ""
    safety_appendix = build_safety_appendix(request.culture.value)
    user_msg = STORY_PLANNER_PROMPT.format(
        culture=request.culture.value,
        timeline=request.timeline.value,
        theme=request.theme.value,
        seed_idea=request.seed_idea,
        wiki_context=wiki_context,
        culture_traps=get_culture_traps(request.culture.value),
    )
    user_msg += bridge_fragment + safety_appendix

    logger.info("Planner: generating blueprint...")
    logger.info(f"Planner max_tokens: {CONFIG.PLANNER_MAX_TOKENS}")
    logger.debug(f"Planner input: culture={request.culture.value}, timeline={request.timeline.value}, theme={request.theme.value}, wiki_context={len(wiki_context)} chars")
    
    raw = await _call_llm(
        system=f"{LLM_OUTPUT_INSTRUCTION}",
        user=user_msg,
        max_tokens=CONFIG.PLANNER_MAX_TOKENS,
        temperature=CONFIG.PLANNER_TEMPERATURE,
        task="planner",
    )

    blueprint = extract_and_repair_json(raw)
    
    # Hash blueprint for debugging
    blueprint_hash = hashlib.sha256(json.dumps(blueprint, sort_keys=True).encode()).hexdigest()[:8]
    logger.info(f"Planner: blueprint ready — title={blueprint.get('title', '?')}, hash={blueprint_hash}")
    
    return blueprint


# ---------------------------------------------------------------------------
# Agent 2: Writer
# ---------------------------------------------------------------------------

async def _run_writer(request: StoryRequest, blueprint: dict, wiki_context: str, bridge: dict = None) -> dict:
    blueprint_chars = blueprint.get('supporting_characters', [])
    blueprint_chars_str = '\n'.join(f"- {char}" for char in blueprint_chars) if blueprint_chars else "No characters specified"

    user_msg = STORY_WRITER_PROMPT.format(
        seed_idea=request.seed_idea,
        blueprint=json.dumps(blueprint, indent=2),
        blueprint_characters=blueprint_chars_str,
        culture=request.culture.value,
        timeline=request.timeline.value,
        theme=request.theme.value,
        wiki_context=wiki_context,
    )
    user_msg += build_writer_bridge_context(bridge, blueprint)

    logger.info("Writer: generating narrative...")
    logger.debug(f"Writer input: blueprint has {len(blueprint)} keys, wiki_context={len(wiki_context)} chars")
    
    raw = await _call_llm(
        system=f"{LLM_OUTPUT_INSTRUCTION}",
        user=user_msg,
        max_tokens=CONFIG.WRITER_MAX_TOKENS,
        temperature=CONFIG.WRITER_TEMPERATURE,
        task="writer",
    )

    story_data = extract_and_repair_json(raw)
    word_count = len(story_data.get("story", "").split())
    
    # Hash story output for debugging
    story_hash = hashlib.sha256(story_data.get("story", "").encode()).hexdigest()[:8]
    logger.info(f"Writer: story ready — {word_count} words, hash={story_hash}")
    
    return story_data


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def generate_story(request: StoryRequest) -> StoryOutput:
    """
    Full pipeline: Wikipedia → Planner → Writer → stereotype scan.
    Returns a validated StoryOutput.
    """
    # Compute cache key from request parameters
    cache_key = hashlib.sha256(
        f"{request.culture.value.lower().strip()}|"
        f"{request.timeline.value.lower().strip()}|"
        f"{request.theme.value.lower().strip()}|"
        f"{request.seed_idea.lower().strip()}"
        .encode()
    ).hexdigest()

    # Check cache first
    cached = await get_cached_story(cache_key)
    if cached:
        logger.info(f"Cache hit for key {cache_key[:8]}...")
        return StoryOutput(**cached["story_data"])

    # Ground the story in real historical context
    wiki_context = await get_wikipedia_summary(
        request.culture.value,
        request.timeline.value,
        request.theme.value,
    )
    logger.info(f"Wiki context fetched ({len(wiki_context)} chars)")

    mode, bridge = detect_mode(request.culture.value, request.timeline.value)
    logger.info(f"Mode: {mode}" + (f" (distance={bridge.get('distance_buckets')})" if bridge else ""))

    # Agent 1: plan
    blueprint = await _run_planner(request, wiki_context, bridge)

    # VALIDATION #1: Check seed in blueprint
    seed_in_blueprint = validate_seed_in_blueprint(request.seed_idea, blueprint)
    if not seed_in_blueprint:
        logger.warning(f"[FAIL] SEED NOT IN BLUEPRINT: '{request.seed_idea}' - RETRYING ONCE")
        # PHASE 2A: Retry Planner once if seed fails
        blueprint = await _run_planner(request, wiki_context, bridge)
        seed_in_blueprint = validate_seed_in_blueprint(request.seed_idea, blueprint)
        if seed_in_blueprint:
            logger.info(f"[PASS] Seed incorporated after retry")
        else:
            logger.warning(f"[WARN] Seed still not incorporated after retry - proceeding anyway")
    else:
        logger.info(f"[PASS] Seed incorporated in blueprint")

    # Agent 2: write
    story_data = await _run_writer(request, blueprint, wiki_context, bridge)

    # Extract and validate story
    story_text = story_data.get("story", "")
    word_count = len(story_text.split())
    theme_reflection = story_data.get("theme_reflection", "")

    # Soft validation: log warning if out of target range
    if word_count < CONFIG.MIN_STORY_WORDS:
        logger.warning(f"Story below target ({word_count} words, min: {CONFIG.MIN_STORY_WORDS})")
    elif word_count > CONFIG.MAX_STORY_WORDS:
        logger.warning(f"Story above target ({word_count} words, max: {CONFIG.MAX_STORY_WORDS})")

    # VALIDATION #2: Check theme presence (Phase 1)
    theme_present = validate_theme(request.theme.value, story_text, theme_reflection)
    if theme_present:
        logger.info(f"[PASS] Theme '{request.theme.value}' demonstrated")
    else:
        logger.warning(f"[WARN] THEME NOT CLEAR: '{request.theme.value}' not found in story")

    # Safety scan
    flagged = scan_for_stereotypes(story_text)
    if flagged:
        logger.warning(f"Stereotype scan flagged: {flagged}")

    # Normalize characters to list of strings
    raw_chars = story_data.get("characters", [])
    if raw_chars and isinstance(raw_chars[0], dict):
        # Model returned objects, convert to strings
        characters = [f"{c.get('name', 'Unknown')}: {c.get('description', c.get('role', ''))}" for c in raw_chars]
    else:
        characters = raw_chars

    result = StoryOutput(
        title=story_data.get("title") or blueprint.get("title", "Untitled"),
        setting=story_data.get("setting") or blueprint.get("setting", ""),
        characters=characters,
        story=story_text,
        theme_reflection=story_data.get("theme_reflection", ""),
        stereotypes_flagged=flagged,
        validation_seed=seed_in_blueprint,
        validation_theme=theme_present,
    )

    # Store in cache
    # DO NOT cache stories with stereotype flags
    if flagged:
        logger.info(f"Skipping cache for flagged story (key {cache_key[:8]}...)")
    else:
        await db_service.save_story(request, result, cache_key)
        story_dict = {
            "title": result.title,
            "setting": result.setting,
            "characters": result.characters,
            "story": result.story,
            "theme_reflection": result.theme_reflection,
            "stereotypes_flagged": result.stereotypes_flagged,
            "validation_seed": result.validation_seed,
            "validation_theme": result.validation_theme,
        }
        await cache_story(cache_key, story_dict, {"mode": mode})

    return result
