"""
Chronicles Story Engine - Database Service
==========================================
Handles permanent storage for stories and characters.
Uses Supabase (PostgreSQL) if configured via environment variables.
"""

import logging
from typing import Optional, List

from config import CONFIG
from schemas import StoryOutput, StoryRequest

logger = logging.getLogger("chronicles-db-service")

try:
    from supabase import create_client, Client
    HAS_SUPABASE = True
except ImportError:
    HAS_SUPABASE = False
    Client = None

class DBService:
    def __init__(self):
        self.client: Optional[Client] = None
        if HAS_SUPABASE and CONFIG.SUPABASE_URL and CONFIG.SUPABASE_KEY:
            try:
                self.client = create_client(CONFIG.SUPABASE_URL, CONFIG.SUPABASE_KEY)
                logger.info("Supabase client initialized.")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}")
        else:
            logger.info("Supabase not configured. Permanent storage disabled.")

    async def save_story(self, request: StoryRequest, output: StoryOutput, story_hash: str) -> bool:
        """
        Saves a generated story to Supabase.
        Uses a dummy user_id for public demo if none provided.
        """
        if not self.client:
            return False

        try:
            # Prepare data (mapping Pydantic to Supabase table)
            # Note: For public demo without auth, we might use a fixed UUID or 
            # expect user_id to be passed in the request eventually.
            # Using a dummy UUID for now if it fails.
            
            story_data = {
                "story_hash": story_hash,
                "title": output.title,
                "seed_idea": request.seed_idea,
                "culture": request.culture.value,
                "timeline": request.timeline.value,
                "theme": request.theme.value,
                "setting_text": output.setting,
                "narrative_text": output.story,
                "theme_reflection": output.theme_reflection,
                "word_count": len(output.story.split()),
                "visual_prompts": output.stereotypes_flagged, # Re-purposing or skipping
                "user_id": "00000000-0000-0000-0000-000000000000" # Dummy for public demo
            }

            self.client.table("stories").upsert(story_data, on_conflict="story_hash").execute()
            
            # Save characters
            if output.characters:
                char_data = []
                for char_str in output.characters:
                    # Simple split logic (Protagonist: description)
                    if ":" in char_str:
                        name, desc = char_str.split(":", 1)
                    else:
                        name, desc = char_str, ""
                    
                    char_data.append({
                        "story_hash": story_hash,
                        "name": name.strip(),
                        "descriptor": desc.strip()
                    })
                
                if char_data:
                    self.client.table("characters").upsert(char_data).execute()

            logger.info(f"Story {story_hash[:8]} saved to Supabase.")
            return True

        except Exception as e:
            logger.error(f"Failed to save story to Supabase: {e}")
            return False

# Global instance
db_service = DBService()
