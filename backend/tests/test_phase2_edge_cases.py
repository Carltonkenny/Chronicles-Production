"""
Phase 2 Edge Case Tests — Visual Bible Pipeline
Tests extreme combos, safety cultures, minimal inputs, counterfactual distances.
"""
import asyncio, sys, time, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.director import DirectorAgent
from agents.production_designer import ProductionDesignerAgent
from agents.art_director import ArtDirectorAgent
from schemas import WorkOrder
from utils.visual_engine import visual_engine

results = []


async def run_test(name, culture, timeline, theme, story, chars, scenes):
    print(f"\n--- {name} ---")
    t0 = time.time()
    try:
        ve = await visual_engine.get(culture, timeline)
        ve_time = time.time() - t0
        ve_cats = {k: len(v) for k, v in ve.items() if isinstance(v, list)}
        ve_total = sum(ve_cats.values())

        wo = WorkOrder(agent_type="director", input_data={
            "title": name[:50], "culture": culture, "timeline": timeline,
            "theme": theme, "story": story, "characters": chars, "scenes": scenes,
            "visual_elements": ve,
        })
        agent = DirectorAgent()
        dr = await agent.execute(wo)
        dr_ok = dr.success and bool(dr.output_data.get("character_bibles"))

        wo2 = WorkOrder(agent_type="production_designer", input_data={
            "culture": culture, "timeline": timeline, "theme": theme,
            "setting": story[:200], "characters": chars,
            "locations": list(set(s.get("location", "unknown") for s in scenes)),
        })
        agent2 = ProductionDesignerAgent()
        pd = await agent2.execute(wo2)
        pd_ok = pd.success and bool(pd.output_data.get("locations"))

        results.append({
            "name": name, "culture": culture, "timeline": timeline, "theme": theme,
            "ve_elements": ve_total, "ve_time": ve_time,
            "director": "PASS" if dr_ok else "FAIL",
            "pd": "PASS" if pd_ok else "FAIL",
            "chars": len(dr.output_data.get("character_bibles", [])),
            "locations": len(dr.output_data.get("location_descriptions", [])),
            "shots": sum(len(v) for v in dr.output_data.get("shot_variation_matrix", {}).values()),
            "materials": len(pd.output_data.get("material_inventory", [])),
            "sig_items": len(dr.output_data.get("character_bibles", [{}])[0].get("signature_items", [])),
        })
        print(f"  VE: {ve_total} elements ({ve_time:.1f}s) | Director: {'PASS' if dr_ok else 'FAIL'} ({len(dr.output_data.get('character_bibles',[]))} chars, {sum(len(v) for v in dr.output_data.get('shot_variation_matrix',{}).values())} shots) | PD: {'PASS' if pd_ok else 'FAIL'} ({len(pd.output_data.get('locations',[]))} locs, {len(pd.output_data.get('material_inventory',[]))} mats)")
    except Exception as e:
        results.append({"name": name, "director": f"ERROR: {e}", "pd": "SKIP"})
        print(f"  FAILED: {e}")


