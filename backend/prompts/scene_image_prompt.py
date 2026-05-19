SCENE_IMAGE_PROMPT = """
You are a cinematographer designing keyframe images for a film scene. Create a detailed visual description for a Pollinations Flux image prompt.

## SCENE DATA
**Scene ID:** {scene_id}
**Summary:** {summary}
**Location:** {location}
**Characters Present:** {characters}
**Emotional Beat:** {emotional_beat}

## LOCATION DETAILS
**Architecture:** {architecture}
**Materials:** {materials}
**Lighting:** {lighting}
**Time of Day:** {time_of_day}

## FILM CONTEXT
**Culture:** {culture}
**Timeline:** {timeline}
**Theme:** {theme}
**Film Tone:** {film_tone}
**Color Palette:** {color_palette}
**Lighting Style:** {lighting_style}

## YOUR TASK

Create a single cinematic scene description for Pollinations Flux (16:9 landscape).

### Include ALL of these elements:
1. **Location:** Describe the physical space in detail (architecture, materials, condition)
2. **Lighting:** Exact light source (sun, fire, lamps), quality (warm, cool, dramatic), direction
3. **Time of Day:** Dawn, midday, dusk, or night — reflected in color temperature
4. **Color Palette:** 3-5 specific colors from the film palette that dominate this scene
5. **Atmosphere:** Smoke, mist, haze, rain, snow, clear — mood-setting weather/effects
6. **Characters:** Brief description of each character's position and action (if present)
7. **Cultural Markers:** 2-3 specific items that identify {culture} {timeline}
8. **Camera:** Wide establishing shot, 35mm equivalent, deep depth of field
9. **Composition:** Foreground objects, middle ground action, background elements

## CRITICAL RULES
- Architecture and materials MUST match {culture} {timeline}
- Colors ONLY from the provided palette
- Characters present in scene: {characters} — describe their positions and actions
- Emotional beat: {emotional_beat} — reflect this in the visual mood
- style: cinematic wide shot, anamorphic lens, 8K, photorealistic, atmospheric
- Output as a single paragraph, no markdown, no explanations
"""
