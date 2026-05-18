"""
Amazon Polly TTS service integration.

Handles authentication, voice selection, and speech synthesis.
"""

import boto3
from botocore.exceptions import NoCredentialsError, ClientError
import logging
import re

from config import CONFIG

logger = logging.getLogger("chronicles-audio")


# =============================================================================
# VOICE MAPPING - AWS Polly (ap-southeast-1 / Singapore Region)
# =============================================================================
# All voices use GENERATIVE engine — highest quality, most natural.
# Generative supports: rate + volume (NOT pitch).
# Fallback: "Amy" (British English, generative) for unmapped cultures.
#
# TESTED 2026-03-02: All 33 generative voices confirmed working.
# Prosody Support (generative engine in ap-southeast-1):
#   rate:   ✅ x-slow, slow, medium, fast, x-fast
#   volume: ✅ x-soft, soft, medium, loud, x-loud
#   pitch:  ❌ Unsupported (causes InvalidSsmlException)
# =============================================================================

VOICE_MAP = {
    # ==========================================================================
    # INDIAN SUBCONTINENT (4 cultures)
    # Voice: Kajal (en-IN, Indian English accent, generative)
    # ==========================================================================
    "chola": "Kajal",               # South India, Tamil Empire (900-1300 CE)
    "mughal": "Kajal",              # North India, Mughal Empire (1526-1857 CE)
    "mauryan": "Kajal",             # Ancient India, Mauryan Empire (322-185 BCE)
    "east_india_company": "Kajal",  # Colonial India (1600-1858 CE)

    # ==========================================================================
    # MIDDLE EAST & NORTH AFRICA (7 cultures)
    # Stephen (en-US, Male, generative) — warm, storyteller tone
    # Ayanda (en-ZA, Female, generative) — authentic African accent
    # Note: Hala (ar-AE) is neural-only, no generative Arabic voice available
    # ==========================================================================
    "egyptian": "Stephen",          # Warm storyteller for ancient Egypt
    "persian": "Stephen",           # Deep narration for Persia
    "ottoman": "Stephen",           # Authoritative for Ottoman Empire
    "mesopotamian": "Matthew",      # Deep, epic for ancient Mesopotamia
    "mali_empire": "Ayanda",        # South African accent for West Africa
    "swahili_coast": "Ayanda",      # South African accent for East Africa
    "yoruba": "Ayanda",             # South African accent for Yoruba

    # ==========================================================================
    # EAST ASIA (2 cultures)
    # Ruth (en-US, Female, generative) — calm, measured delivery
    # Note: Takumi/Zhiyu are neural-only, no generative JP/CN voices
    # ==========================================================================
    "japanese": "Ruth",             # Calm, measured for Japanese stories
    "tang_dynasty": "Ruth",         # Calm, measured for Chinese stories

    # ==========================================================================
    # EUROPE (5 cultures)
    # ==========================================================================
    "ancient_greek": "Amy",         # en-GB, British English, generative
    "byzantine": "Amy",             # en-GB, British English, generative
    "roman": "Bianca",              # it-IT, Italian accent, generative!
    "viking": "Matthew",            # en-US, Male, deep epic voice, generative
    "celtic": "Niamh",              # en-IE, Irish accent, generative!

    # ==========================================================================
    # MESOAMERICA & ANDES (3 cultures)
    # Voice: Lupe (es-US, Spanish accent, generative)
    # ==========================================================================
    "aztec": "Lupe",                # Aztec Empire (1345-1521 CE)
    "maya": "Lupe",                 # Maya Civilization (2000 BCE-1697 CE)
    "andean": "Lupe",               # Inca, Peru, Andes (3000 BCE-1572 CE)

    # ==========================================================================
    # PACIFIC (1 culture)
    # Voice: Olivia (en-AU, Australian English, generative)
    # ==========================================================================
    "polynesian": "Olivia",         # en-AU, closest Pacific voice
}