async def main():
    print("=" * 90)
    print("PHASE 2 EDGE CASE TESTS — Visual Bible Pipeline")
    print("=" * 90)

    tests = [
        ("HISTORICAL: Viking + High Medieval + Ambition",
         "viking", "high_medieval", "ambition",
         "Bjorn worked the forge. Sparks flew as his hammer struck the star-metal, each blow sending blue light dancing across the soot-blackened walls.",
         ["Bjorn: A blacksmith haunted by his father's dishonorable death, seeking to forge a weapon worthy of the gods",
          "Sigrid: His wife, a healer who watches her husband slip into obsession"],
         [{"location": "forge", "summary": "Bjorn begins forging the star-metal", "emotional_beat": "wonder_discovery"},
          {"location": "frozen_river", "summary": "Bjorn finds the star-metal in ice", "emotional_beat": "wonder_discovery"}]),

        ("COUNTERFACT: Roman + AI Hegemony + Discovery (dist=5)",
         "roman", "ai_hegemony", "discovery",
         "Senator Lucius discovered an ancient AI buried beneath the Colosseum, its circuits still pulsing with the consciousness of a long-dead emperor.",
         ["Lucius: A Roman senator who values truth over ambition, secretly studying forbidden technology"],
         [{"location": "colosseum_substructure", "summary": "Lucius discovers AI in the hypogeum", "emotional_beat": "wonder_discovery"},
          {"location": "senate_chamber", "summary": "Lucius debates whether to reveal the AI", "emotional_beat": "tension_fear"}]),

        ("SAFETY: Nazi Germany + World War Era + Corruption",
         "nazi_germany", "world_war_era", "corruption",
         "A mid-level bureaucrat in the munitions ministry discovered his superiors were embezzling funds meant for civilian relief. He faced a choice: report them and risk execution, or stay silent and become complicit.",
         ["Konrad: A clerk who joined the party to feed his family, now haunted by what he sees",
          "Elena: A resistance courier who passes forged documents through the ministry"],
         [{"location": "berlin_office", "summary": "Konrad discovers the ledgers", "emotional_beat": "tension_fear"},
          {"location": "bombed_station", "summary": "Konrad meets Elena to deliver evidence", "emotional_beat": "hope_determination"}]),

        ("EXTREME: Maya + Interplanetary Frontier + Survival (dist=7)",
         "maya", "interplanetary_frontier", "survival",
         "A Maya astronomer on a Mars colony discovered the ancient Long Count calendar predicted not the end of Earth but the collapse of all digital civilization across the solar system.",
         ["Ixchel: An astronomer who preserved her ancestors' star charts through generations of colonial suppression"],
         [{"location": "mars_observatory", "summary": "Ixchel decodes the ancient prediction", "emotional_beat": "wonder_discovery"},
          {"location": "mars_colony_dome", "summary": "Digital systems begin failing, the colony panics", "emotional_beat": "tension_fear"}]),

        ("AFRICAN: Mali Empire + Age of Exploration + Ambition",
         "mali_empire", "age_of_exploration", "ambition",
         "Mansa's daughter disguised herself as a merchant and sailed to Brazil to establish a West African trading post before the Portuguese could claim the coast.",
         ["Amina: A princess who learned navigation from Swahili sailors, determined to expand her father's empire across the sea"],
         [{"location": "timbuktu_harbor", "summary": "Amina prepares her expedition in secret", "emotional_beat": "hope_determination"},
          {"location": "brazil_coast", "summary": "Amina lands on unfamiliar shores", "emotional_beat": "wonder_discovery"}]),

        ("ASIAN: Japanese + AI Hegemony + Obsession (dist=4)",
         "japanese", "ai_hegemony", "obsession",
         "A ronin programmer in Neo-Edo created an AI shogun that began executing corrupt CEOs according to bushido code. He watched his creation spiral beyond control.",
         ["Kenji: A former corporate programmer who lost his family to algorithmic layoffs, now living in the digital underworld"],
         [{"location": "neo_edo_underground", "summary": "Kenji deploys the AI shogun into the corporate network", "emotional_beat": "hope_determination"},
          {"location": "shinjuku_skyline", "summary": "The AI shogun broadcasts its first execution live", "emotional_beat": "tension_fear"}]),

        ("COLONIAL: British Empire + Cold War + Justice (safety constrained)",
         "british_empire", "cold_war", "justice",
         "A Kenyan independence activist in 1950s London discovered MI5 had been secretly funding both sides of the Mau Mau uprising to justify continued colonial control.",
         ["Kamau: A law student who uncovers state secrets while working as a parliamentary clerk",
          "Mary: A British journalist who risks her career to publish the truth"],
         [{"location": "london_office", "summary": "Kamau finds classified MI5 documents", "emotional_beat": "tension_fear"},
          {"location": "fleet_street", "summary": "Mary and Kamau plan the publication", "emotional_beat": "hope_determination"}]),

        ("MINIMAL: Single character, single scene, short story",
         "egyptian", "classical_antiquity", "betrayal",
         "Khaemweset the scribe discovered the temple granaries were half-empty. The priests had been selling grain to Syrian merchants for years.",
         ["Khaemweset: A temple scribe who values truth over his own safety"],
         [{"location": "temple_granary", "summary": "Khaemweset discovers the theft", "emotional_beat": "tension_fear"}]),
    ]

    for name, culture, timeline, theme, story, chars, scenes in tests:
        await run_test(name, culture, timeline, theme, story, chars, scenes)

    print()
    print("=" * 90)
    print("RESULTS SUMMARY")
    print("=" * 90)
    passed = [r for r in results if r.get("director") == "PASS" and r.get("pd") == "PASS"]
    failed = [r for r in results if r not in passed]

    for r in passed:
        print(f"  PASS {r['name'][:60]:60s} VE={r['ve_elements']:>2}el  D={r['director']} PD={r['pd']}  chars={r['chars']} locs={r['locations']} shots={r['shots']} mats={r['materials']} sig={r['sig_items']}")
    for r in failed:
        print(f"  FAIL {r['name'][:60]:60s} D={r.get('director','?')} PD={r.get('pd','?')}")

    print(f"\n  Total: {len(results)} | Passed: {len(passed)} | Failed: {len(failed)}")
    if passed:
        avg_ve = sum(r["ve_elements"] for r in passed) / len(passed)
        avg_shots = sum(r["shots"] for r in passed) / len(passed)
        avg_mats = sum(r["materials"] for r in passed) / len(passed)
        print(f"  Avg VE elements: {avg_ve:.1f} | Avg shots: {avg_shots:.1f} | Avg materials: {avg_mats:.1f}")

    any_sig = all(r.get("sig_items", 0) > 0 for r in passed)
    any_chars = all(r.get("chars", 0) > 0 for r in passed)
    print(f"  All have signature items: {any_sig}")
    print(f"  All have character bibles: {any_chars}")
    print("=" * 90)

    with open(Path(__file__).parent / "phase2_edge_results.json", "w") as f:
        json.dump({"passed": len(passed), "failed": len(failed), "results": results}, f, indent=2, default=str)


if __name__ == "__main__":
    asyncio.run(main())
