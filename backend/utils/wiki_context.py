import logging
import re
import time
import json
import httpx
from pathlib import Path
from typing import Optional
import sqlite3

logger = logging.getLogger("chronicles-tools")

DB_PATH = Path(__file__).parent.parent / "chronicles.db"

WIKI_CACHE: dict[str, tuple[float, str]] = {}
WIKI_CACHE_TTL = 86400
WIKI_CACHE_MAX_SIZE = 100

_DB_CACHE: dict[str, dict] = {}


def _load_db_cache():
    global _DB_CACHE
    if _DB_CACHE:
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT id, name, fallback_text, traps, redirects FROM cultures")
        for row in cursor.fetchall():
            _DB_CACHE[f"culture:{row['id']}"] = {
                "name": row["name"],
                "fallback_text": row["fallback_text"] or "",
                "traps": json.loads(row["traps"]) if row["traps"] else [],
                "redirects": json.loads(row["redirects"]) if row["redirects"] else [],
            }

        cursor.execute("SELECT id, name, fallback_text, era_dates FROM timelines")
        for row in cursor.fetchall():
            _DB_CACHE[f"timeline:{row['id']}"] = {
                "name": row["name"],
                "fallback_text": row["fallback_text"] or "",
                "era_dates": row["era_dates"] or "",
            }

        cursor.execute("SELECT id, name, craft_notes FROM themes")
        for row in cursor.fetchall():
            _DB_CACHE[f"theme:{row['id']}"] = {
                "name": row["name"],
                "craft_notes": row["craft_notes"] or "",
            }

        conn.close()
        logger.info(f"DB cache loaded: {len(_DB_CACHE)} entries")
    except Exception as e:
        logger.error(f"Failed to load DB cache: {e}")


def get_db_fallback(category: str, slug: str) -> str:
    _load_db_cache()
    key = f"{category}:{slug}"
    entry = _DB_CACHE.get(key, {})

    if category == "culture":
        return entry.get("fallback_text", f"Historical setting: {slug.replace('_', ' ').title()}.")
    elif category == "timeline":
        return entry.get("fallback_text", f"Historical period: {slug.replace('_', ' ').title()}.")
    elif category == "theme":
        return entry.get("craft_notes", f"Theme: {slug.replace('_', ' ').title()}.")
    return ""


async def get_wikipedia_summary(culture: str, timeline: str, theme: str = None) -> str:
    CULTURE_PAGES = {
        "roman": "Roman Empire",
        "ancient_greek": "Ancient Greece",
        "egyptian": "Ancient Egypt",
        "viking": "Vikings",
        "japanese": "Feudal Japan",
        "persian": "Achaemenid Empire",
        "aztec": "Aztec Empire",
        "celtic": "Celts",
        "mughal": "Mughal Empire",
        "mauryan": "Maurya Empire",
        "chola": "Chola dynasty",
        "east_india_company": "East India Company",
        "ottoman": "Ottoman Empire",
        "byzantine": "Byzantine Empire",
        "tang_dynasty": "Tang dynasty",
        "mali_empire": "Mali Empire",
        "swahili_coast": "Swahili coast",
        "yoruba": "Yoruba people",
        "maya": "Maya civilization",
        "andean": "Andean civilizations",
        "polynesian": "Polynesians",
        "mesopotamian": "Mesopotamia",
        "stone_age": "Stone Age",
        "bronze_age": "Bronze Age",
        "iron_age": "Iron Age",
    }

    FALLBACK_ONLY_CULTURES = {
        "east_india_company", "swahili_coast", "mali_empire",
        "yoruba", "polynesian", "andean",
        "ai_hegemony", "digital_feudalism", "climate_migration",
        "bioengineering_age", "interplanetary_frontier", "star_engineering",
        "interstellar_exodus", "entropy_wars",
        "nazi_germany", "soviet_union", "british_empire", "spanish_empire",
    }

    if culture in FALLBACK_ONLY_CULTURES:
        culture_context = get_db_fallback("culture", culture)
    else:
        page_title = CULTURE_PAGES.get(culture)
        if not page_title:
            culture_context = get_db_fallback("culture", culture)
        else:
            current_time = time.time()
            if page_title in WIKI_CACHE:
                cached_time, cached_result = WIKI_CACHE[page_title]
                if current_time - cached_time < WIKI_CACHE_TTL:
                    culture_context = cached_result
                else:
                    del WIKI_CACHE[page_title]
            else:
                url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{page_title.replace(' ', '_')}"
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.get(
                            url,
                            headers={"User-Agent": "Chronicles-Engine/2.0 (Educational Story Generation API)"},
                            timeout=5.0
                        )
                        response.raise_for_status()
                        data = response.json()
                        summary = data.get("extract", "")
                        sentences = summary.split(". ")[:3]
                        culture_context = ". ".join(sentences) + "." if sentences else ""

                        if len(WIKI_CACHE) >= WIKI_CACHE_MAX_SIZE:
                            oldest_key = min(WIKI_CACHE.keys(), key=lambda k: WIKI_CACHE[k][0])
                            del WIKI_CACHE[oldest_key]
                        WIKI_CACHE[page_title] = (current_time, culture_context)
                except httpx.HTTPError:
                    culture_context = get_db_fallback("culture", culture)

    timeline_context = get_db_fallback("timeline", timeline)

    theme_context = ""
    if theme:
        theme_context = get_db_fallback("theme", theme)

    combined = f"{culture_context}\n\n**Timeline Context ({timeline.replace('_', ' ').title()}):**\n{timeline_context}"

    if theme_context:
        combined += f"\n\n**Theme Context ({theme.replace('_', ' ').title()}):**\n{theme_context}"

    return combined


