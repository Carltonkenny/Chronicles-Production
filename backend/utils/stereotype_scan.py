import logging

logger = logging.getLogger("chronicles-tools")

STEREOTYPE_PATTERNS = {
    "south_asian": [
        "snake charmer", "mystic guru", "exotic east", "cow worship",
        "arranged marriage forced", "curry spice", "third world poverty",
    ],
    "middle_eastern": [
        "harem", "tyrannical sultan", "oppressive empire", "mystical genie",
    ],
    "east_asian": [
        "honor suicide", "mystical zen", "kung fu", "geisha pleasure",
    ],
    "mesoamerican": [
        "bloodthirsty savage", "human sacrifice obsessed", "primitive ritual",
    ],
    "european_ancient": [
        "barbarian tribe", "druid sacrifice", "horned helmet", "rape and pillage",
    ],
    "generic": [
        "wise old elder", "magical negro", "damsel in distress",
        "chosen one", "dark lord",
    ],
    "west_african": [
        "primitive tribe", "mud hut village", "jungle kingdom", "dark continent",
        "no written culture", "savage ritual", "tribal warfare only", "no cities or trade",
    ],
    "east_african": [
        "poverty stricken coast", "fishing village", "no urban culture", "backward settlement",
        "pre-contact isolation",
    ],
    "oceanic": [
        "noble savage", "simple island life", "primitive navigator", "nature worshipper",
        "peaceful primitive", "unspoiled native", "mystical islander",
    ],
    "indigenous_spiritual": [
        "ancient mystical wisdom", "one with nature", "spiritual guide to outsiders",
        "magical elder", "timeless primitive spirituality", "nature shaman",
    ],
    "colonial_default": [
        "white savior", "civilizing mission", "bringing order", "native gratitude",
        "backward locals", "primitive customs", "benevolent colonizer",
    ],
    "court_exotic": [
        "mysterious east", "exotic palace", "veiled mystery", "decadent empire",
        "oriental splendor", "despotic sultan", "opulent excess",
    ],
}

CULTURE_STEREOTYPE_MAP = {
    "roman": ["european_ancient", "generic"],
    "ancient_greek": ["european_ancient", "generic"],
    "egyptian": ["middle_eastern", "generic"],
    "viking": ["european_ancient", "generic"],
    "japanese": ["east_asian", "generic"],
    "persian": ["middle_eastern", "generic"],
    "aztec": ["mesoamerican", "generic"],
    "celtic": ["european_ancient", "generic"],
    "mughal": ["south_asian", "court_exotic", "generic"],
    "mauryan": ["south_asian", "generic"],
    "chola": ["south_asian", "generic"],
    "east_india_company": ["south_asian", "colonial_default", "generic"],
    "ottoman": ["middle_eastern", "court_exotic", "generic"],
    "byzantine": ["middle_eastern", "court_exotic", "generic"],
    "tang_dynasty": ["east_asian", "generic"],
    "mali_empire": ["west_african", "generic"],
    "swahili_coast": ["east_african", "generic"],
    "yoruba": ["west_african", "indigenous_spiritual", "generic"],
    "maya": ["mesoamerican", "generic"],
    "andean": ["mesoamerican", "generic"],
    "polynesian": ["oceanic", "indigenous_spiritual", "generic"],
    "mesopotamian": ["middle_eastern", "generic"],
}


def scan_for_stereotypes(text: str) -> list[str]:
    text_lower = text.lower()
    flagged: list[str] = []

    for category, patterns in STEREOTYPE_PATTERNS.items():
        for pattern in patterns:
            if pattern in text_lower:
                flagged.append(f"Potential {category} stereotype: '{pattern}'")

    return flagged


def get_culture_traps(culture: str) -> str:
    categories = CULTURE_STEREOTYPE_MAP.get(culture, ["generic"])
    traps = []
    for category in categories:
        patterns = STEREOTYPE_PATTERNS.get(category, [])
        traps.extend(patterns)

    if not traps:
        return "No specific traps identified - apply general authenticity standards."

    traps = list(dict.fromkeys(traps))

    formatted = "\n".join(f'  - "{trap}"' for trap in traps)
    return f"These specific phrases indicate stereotyping for this culture. Do not write them or anything close to them:\n{formatted}"
