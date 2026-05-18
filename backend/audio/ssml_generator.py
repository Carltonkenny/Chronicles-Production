"""
SSML (Speech Synthesis Markup Language) generator.

Three-tier approach:
1. Check cache (instant if cached)
2. LLM agent with 30s timeout (emotional, dramatic)
3. Rule-based fallback (fast, reliable)
"""

import re
import asyncio
import logging
import hashlib

import httpx

from config import CONFIG

logger = logging.getLogger("chronicles-audio")


def validate_and_sanitize_ssml(ssml: str, voice_id: str = None) -> str:
    """
    Validate and sanitize SSML from LLM to fix common hallucination patterns.

    This is a defensive layer — never trust raw LLM output for Polly.

    Prosody Strategy ("strip unless proven safe"):
    - Stripping prosody never breaks audio — worst case is flat delivery
    - Keeping broken prosody crashes the entire synthesis
    - So we validate each tag and strip anything suspicious

    Args:
        ssml: Raw SSML from LLM
        voice_id: AWS Polly voice ID (for capability detection)

    Returns:
        Sanitized SSML safe for Polly
    """

    # Valid prosody attribute values (generative engine, ap-southeast-1)
    # TESTED 2026-03-02: rate ✅, volume ✅, pitch ❌ on ALL generative voices.
    VALID_RATES = {'x-slow', 'slow', 'medium', 'fast', 'x-fast'}
    VALID_VOLUMES = {'silent', 'x-soft', 'soft', 'medium', 'loud', 'x-loud'}

    def _is_valid_percentage(val: str) -> bool:
        """Check if value is a valid percentage like '80%', '+10%', '-5%'."""
        val = val.strip()
        if not val.endswith('%'):
            return False
        num_part = val[:-1]
        try:
            float(num_part)
            return True
        except ValueError:
            return False

    def _is_valid_db(val: str) -> bool:
        """Check if value is a valid dB like '+2dB', '-6dB'."""
        val = val.strip().lower()
        if not val.endswith('db'):
            return False
        num_part = val[:-2]
        try:
            float(num_part)
            return True
        except ValueError:
            return False

    def _validate_prosody_attrs(tag_str: str) -> bool:
        """
        Validate prosody tag attributes for generative engine in ap-southeast-1.

        Generative voices support: rate + volume
        NOT supported: pitch (causes InvalidSsmlException)

        Returns True if tag has at least one valid rate or volume attribute.
        """
        # Extract attribute pairs
        attrs = re.findall(r'(rate|pitch|volume)="([^"]*)"', tag_str)
        if not attrs:
            return False  # prosody with no attributes is pointless, strip it

        has_valid_attr = False
        for attr_name, attr_val in attrs:
            val = attr_val.strip().lower()
            if attr_name == 'rate':
                if val in VALID_RATES or _is_valid_percentage(val):
                    has_valid_attr = True
                else:
                    return False  # Invalid rate value
            elif attr_name == 'volume':
                if val in VALID_VOLUMES or _is_valid_db(val) or _is_valid_percentage(val):
                    has_valid_attr = True
                else:
                    return False  # Invalid volume value
            elif attr_name == 'pitch':
                pass  # pitch will be stripped in step 3.5, don't fail tag

        return has_valid_attr

    # 1. Fix double+ dots anywhere in SSML (time="0..5s" → time="0.5s")
    ssml = re.sub(r'\.{2,}', '.', ssml)

    # 2. Fix self-closing break tags: <break time="0.5s"> → <break time="0.5s"/>
    ssml = re.sub(r'<break time="([^"]*)">', r'<break time="\1"/>', ssml)

    # 3. Remove emphasis tags (NOT supported by generative engine)
    ssml = re.sub(r'<emphasis[^>]*>(.*?)</emphasis>', r'\1', ssml, flags=re.DOTALL)

    # 3.5. Strip 'pitch' attribute from prosody (NOT supported in ap-southeast-1)
    # Volume IS supported by generative engine, so we keep it.
    # <prosody rate="slow" pitch="-10%" volume="soft"> → <prosody rate="slow" volume="soft">
    ssml = re.sub(r'\s*pitch="[^"]*"', '', ssml)

    # 4. Remove amazon:effect tags (not supported for neural voices)
    ssml = re.sub(r'<amazon:effect[^>]*>(.*?)</amazon:effect>', r'\1', ssml, flags=re.DOTALL)

    # 5. Bulletproof prosody handler — "strip unless proven safe"
    def safe_prosody_handler(match):
        """
        Validate each prosody tag through 4 checks:
        1. Nested <break> tags? → STRIP (causes Polly errors)
        2. Invalid attribute values? → STRIP (causes Polly errors)
        3. All clean? → KEEP (prosody reaches Polly for expressive narration)
        """
        full_match = match.group(0)
        tag_opening = full_match[:full_match.index('>')]
        content = match.group(1)

        # Check 1: nested breaks inside prosody
        if '<break' in content:
            logger.debug("Prosody stripped: contains nested <break> tags")
            return content

        # Check 2: invalid attribute values
        if not _validate_prosody_attrs(tag_opening):
            logger.debug(f"Prosody stripped: invalid attributes in {tag_opening[:60]}")
            return content

        # All checks passed — keep prosody for expressive narration
        return full_match

    ssml = re.sub(r'<prosody[^>]*>(.*?)</prosody>', safe_prosody_handler, ssml, flags=re.DOTALL)

    # 6. Fix unclosed prosody tags (LLM hallucination)
    # Find orphaned <prosody> openers with no </prosody> and strip them
    # This runs AFTER the above handler, so only broken tags remain
    ssml = re.sub(r'<prosody[^>]*>(?!.*?</prosody>)', '', ssml, flags=re.DOTALL)

    # 7. Strip ALL existing <speak> tags and re-wrap once
    ssml = ssml.strip()
    while ssml.startswith("<speak>"):
        ssml = ssml[7:]
    while ssml.endswith("</speak>"):
        ssml = ssml[:-8]
    ssml = f"<speak>{ssml.strip()}</speak>"

    # 8. Final tag balance check (log only, don't crash)
    for tag in ['break', 'prosody']:
        open_count = ssml.count(f'<{tag}')
        close_count = ssml.count(f'</{tag}>') + len(re.findall(rf'<{tag}[^>]*/>', ssml))
        if open_count > close_count:
            logger.warning(f"SSML has {open_count - close_count} unclosed <{tag}> tags")

    return ssml


