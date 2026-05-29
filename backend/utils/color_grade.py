from typing import Optional

WARM_PALETTE_KEYS = {"amber", "gold", "orange", "red", "crimson", "ochre", "bronze", "copper", "rust", "sepia"}
COOL_PALETTE_KEYS = {"blue", "teal", "cyan", "indigo", "navy", "slate", "steel", "ice", "azure", "lavender"}
DARK_TONES = {"dark", "gritty", "noir", "gothic", "horror", "tragic", "somber", "brutal"}
BRIGHT_TONES = {"bright", "vibrant", "heroic", "epic", "adventure", "fantasy", "triumphant", "hopeful"}


def compute_grading_spec(color_palette: Optional[dict] = None,
                         film_tone: str = "",
                         lighting_style: str = "") -> dict:
    palette = color_palette or {}
    primary = palette.get("primary", [])
    accent = palette.get("accent", [])

    all_colors = " ".join(primary + accent).lower()

    temperature_offset = 0.0
    for kw in WARM_PALETTE_KEYS:
        if kw in all_colors:
            temperature_offset += 300.0
            break
    for kw in COOL_PALETTE_KEYS:
        if kw in all_colors:
            temperature_offset -= 300.0
            break

    contrast = 1.02
    tone_lower = film_tone.lower()
    for kw in DARK_TONES:
        if kw in tone_lower:
            contrast = 1.06
            break
    for kw in BRIGHT_TONES:
        if kw in tone_lower:
            contrast = 1.03
            break

    saturation = 1.0
    if "vibrant" in tone_lower or "epic" in tone_lower:
        saturation = 1.08
    elif "dark" in tone_lower or "gritty" in tone_lower:
        saturation = 0.92

    brightness = 0.0
    if "dark" in tone_lower or "noir" in tone_lower:
        brightness = -0.02
    elif "bright" in tone_lower:
        brightness = 0.02

    vignette = 0.25 if "gritty" in tone_lower or "noir" in tone_lower else 0.12

    return {
        "brightness": round(brightness, 3),
        "contrast": round(contrast, 3),
        "saturation": round(saturation, 3),
        "temperature_offset": round(temperature_offset),
        "vignette": round(vignette, 3),
    }
