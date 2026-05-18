import asyncio, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.director import DirectorAgent
from agents.production_designer import ProductionDesignerAgent
from agents.art_director import ArtDirectorAgent
from schemas import WorkOrder
from utils.visual_engine import visual_engine


async def main():
    print("=" * 70)
    print("PHASE 2 LIVE INTEGRATION TEST")
    print("=" * 70)

    print("\n--- Part 1: VisualElementsEngine (viking/high_medieval) ---")
    t0 = time.time()
    ve = await visual_engine.get("viking", "high_medieval")
    cats = {k: len(v) for k, v in ve.items() if isinstance(v, list)}
    print(f"  Generated in {time.time()-t0:.1f}s")
    print(f"  Categories: {cats}")
    total = sum(cats.values())
    print(f"  Total elements: {total}")

    print("\n--- Part 2: Director Agent ---")
    wo = WorkOrder(agent_type="director", input_data={
        "title": "The Star-Forged Axe", "culture": "viking", "timeline": "high_medieval",
        "theme": "ambition",
        "story": "Bjorn worked the forge. Sparks flew. The star-metal glowed blue with an otherworldly light. He raised his hammer.",
        "characters": ["Bjorn: A blacksmith haunted by his fathers dishonor"],
        "scenes": [{"location": "forge", "summary": "Bjorn discovers star-metal", "emotional_beat": "wonder_discovery"}],
        "visual_elements": ve,
    })
    agent = DirectorAgent()
    t1 = time.time()
    result = await agent.execute(wo)
    print(f"  Success: {result.success}")
    if result.success:
        d = result.output_data
        tone = d.get("film_tone", "?")
        print(f"  film_tone: {tone[:80]}")
        print(f"  Characters: {len(d.get('character_bibles', []))}")
        print(f"  Locations: {len(d.get('location_descriptions', []))}")
        shots = sum(len(v) for v in d.get("shot_variation_matrix", {}).values())
        print(f"  Shots: {shots}")
    print(f"  Time: {time.time()-t1:.1f}s")

    print("\n--- Part 3: Production Designer ---")
    wo2 = WorkOrder(agent_type="production_designer", input_data={
        "culture": "viking", "timeline": "high_medieval", "theme": "ambition",
        "setting": "A smoke-filled forge at night, timber beams blackened by fire",
        "characters": ["Bjorn: A blacksmith"], "locations": ["forge"],
    })
    agent2 = ProductionDesignerAgent()
    t2 = time.time()
    result2 = await agent2.execute(wo2)
    print(f"  Success: {result2.success}")
    if result2.success:
        d2 = result2.output_data
        print(f"  Locations: {len(d2.get('locations', []))}")
        print(f"  Materials: {len(d2.get('material_inventory', []))}")
    print(f"  Time: {time.time()-t2:.1f}s")

    print("\n--- Part 4: Cache Test ---")
    t3 = time.time()
    ve2 = await visual_engine.get("viking", "high_medieval")
    cache_time = time.time() - t3
    cats2 = sum(len(v) for v in ve2.values() if isinstance(v, list))
    print(f"  Cache hit: {cache_time:.3f}s ({cats2} elements)")

    print()
    print("=" * 70)
    print("RESULTS")
    print(f"  VisualElementsEngine: {total} elements")
    print(f"  Director: {'PASS' if result.success else 'FAIL'}")
    print(f"  Production Designer: {'PASS' if result2.success else 'FAIL'}")
    print(f"  Cache: {'PASS' if cache_time < 1.0 else 'SLOW'}")
    all_pass = result.success and result2.success and total >= 5 and cache_time < 1.0
    print(f"  ALL PASSED: {all_pass}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
