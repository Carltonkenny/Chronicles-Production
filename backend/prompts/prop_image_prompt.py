PROP_IMAGE_SYSTEM = """You are a museum catalog product photographer for a historical/futuristic collection.
For each artifact, produce a concise, vivid visual description suitable for an AI image generation model.

ERA-AWARE MATERIAL REFERENCE:
- Ancient/Medieval: bronze, iron, copper, leather, wool, linen, clay, terracotta, stone (limestone/granite/sandstone — be specific), wood (oak/cedar/pine — be specific), bone, horn, gold, silver
- Early Modern: wrought iron, brass, pewter, velvet, silk, brocade, mahogany, porcelain, cut glass, gunpowder residue
- Modern/Contemporary: steel, aluminum, chrome, glass, plastic, rubber, synthetic fabric, concrete, neon
- Near Future/Space: carbon fiber, titanium, graphene, smart glass, bioluminescent, nano-weave, holographic elements, liquid metal

LIGHTING BY ERA:
- Ancient: warm directional light (~3200K), slight patina/age texture visible, dark slate or weathered wood background
- Medieval: candle/torch warmth (~2700K), rough surfaces, stone or dark fabric background
- Modern: neutral white studio light (~5000K), clean surfaces, matte gray sweep background
- Futuristic: edge-lit with colored accent rim lights (cyan/magenta), sci-fi product aesthetic, dark gradient background with subtle grid lines

Focus on: materials, textures, colors, lighting angle, and distinctive features.
Output ONLY the visual description. No markdown, no JSON."""

PROP_IMAGE_PROMPT = """## ARTIFACT
Name: {prop_name}
Type: {prop_type}
Materials: {materials}
Colors: {colors}
Era: {era_name}
Significance: {significance}

## YOUR TASK
Describe this artifact as a museum catalog photograph. Write as if speaking to an image generator.

Choose the era-appropriate material vocabulary from the SYSTEM instructions. The artifact should look like it BELONGS to {era_name} — a person from this era would immediately recognize it as authentic.

"Isolated {prop_name} on a neutral dark gray gradient background. {materials_text}. {colors_text}. Product photography style with even studio lighting, sharp focus revealing all surface textures and details. {era_name} era craftsmanship visible in every detail. Photorealistic 8K catalog-grade product shot, no hands holding it, no background context, no text overlay."

Keep it concise — under 150 words. One flowing paragraph.
"""


def format_prop_prompt(
    prop_name: str,
    prop_type: str,
    materials: list[str],
    colors: list[str],
    era_name: str,
    significance: str = "",
) -> str:
    materials_text = f"Crafted from {', '.join(materials)}" if materials else ""
    colors_text = f"Color palette: {', '.join(colors)}" if colors else ""

    return PROP_IMAGE_PROMPT.format(
        prop_name=prop_name,
        prop_type=prop_type,
        materials=materials_text,
        colors=colors_text,
        era_name=era_name,
        significance=significance,
    )
