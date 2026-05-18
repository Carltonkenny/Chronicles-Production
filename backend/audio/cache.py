"""
Audio file caching service.

Stores generated MP3 files and SSML for instant replay.
Cache directories are resolved relative to this file's location (not cwd).
"""

import hashlib
from pathlib import Path
import logging

logger = logging.getLogger("chronicles-audio")


class AudioCache:
    """
    Simple file-based cache for generated audio and SSML.

    Stores MP3 files in backend/audio_cache/audio/ directory.
    Stores SSML files in backend/audio_cache/ssml/ directory.
    Cache keys are SHA-256 hashes of story text + voice ID.
    """

    def __init__(self, cache_dir: str = "audio_cache"):
        """
        Initialize cache directories with absolute paths.

        Args:
            cache_dir: Directory name for cache (relative to backend/)
        """
        # Resolve cache directory relative to THIS file's location (not cwd)
        base_path = Path(__file__).parent / cache_dir
        self.cache_dir = base_path.resolve()
        self.audio_dir = self.cache_dir / "audio"
        self.ssml_dir = self.cache_dir / "ssml"
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.ssml_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Audio cache initialized at {self.cache_dir}")
        logger.info(f"SSML cache initialized at {self.ssml_dir}")
    
    def compute_hash(self, story_text: str, voice_id: str) -> str:
        """
        Compute cache key from story text and voice ID.
        
        Args:
            story_text: Full story text
            voice_id: AWS Polly voice ID
        
        Returns:
            SHA-256 hash string (first 16 chars for filename)
        """
        content = f"{story_text}:{voice_id}".encode()
        full_hash = hashlib.sha256(content).hexdigest()
        return full_hash[:16]  # Use first 16 chars for shorter filenames
    
    def get_path(self, story_hash: str) -> Path:
        """
        Get file path for a cached audio file.
        
        Args:
            story_hash: Story hash (from compute_hash)
        
        Returns:
            Path to MP3 file
        """
        return self.cache_dir / f"{story_hash}.mp3"
    
    def exists(self, story_hash: str) -> bool:
        """
        Check if audio is cached.
        
        Args:
            story_hash: Story hash
        
        Returns:
            True if cached, False otherwise
        """
        return self.get_path(story_hash).exists()
    
    def get(self, story_hash: str) -> bytes | None:
        """
        Retrieve cached audio data.
        
        Args:
            story_hash: Story hash
        
        Returns:
            MP3 data as bytes, or None if not cached
        """
        path = self.get_path(story_hash)
        if not path.exists():
            return None
        
        try:
            audio_data = path.read_bytes()
            logger.debug(f"Cache hit for story {story_hash} ({len(audio_data)} bytes)")
            return audio_data
        except Exception as e:
            logger.error(f"Error reading cached audio: {e}")
            return None
    
    def save(self, story_hash: str, audio_data: bytes) -> Path:
        """
        Save audio data to cache.

        Args:
            story_hash: Story hash
            audio_data: MP3 data as bytes

        Returns:
            Path to saved file
        """
        path = self.get_path(story_hash)
        try:
            path.write_bytes(audio_data)
            logger.debug(f"Saved {len(audio_data)} bytes to cache: {story_hash}")
            return path
        except Exception as e:
            logger.error(f"Error saving audio to cache: {e}")
            raise

    # SSML caching methods
    def get_ssml_path(self, story_hash: str) -> Path:
        """
        Get file path for a cached SSML file.

        Args:
            story_hash: Story hash

        Returns:
            Path to SSML file
        """
        return self.ssml_dir / f"{story_hash}.xml"

    def ssml_exists(self, story_hash: str) -> bool:
        """
        Check if SSML is cached.

        Args:
            story_hash: Story hash

        Returns:
            True if cached, False otherwise
        """
        return self.get_ssml_path(story_hash).exists()

    def get_ssml(self, story_hash: str) -> str | None:
        """
        Retrieve cached SSML.

        Args:
            story_hash: Story hash

        Returns:
            SSML text, or None if not cached
        """
        path = self.get_ssml_path(story_hash)
        if not path.exists():
            return None

        try:
            ssml = path.read_text(encoding='utf-8')
            logger.debug(f"SSML cache hit for story {story_hash}")
            return ssml
        except Exception as e:
            logger.error(f"Error reading cached SSML: {e}")
            return None

    def save_ssml(self, story_hash: str, ssml: str) -> Path:
        """
        Save SSML to cache.

        Args:
            story_hash: Story hash
            ssml: SSML text

        Returns:
            Path to saved file
        """
        path = self.get_ssml_path(story_hash)
        try:
            path.write_text(ssml, encoding='utf-8')
            logger.debug(f"Saved SSML to cache: {story_hash}")
            return path
        except Exception as e:
            logger.error(f"Error saving SSML to cache: {e}")
            raise