# SSML generation prompt for LLM agent
# Simpler prompt - sanitization layer catches hallucinations
# Includes thinking block for better emotional analysis
SSML_PROMPT = """
You are an expert audiobook director. Analyze the story's emotional arc, then add Amazon Polly SSML tags for dramatic, expressive narration.

STORY TEXT:
{story_text}

THEME: {theme}
CULTURE: {culture}

STEP 1: ANALYZE EMOTIONAL ARC
First, write a brief <thinking> block analyzing:
- Where are the tense moments? (use fast rate, short breaks)
- Where are the emotional beats? (use slow rate, soft volume for intimacy)
- Where are the major revelations/climaxes? (use x-slow rate, loud volume)
- Where should the narrator whisper? (use slow rate, soft volume)

STEP 2: ADD SSML TAGS
Then output the SSML-wrapped story with these tools:

1. PACING (break tags for silence)
   - <break time="0.3s"/> for rapid action, quick dialogue
   - <break time="0.5s"/> for normal sentence gaps
   - <break time="1.0s"/> for emotional beats, scene transitions
   - <break time="2.0s"/> before revelations, climax moments

2. PROSODY (rate + volume for vocal expression)
   Use <prosody> to make narration sound ALIVE, not robotic.
   Supported attributes: rate and volume. Do NOT use pitch (unsupported).

   Whispers / secrets (soft + slow = intimate):
     <prosody rate="slow" volume="soft">She whispered the truth.</prosody>

   Action / urgency (fast = tension):
     <prosody rate="fast">He ran through the flames!</prosody>

   Dramatic revelation (extra slow + loud = maximum impact):
     <prosody rate="x-slow" volume="loud">The king was dead.</prosody>

   Panic / shouting (fast + loud = chaos):
     <prosody rate="fast" volume="loud">"RUN!"</prosody>

   Somber / reflective (slow + soft = emotional weight):
     <prosody rate="slow" volume="soft">The village lay in ashes.</prosody>

   Dialogue (medium for clarity):
     <prosody rate="medium">"Why did you betray us?"</prosody>

   Valid rate values: x-slow, slow, medium, fast, x-fast
   Valid volume values: x-soft, soft, medium, loud, x-loud
   Do NOT use pitch attribute (causes errors).

CONSTRAINTS:
- Use ONLY: <break>, <prosody>, <speak>, <thinking>
- Prosody supports: rate, volume. Do NOT use pitch.
- Do NOT use: <emphasis>, <amazon:effect>, <phoneme>
- Do NOT nest <break> inside <prosody> (causes errors)
- Close EVERY <prosody> tag with </prosody>
- Wrap output in <speak>...</speak>
- Preserve original text exactly — only add tags around it
- Use prosody 4-8 times per passage for variety without overdoing it

OUTPUT FORMAT:
<speak>
<thinking>
[Brief analysis of emotional arc and prosody decisions]
</thinking>
[Story with SSML tags]
</speak>

EXAMPLE:
<speak>
<thinking>
This is a betrayal story. Opening is calm (slow, soft). Tension builds (medium, then fast). The revelation needs silence + loud slow delivery. Ending is somber (slow, soft).
</thinking>
The wind howled.<break time="1.0s"/>
<prosody rate="slow" volume="soft">Priya stood at the cliff's edge, staring into the abyss.</prosody><break time="0.5s"/>
<prosody rate="medium">"We must go back,"</prosody> she whispered.<break time="0.3s"/>
<prosody rate="fast">Her footsteps echoed as she turned and ran.</prosody><break time="2.0s"/>
<prosody rate="x-slow" volume="loud">The village was burning.</prosody>
</speak>
"""