# Voice capability matrix for SSML feature detection
# TESTED 2026-03-02 against ap-southeast-1 (100 voices, 63 neural, 33 generative):
#
# NEURAL engine:
#   rate: ✅    pitch: ❌    volume: ❌    break: ✅
#
# GENERATIVE engine:
#   rate: ✅    pitch: ❌    volume: ✅    break: ✅
#   (volume=soft for whispers, rate+volume combo works)
#
# pitch causes InvalidSsmlException on ALL engines in ap-southeast-1.
VOICE_CAPABILITIES = {
    "neural": {
        "prosody_rate": True,      # <prosody rate="slow|medium|fast">
        "prosody_pitch": False,    # ❌ Unsupported Neural feature
        "prosody_volume": False,   # ❌ Unsupported Neural feature
        "break_tags": True,        # <break time="Xs"/>
        "emphasis": False,
        "amazon_effect": False,
    },
    "generative": {
        "prosody_rate": True,      # ✅ rate works
        "prosody_pitch": False,    # ❌ pitch still fails
        "prosody_volume": True,    # ✅ volume works! (whispers, loud)
        "break_tags": True,
        "emphasis": False,
        "amazon_effect": False,
    },
    "standard": {
        "prosody_rate": True,
        "prosody_pitch": False,
        "prosody_volume": True,    # standard voices DO support volume
        "break_tags": True,
        "emphasis": True,
        "amazon_effect": False,
    }
}


def get_voice_capabilities(voice_id: str) -> dict:
    """
    Get SSML feature capabilities for a specific voice.
    
    Production systems use feature detection to enable advanced SSML
    features safely. This prevents synthesis errors when voices don't
    support certain tags.
    
    Args:
        voice_id: AWS Polly voice ID (e.g., "Kajal", "Hala", "Amy")
    
    Returns:
        Dict of supported SSML features
    """
    # All voices in our voice map are neural - they all support full prosody
    # This is verified against ap-southeast-1 region documentation
    return VOICE_CAPABILITIES["neural"].copy()


def supports_prosody(voice_id: str) -> bool:
    """
    Check if a voice supports prosody tags (rate, pitch, volume).
    
    All neural voices in ap-southeast-1 support prosody.
    This is a convenience wrapper for template conditionals.
    
    Args:
        voice_id: AWS Polly voice ID
    
    Returns:
        True if voice supports prosody tags
    """
    capabilities = get_voice_capabilities(voice_id)
    return (
        capabilities.get("prosody_rate", False) or
        capabilities.get("prosody_pitch", False) or
        capabilities.get("prosody_volume", False)
    )


