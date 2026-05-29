from agents.base_agent import BaseAgent
from schemas import WorkOrder, WorkResult
from logger_config import setup_logger
from utils import get_visual_elements

logger = setup_logger("PropDesigner")


class PropDesignerAgent(BaseAgent):
    agent_type = "prop_designer"

    async def _execute_internal(self, work_order: WorkOrder) -> WorkResult:
        data = work_order.input_data
        culture = data.get("culture", "")
        timeline = data.get("timeline", "")
        vb = data.get("visual_bible", {})

        visual_elements = get_visual_elements(culture, timeline)
        artifacts = visual_elements.get("artifact", [])
        clothing_items = visual_elements.get("clothing", [])

        props = []

        for art in artifacts:
            if isinstance(art, dict):
                name = art.get("name", "").replace("_", " ").title()
                props.append({
                    "name": name,
                    "prop_type": _classify_prop_type(name, art.get("description", "")),
                    "materials": art.get("materials", []),
                    "dimensions": art.get("dimensions", ""),
                    "colors": art.get("colors", []),
                    "era_name": f"{culture} {timeline}",
                    "character_owner": None,
                    "scene_used_in": [],
                    "cultural_significance": art.get("description", ""),
                })

        char_bibles = (
            vb.get("director", {}).get("character_bibles")
            or vb.get("character_bibles", [])
        )
        for cb in char_bibles:
            if not isinstance(cb, dict):
                continue
            char_name = cb.get("name", "")
            sig_items = cb.get("signature_items", [])
            for item in sig_items:
                if isinstance(item, str):
                    props.append({
                        "name": item.title(),
                        "prop_type": _classify_prop_type(item, cb.get("appearance", "")),
                        "materials": [],
                        "dimensions": "",
                        "colors": [],
                        "era_name": f"{culture} {timeline}",
                        "character_owner": char_name,
                        "scene_used_in": [],
                        "cultural_significance": f"Signature item of {char_name}",
                    })

        for c in clothing_items:
            if isinstance(c, dict):
                name = c.get("name", "").replace("_", " ").title()
                props.append({
                    "name": name,
                    "prop_type": "accessory",
                    "materials": c.get("materials", []),
                    "dimensions": "",
                    "colors": c.get("colors", []),
                    "era_name": f"{culture} {timeline}",
                    "character_owner": None,
                    "scene_used_in": [],
                    "cultural_significance": c.get("description", ""),
                })

        self.tokens_used = 0
        logger.info(f"[{self.agent_type}] Extracted {len(props)} props for {culture}/{timeline}")
        return WorkResult(
            success=True,
            output_data={"props": props},
            wall_time_ms=self.wall_time_ms,
            tokens_used=self.tokens_used,
        )


def _classify_prop_type(name: str, description: str) -> str:
    combined = f"{name} {description}".lower()
    weapon_keywords = ["sword", "axe", "spear", "dagger", "bow", "mace", "shield", "gun", "rifle", "blade", "hammer", "lance"]
    jewelry_keywords = ["ring", "necklace", "bracelet", "earring", "torc", "brooch", "crown", "pendant", "anklet", "circlet", "bead"]
    vehicle_keywords = ["chariot", "ship", "cart", "wagon", "longship", "galley", "horse", "spaceship", "craft", "vessel", "transport"]
    tool_keywords = ["plow", "loom", "anvil", "forge", "chisel", "sickle", "hammer", "saw", "drill", "needle", "wrench", "quern", "mill", "grind", "awl", "file", "scraper"]
    furniture_keywords = ["throne", "chair", "table", "bench", "bed", "chest", "altar", "couch", "desk", "stool"]
    religious_keywords = ["idol", "totem", "amulet", "icon", "relic", "ritual", "temple", "shrine", "staff", "scepter", "censar"]

    for kw in weapon_keywords:
        if kw in combined:
            return "weapon"
    for kw in jewelry_keywords:
        if kw in combined:
            return "jewelry"
    for kw in vehicle_keywords:
        if kw in combined:
            return "vehicle"
    for kw in furniture_keywords:
        if kw in combined:
            return "furniture"
    for kw in religious_keywords:
        if kw in combined:
            return "religious"
    for kw in tool_keywords:
        if kw in combined:
            return "tool"
    return "accessory"