async def generate_ssml_llm(story_text: str, theme: str, culture: str, timeout: float = 30.0) -> str:
    """
    Generate SSML using LLM agent.
    
    Args:
        story_text: Story text to convert to SSML
        theme: Story theme (e.g., "betrayal", "hope")
        culture: Culture code (e.g., "egyptian", "chola")
        timeout: Maximum seconds to wait for LLM response
    
    Returns:
        SSML-formatted text
    
    Raises:
        asyncio.TimeoutError: If LLM takes longer than timeout
        Exception: If LLM call fails
    """
    prompt = SSML_PROMPT.format(
        story_text=story_text[:4000],  # Truncate very long stories
        theme=theme,
        culture=culture,
    )
    
    payload = {
        "model": CONFIG.POLLINATIONS_MODEL,
        "messages": [
            {"role": "system", "content": "You are an expert audiobook director. Output ONLY SSML-wrapped text."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,  # Lower temperature for more consistent SSML
    }
    
    headers = {"Content-Type": "application/json"}
    if CONFIG.POLLINATIONS_API_KEY:
        headers["Authorization"] = f"Bearer {CONFIG.POLLINATIONS_API_KEY}"
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            CONFIG.POLLINATIONS_BASE_URL,
            json=payload,
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()
        raw_ssml = data["choices"][0]["message"]["content"]

        # Strip <thinking> block (internal analysis, not for Polly)
        ssml = re.sub(r'<thinking>.*?</thinking>', '', raw_ssml, flags=re.DOTALL).strip()

        # Strip any existing <speak> tags, then re-wrap cleanly (prevents double <speak>)
        ssml = ssml.strip()
        if ssml.startswith("<speak>"):
            ssml = ssml[7:]
        if ssml.endswith("</speak>"):
            ssml = ssml[:-8]
        ssml = f"<speak>{ssml.strip()}</speak>"

        return ssml


def generate_ssml_rule_based(story_text: str) -> str:
    """
    Generate SSML using simple regex rules.
    
    Fast fallback when LLM fails or times out.
    Preserves paragraph breaks from the original text.
    
    Args:
        story_text: Story text to convert to SSML
    
    Returns:
        SSML-formatted text
    """
    text = story_text
    
    # Escape any existing SSML tags in the text (prevent injection)
    text = text.replace('<', '&lt;').replace('>', '&gt;')
    
    # Pause after sentences (0.5s) - DON'T add extra period, text already has one
    text = re.sub(r'\. ', r'<break time="0.5s"/> ', text)
    text = re.sub(r'\! ', r'<break time="0.5s"/> ', text)
    text = re.sub(r'\? ', r'<break time="0.5s"/> ', text)
    
    # Longer pause at paragraph breaks (2.0s)
    text = text.replace('\n\n', '<break time="2.0s"/>')
    
    # Wrap in speak tags
    return f"<speak>{text}</speak>"


async def generate_ssml(story_text: str, theme: str, culture: str, voice_id: str, audio_cache=None) -> tuple[str, str]:
    """
    Generate SSML with caching, LLM (30s timeout), and rule-based fallback.

    Args:
        story_text: Story text to convert to SSML
        theme: Story theme
        culture: Culture code
        voice_id: AWS Polly voice ID (for cache key)
        audio_cache: AudioCache instance (optional, for SSML caching)

    Returns:
        Tuple of (SSML-formatted text, source: "cache", "llm", or "rule-based")
    """
    # Compute cache key from story text
    story_hash = hashlib.sha256(story_text.encode()).hexdigest()[:16]

    # Tier 1: Check cache
    if audio_cache and audio_cache.ssml_exists(story_hash):
        logger.info(f"SSML cache hit for story {story_hash[:8]}...")
        ssml = audio_cache.get_ssml(story_hash)
        return ssml, "cache"

    # Tier 2: Try LLM with 30-second timeout
    try:
        logger.info("Generating SSML with LLM agent (30s timeout)...")
        raw_ssml = await asyncio.wait_for(
            generate_ssml_llm(story_text, theme, culture, timeout=30.0),
            timeout=30.0
        )

        # SANITIZE: Never trust raw LLM output
        ssml = validate_and_sanitize_ssml(raw_ssml)

        logger.info(f"LLM SSML generated and sanitized ({len(ssml)} chars)")

        # Cache the sanitized result (non-fatal if this fails)
        if audio_cache:
            try:
                audio_cache.save_ssml(story_hash, ssml)
            except Exception as cache_err:
                logger.warning(f"SSML cache save failed (non-fatal): {cache_err}")

        return ssml, "llm"

    except asyncio.TimeoutError:
        logger.warning("LLM SSML timed out after 30s, using rule-based fallback")

    except Exception as e:
        logger.error(f"LLM SSML failed: {e}, using rule-based fallback")

    # Tier 3: Rule-based fallback
    ssml = generate_ssml_rule_based(story_text)
    logger.info(f"Rule-based SSML generated ({len(ssml)} chars)")

    # Cache the result (non-fatal if this fails)
    if audio_cache:
        try:
            audio_cache.save_ssml(story_hash, ssml)
        except Exception as cache_err:
            logger.warning(f"SSML cache save failed (non-fatal): {cache_err}")

    return ssml, "rule-based"