class PollyService:
    """
    Amazon Polly TTS service.
    
    Synthesizes speech from SSML text using culturally-matched English voices.
    Falls back gracefully if credentials are missing or API fails.
    """
    
    def __init__(self):
        """
        Initialize Polly client with AWS credentials from config.
        
        Sets available=False if credentials are missing/invalid.
        """
        self.available = False
        
        try:
            self.client = boto3.client(
                "polly",
                region_name=CONFIG.AWS_REGION,
                aws_access_key_id=CONFIG.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=CONFIG.AWS_SECRET_ACCESS_KEY,
            )
            # Test connection with a simple call
            self.client.describe_voices()
            self.available = True
            logger.info(f"Polly service initialized (region: {CONFIG.AWS_REGION})")
        except NoCredentialsError:
            logger.error("AWS credentials not found, Polly disabled")
        except ClientError as e:
            logger.error(f"Polly client error: {e}, Polly disabled")
        except Exception as e:
            logger.error(f"Unexpected error initializing Polly: {e}, Polly disabled")
    
    def get_voice_for_culture(self, culture: str) -> str:
        """
        Get AWS Polly voice ID for a given culture.
        
        Args:
            culture: Culture code (e.g., "egyptian", "chola")
        
        Returns:
            Voice ID string (e.g., "Hala", "Raveena")
        
        Note:
            Falls back to "Amy" (British English) if culture not found.
        """
        return VOICE_MAP.get(culture, "Amy")
    
    async def synthesize(self, ssml: str, voice_id: str) -> bytes:
        """
        Synthesize speech from SSML text.
        
        Handles long SSML by chunking into 2500-character segments.
        
        Args:
            ssml: SSML-formatted text to synthesize
            voice_id: AWS Polly voice ID (e.g., "Hala", "Raveena")
        
        Returns:
            MP3 audio data as bytes
        
        Raises:
            PollyError: If synthesis fails
        """
        if not self.available:
            raise PollyError("Polly service not available")
        
        # Polly has 3000 char limit, use 2500 for safety
        MAX_CHUNK_SIZE = 2500
        
        # If SSML is short enough, synthesize directly
        if len(ssml) <= MAX_CHUNK_SIZE:
            return await self._synthesize_chunk(ssml, voice_id)
        
        # Otherwise, split into chunks and concatenate
        logger.info(f"SSML too long ({len(ssml)} chars), splitting into chunks...")
        chunks = self._split_ssml(ssml, MAX_CHUNK_SIZE)
        logger.info(f"Split into {len(chunks)} chunks")
        
        if len(chunks) == 1 and len(chunks[0]) > MAX_CHUNK_SIZE:
            logger.error(f"Chunking failed: single chunk still too large ({len(chunks[0])} chars)")
            # Fall back to truncating
            ssml = ssml[:MAX_CHUNK_SIZE]
            return await self._synthesize_chunk(f"<speak>{ssml}</speak>", voice_id)
        
        audio_chunks = []
        for i, chunk in enumerate(chunks):
            logger.debug(f"Synthesizing chunk {i+1}/{len(chunks)} ({len(chunk)} chars)...")
            try:
                audio_data = await self._synthesize_chunk(chunk, voice_id)
                audio_chunks.append(audio_data)
            except PollyError as e:
                logger.error(f"Chunk {i+1} failed: {e}")
                raise
        
        # Concatenate all audio chunks
        logger.info(f"Successfully synthesized {len(chunks)} chunks, total {sum(len(c) for c in audio_chunks)} bytes")
        return b''.join(audio_chunks)
    
    async def _synthesize_chunk(self, ssml: str, voice_id: str) -> bytes:
        """Synthesize a single SSML chunk."""
        try:
            logger.debug(f"Synthesizing chunk ({len(ssml)} chars): {ssml[:200]}...")
            response = self.client.synthesize_speech(
                Text=ssml,
                TextType="ssml",
                VoiceId=voice_id,
                OutputFormat="mp3",
                SampleRate="22050",
                Engine="generative",
            )
            
            audio_data = response["AudioStream"].read()
            logger.debug(f"Synthesized {len(audio_data)} bytes for voice {voice_id}")
            return audio_data
            
        except ClientError as e:
            logger.error(f"Polly API error: {e}")
            logger.error(f"Invalid SSML was: {ssml[:500]}...")
            raise PollyError(f"Failed to synthesize speech: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during synthesis: {e}")
            raise PollyError(f"Synthesis failed: {e}")
    
    def _split_ssml(self, ssml: str, max_size: int) -> list[str]:
        """
        Split long SSML into chunks at sentence boundaries.

        Simple, reliable chunking for Polly's 3000-char limit.
        Ensures each chunk is valid SSML with proper tag balancing.

        Args:
            ssml: Full SSML text (may or may not have <speak> tags)
            max_size: Maximum chunk size in characters

        Returns:
            List of valid SSML chunks (each wrapped in <speak> tags)
        """
        # Remove outer <speak> tags if present
        ssml = ssml.strip()
        if ssml.startswith("<speak>"):
            ssml = ssml[7:]
        if ssml.endswith("</speak>"):
            ssml = ssml[:-8]

        # Simple approach: split on sentence boundaries, accumulate until max_size
        chunks = []
        current_chunk = ""

        # Split on sentence endings (keep the delimiter)
        # Negative lookbehind: don't split on dots preceded by digits (e.g., 0.5s in break tags)
        sentences = re.split(r'((?<![0-9])[.!?]\s*)', ssml)

        for i, part in enumerate(sentences):
            # Skip odd indices (delimiters) — already consumed by the even index before them
            if i % 2 == 1:
                continue
            if not part.strip():
                continue

            # Reconstruct: sentence text + its punctuation delimiter
            if i + 1 < len(sentences):
                sentence = part + sentences[i + 1]
            else:
                sentence = part

            # If this sentence fits, add it
            if len(current_chunk) + len(sentence) <= max_size:
                current_chunk += sentence
            else:
                # Save current chunk and start new one
                if current_chunk.strip():
                    chunks.append(f"<speak>{current_chunk.strip()}</speak>")
                current_chunk = sentence

        # Don't forget the last chunk
        if current_chunk.strip():
            chunks.append(f"<speak>{current_chunk.strip()}</speak>")

        # Fallback: if somehow we still have no chunks, return the whole thing
        return chunks if chunks else [f"<speak>{ssml}</speak>"]


class PollyError(Exception):
    """Custom exception for Polly service errors."""
    pass


def get_voice_for_culture(culture: str) -> str:
    """
    Get AWS Polly voice ID for a given culture.
    
    Convenience function for use without instantiating PollyService.
    
    Args:
        culture: Culture code (e.g., "egyptian", "chola")
    
    Returns:
        Voice ID string (e.g., "Hala", "Raveena")
    """
    return VOICE_MAP.get(culture, "Amy")
