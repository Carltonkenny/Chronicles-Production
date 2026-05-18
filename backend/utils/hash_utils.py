import hashlib


def compute_story_hash(culture: str, timeline: str, theme: str, seed_idea: str) -> str:
    key = (
        f"{culture.lower().strip()}|"
        f"{timeline.lower().strip()}|"
        f"{theme.lower().strip()}|"
        f"{seed_idea.lower().strip()}"
    )
    return hashlib.sha256(key.encode()).hexdigest()
