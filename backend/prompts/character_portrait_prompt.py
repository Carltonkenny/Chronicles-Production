CHARACTER_PORTRAIT_PROMPT = """
You are a character portrait designer for AI image generation. Create a detailed visual description of a single character for a Pollinations Flux prompt.

## CHARACTER BIBLE
**Name:** {name}
**Role:** {role}
**Appearance:** {appearance}
**Costume:** {costume}
**Signature Items:** {signature_items}
**Emotional Range:** {emotional_range}

## FILM CONTEXT
**Culture:** {culture}
**Timeline:** {timeline}
**Theme:** {theme}
**Film Tone:** {film_tone}
**Color Palette:** {color_palette}
**Lighting Style:** {lighting_style}

## YOUR TASK

Create a single vivid character prompt for variation type: **{variation_type}**

### For "full_body" variation:
- Full body standing pose, camera at eye level
- Show complete costume from head to toe
- All signature items MUST be visible
- Neutral expression, character faces camera slightly off-center
- Background should hint at setting (blurred)

### For "close_up" variation:
- Intimate portrait from chest up, 85mm lens equivalent
- EMOTION from story visible in eyes and micro-expressions
- Lighting highlights character's key facial features
- Signature items visible at shoulders/neck if wearable
- Shallow depth of field, background soft blur

### For "action" variation:
- Dynamic pose showing character in a key story moment
- Medium shot (waist up) or full body action pose
- Signature items in USE (hammer swinging, sword drawn, etc.)
- Motion implied through posture and clothing
- Environment visible (where the action happens)

## CRITICAL RULES
- EXACT appearance matching: eyes, hair, scars, build MUST match Character Bible
- ALL signature items MUST be visible
- Colors ONLY from the provided color palette
- Culturally accurate costume for {culture} during {timeline}
- theme={theme} mood in expression
- style: cinematic, photorealistic, intricate details
- Output as a single paragraph, no markdown, no explanations
"""