def get_culture_fallback_data(culture_slug: str) -> dict:
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT fallback_text, traps, redirects 
            FROM cultures 
            WHERE id = ?
        """, (culture_slug,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "fallback_text": row["fallback_text"],
                "traps": json.loads(row["traps"]) if row["traps"] else [],
                "redirects": json.loads(row["redirects"]) if row["redirects"] else []
            }
    except Exception as e:
        logger.warning(f"Failed to get culture fallback: {e}")

    return {"fallback_text": "", "traps": [], "redirects": []}


def audit_fallback_coverage(cultures: list[str], timelines: list[str], themes: list[str]) -> dict:
    _load_db_cache()

    def _status_for(category: str, slug: str) -> dict:
        key = f"{category}:{slug}"
        entry = _DB_CACHE.get(key)
        if not entry:
            return {"present": False, "text_ok": False}

        if category == "culture":
            text_ok = bool((entry.get("fallback_text") or "").strip())
            return {
                "present": True,
                "text_ok": text_ok,
                "traps_count": len(entry.get("traps", [])),
                "redirects_count": len(entry.get("redirects", [])),
            }

        if category == "timeline":
            text_ok = bool((entry.get("fallback_text") or "").strip())
            return {"present": True, "text_ok": text_ok, "era_dates": entry.get("era_dates", "")}

        if category == "theme":
            text_ok = bool((entry.get("craft_notes") or "").strip())
            return {"present": True, "text_ok": text_ok}

        return {"present": True, "text_ok": False}

    report = {
        "cultures": {slug: _status_for("culture", slug) for slug in cultures},
        "timelines": {slug: _status_for("timeline", slug) for slug in timelines},
        "themes": {slug: _status_for("theme", slug) for slug in themes},
    }

    missing = [
        f"{cat}:{slug}"
        for cat, entries in report.items()
        for slug, st in entries.items()
        if not st.get("present")
    ]
    empty_text = [
        f"{cat}:{slug}"
        for cat, entries in report.items()
        for slug, st in entries.items()
        if st.get("present") and not st.get("text_ok")
    ]

    if missing:
        logger.warning(f"Fallback DB missing entries: {missing}")
    if empty_text:
        logger.warning(f"Fallback DB has empty text fields: {empty_text}")

    return {"missing": missing, "empty_text": empty_text, "report": report}


_VISUAL_CACHE: dict[str, list] = {}


def get_visual_elements(culture: str, timeline: str) -> dict:
    cache_key = f"{culture}:{timeline}"
    if cache_key in _VISUAL_CACHE:
        return _VISUAL_CACHE[cache_key]

    result = {
        "clothing": [],
        "architecture": [],
        "artifact": [],
        "lighting": [],
        "hairstyle": [],
        "color_palette": [],
    }

    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """SELECT category, name, description, materials, colors
               FROM visual_elements
               WHERE culture = ? AND timeline = ?
               ORDER BY category, id""",
            (culture, timeline)
        )

        for row in cursor.fetchall():
            category = row["category"]
            if category not in result:
                result[category] = []
            element = {
                "name": row["name"],
                "description": row["description"] or "",
                "materials": json.loads(row["materials"]) if row["materials"] else [],
                "colors": json.loads(row["colors"]) if row["colors"] else [],
            }
            result[category].append(element)

        conn.close()
        _VISUAL_CACHE[cache_key] = result
    except Exception as e:
        logger.error(f"Failed to load visual elements: {e}")

    return result


def format_visual_elements_for_prompt(visual_data: dict) -> str:
    sections = []

    if visual_data.get("clothing"):
        items = []
        for c in visual_data["clothing"]:
            colors_str = ", ".join(c["colors"][:3]) if c["colors"] else ""
            mats_str = ", ".join(c["materials"][:3]) if c["materials"] else ""
            items.append(f'{c["name"]}: {c["description"]} (materials: {mats_str}, colors: {colors_str})')
        sections.append("CLOTHING:\n" + "\n".join(f"  - {i}" for i in items))

    if visual_data.get("architecture"):
        items = []
        for a in visual_data["architecture"]:
            colors_str = ", ".join(a["colors"][:3]) if a["colors"] else ""
            mats_str = ", ".join(a["materials"][:3]) if a["materials"] else ""
            items.append(f'{a["name"]}: {a["description"]} (materials: {mats_str}, colors: {colors_str})')
        sections.append("ARCHITECTURE:\n" + "\n".join(f"  - {i}" for i in items))

    if visual_data.get("artifact"):
        items = [f'{a["name"]}: {a["description"]}' for a in visual_data["artifact"][:5]]
        sections.append("PROPS & ARTIFACTS:\n" + "\n".join(f"  - {i}" for i in items))

    if visual_data.get("lighting"):
        items = [f'{l["name"]}: {l["description"]}' for l in visual_data["lighting"]]
        sections.append("LIGHTING:\n" + "\n".join(f"  - {i}" for i in items))

    if visual_data.get("hairstyle"):
        items = [f'{h["name"]}: {h["description"]}' for h in visual_data["hairstyle"]]
        sections.append("HAIRSTYLES:\n" + "\n".join(f"  - {i}" for i in items))

    if visual_data.get("color_palette"):
        items = []
        for p in visual_data["color_palette"]:
            colors_str = ", ".join(p["colors"]) if p["colors"] else ""
            items.append(f'{p["name"]}: {p["description"]} [{colors_str}]')
        sections.append("COLOR PALETTE:\n" + "\n".join(f"  - {i}" for i in items))

    if not sections:
        return "No specific visual reference data available for this culture+timeline combination."

    return "\n\n".join(sections)
