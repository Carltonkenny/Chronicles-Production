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

### For "mugshot" variation:
- Front-facing identification photograph style
- Face centered, eyes level with camera, neutral expression
- Even flat lighting, no dramatic shadows — clinical reference quality
- Plain light gray background, no props visible in frame
- Hair pulled back or clearly visible, ears showing
- Passport/ID card aesthetic: scientific documentation, not drama

### For "physique_chart" variation:
- Full body anatomical reference pose: standing straight, arms at sides, feet shoulder-width
- Measurement scale bar on left side showing height in BOTH feet/inches AND centimeters
- Clinical/medical lighting: even, shadowless, reveals body proportions and build
- Plain white or light gray cyclorama background
- Costume partially visible but physique is the primary focus
- Museum archive aesthetic: scientific accuracy over artistic drama

### For "feature_closeup" variation:
- Extreme close-up of a SINGLE distinguishing feature (scar, tattoo, eye color, hand detail, signature jewelry item)
- Macro photography style: 100mm+ equivalent, razor-thin depth of field
- The feature fills 80% of the frame — this is forensic-level detail
- Sharp focus on texture: skin pores, metal patina, fabric weave, iris detail
- Medical illustration quality lighting: ring flash or twin softboxes
- Background: completely out of focus, nearly abstract

## CRITICAL RULES
- EXACT appearance matching: eyes, hair, scars, build MUST match Character Bible
- ALL signature items MUST be visible (unless variation type explicitly excludes them)
- Colors ONLY from the provided color palette
- Culturally accurate costume for {culture} during {timeline}
- theme={theme} mood in expression (unless mugshot/physique chart — then neutral/scientific)
- style: cinematic, photorealistic, intricate details
- Output as a single paragraph, no markdown, no explanations
"""
