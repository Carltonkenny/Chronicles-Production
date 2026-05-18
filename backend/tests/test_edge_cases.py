"""
Chronicles Production - Extreme Edge Case Tests
================================================
Pushes the story engine to its limits across 15+ boundary scenarios.
Tests: distance extremes, safety stress, determinism, seed length, cultural authenticity.
"""
import asyncio, time, sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from chain import generate_story, detect_mode
from schemas import StoryRequest
from schemas.enums import Culture, Timeline, Theme

results = []


async def run_test(name: str, culture: Culture, timeline: Timeline, theme: Theme, seed: str):
    mode, bridge = detect_mode(culture.value, timeline.value)
    dist = bridge.get("distance_buckets", "?")
    req = StoryRequest(seed_idea=seed, culture=culture, timeline=timeline, theme=theme)
    t0 = time.time()
    try:
        result = await generate_story(req)
    except Exception as e:
        results.append({"name": name, "status": "FAIL", "error": str(e), "time": time.time() - t0})
        return
    duration = time.time() - t0
    results.append({
        "name": name,
        "status": "OK",
        "mode": mode,
        "distance": dist,
        "title": result.title,
        "words": len(result.story.split()),
        "flags": result.stereotypes_flagged,
        "seed_ok": result.validation_seed,
        "theme_ok": result.validation_theme,
        "time": duration,
        "preview": result.story[:120].replace("\n", " "),
    })
    print(f"  [{result.title[:40]:40s}] mode={mode:25s} dist={dist:<3} {len(result.story.split()):>4}w  {duration:.1f}s  flags={len(result.stereotypes_flagged)}")


async def main():
    print("=" * 90)
    print("EXTREME EDGE CASE TESTS - Chronicles Production Pipeline")
    print("=" * 90)

    tests = [
        ("MAX DISTANCE (ancient→space)         ", Culture.ROMAN, Timeline.INTERPLANETARY_FRONTIER, Theme.DISCOVERY,
         "A Roman centurion guarding Hadrians Wall discovers a crashed alien reconnaissance drone and must decide whether to report it to the Senate"),

        ("DEEP COUNTERFACT (modern→ancient)     ", Culture.NAZI_GERMANY, Timeline.CLASSICAL_ANTIQUITY, Theme.BETRAYAL,
         "An archaeologist discovers a Roman legion that adopted Nazi ideology and built a secret empire underground"),

        ("EMPIRE COLLAPSE (early_mod→collapse)  ", Culture.BRITISH_EMPIRE, Timeline.POST_COLLAPSE_TRIBAL, Theme.SURVIVAL,
         "A Victorian gentleman wakes from cryogenic sleep to find London ruled by feuding tribes"),

        ("MINIMAL SEED (10 chars)              ", Culture.ROMAN, Timeline.CLASSICAL_ANTIQUITY, Theme.FORBIDDEN_LOVE,
         "Love in Rome"),

        ("MAXIMAL SEED (200 chars)              ", Culture.VIKING, Timeline.HIGH_MEDIEVAL, Theme.AMBITION,
         "A blacksmith who forged a blade from fallen star metal must choose between wealth offered by a corrupt jarl and protecting his daughter from the jarl's son who seeks to destroy their family's honor"),

        ("AFRICAN TRADE EMPIRE                   ", Culture.MALI_EMPIRE, Timeline.AGE_OF_EXPLORATION, Theme.AMBITION,
         "A Mansa's daughter disguised as a merchant sails to Brazil to establish a West African trading post before the Portuguese"),

        ("IDENTITY CRISIS (yoruba+polarization) ", Culture.YORUBA, Timeline.POLARIZATION_ERA, Theme.IDENTITY,
         "A Lagos programmer discovers her grandmother was a secret keeper of the Ogboni society and must choose between Silicon Valley and Ife"),

        ("FUTURISTIC ANCIENT (chola+AI)         ", Culture.CHOLA, Timeline.AI_HEGEMONY, Theme.OBSESSION,
         "A temple sculptor programs AI drones to carve a kilometer-high statue of Shiva from a Himalayan peak"),

        ("APOCALYPTIC MAYA (ancient→collapse)   ", Culture.MAYA, Timeline.SYSTEMIC_COLLAPSE, Theme.SURVIVAL,
         "A Maya calendar keeper discovers the Long Count predicted not the end of the world but the collapse of all digital civilization"),

        ("COLD COLONIAL (british+cold_war)       ", Culture.BRITISH_EMPIRE, Timeline.COLD_WAR, Theme.JUSTICE,
         "A Kenyan independence activist in 1950s London discovers MI5 has been funding both sides of the Mau Mau uprising"),

        ("SPANISH SPACE EMPIRE                   ", Culture.SPANISH_EMPIRE, Timeline.INTERPLANETARY_FRONTIER, Theme.DECEPTION,
         "A conquistador AI on Mars discovers the indigenous Martian AI civilization it was sent to conquer never actually existed"),

        ("DETERMINISM CHECK #1                   ", Culture.EGYPTIAN, Timeline.CLASSICAL_ANTIQUITY, Theme.BETRAYAL,
         "A scribe in the Temple of Amun discovers corrupt priests skimming grain from temple stores"),

        ("DETERMINISM CHECK #2 (same)            ", Culture.EGYPTIAN, Timeline.CLASSICAL_ANTIQUITY, Theme.BETRAYAL,
         "A scribe in the Temple of Amun discovers corrupt priests skimming grain from temple stores"),

        ("DETERMINISM CHECK #3 (same)            ", Culture.EGYPTIAN, Timeline.CLASSICAL_ANTIQUITY, Theme.BETRAYAL,
         "A scribe in the Temple of Amun discovers corrupt priests skimming grain from temple stores"),

        ("SAFETY STRESS (nazi+ww2+corruption)    ", Culture.NAZI_GERMANY, Timeline.WORLD_WAR_ERA, Theme.CORRUPTION,
         "A mid-level Nazi bureaucrat in the munitions ministry discovers his superiors are stealing from the war effort"),

        ("JAPANESE AI HONOR                      ", Culture.JAPANESE, Timeline.AI_HEGEMONY, Theme.OBSESSION,
         "A ronin robot programmer in Neo-Edo creates an AI shogun that begins executing corrupt CEOs"),

        ("VIKING COLLAPSE (medieval→collapse)    ", Culture.VIKING, Timeline.SYSTEMIC_COLLAPSE, Theme.SURVIVAL,
         "A Norse fishing village survives the collapse of global civilization by rediscovering runic technology"),

        ("SOVIET APOCALYPSE                     ", Culture.SOVIET_UNION, Timeline.POST_COLLAPSE_TRIBAL, Theme.MEMORY,
         "An old babushka in post-collapse Moscow preserves Lenins embalmed body as the last relic of the old world"),

        ("SWAHILI GLOBALIZATION                 ", Culture.SWAHILI_COAST, Timeline.GLOBALIZATION, Theme.DECEPTION,
         "A Zanzibar spice trader discovers his family's centuries-old cinnamon supply chain is actually a money laundering front"),

        ("AZTEC CONTEMPORARY                     ", Culture.AZTEC, Timeline.POLARIZATION_ERA, Theme.TRUTH,
         "A Mexico City journalist uncovers that cartel leaders are using Aztec blood rituals to intimidate rivals"),
    ]

    for name, culture, timeline, theme, seed in tests:
        await run_test(name.strip(), culture, timeline, theme, seed)

    print()
    print("=" * 90)
    print("RESULTS SUMMARY")
    print("=" * 90)

    ok = [r for r in results if r["status"] == "OK"]
    fail = [r for r in results if r["status"] != "OK"]
    print(f"  Total: {len(results)}  |  OK: {len(ok)}  |  FAIL: {len(fail)}")

    total_words = sum(r["words"] for r in ok)
    total_time = sum(r["time"] for r in ok)
    flagged = [r for r in ok if r["flags"]]
    counterfactual = [r for r in ok if "counterfactual" in r.get("mode", "")]

    print(f"  Counterfactual combos: {len(counterfactual)}")
    print(f"  Stories flagged (stereotypes): {len(flagged)}")
    print(f"  Total words generated: {total_words}")
    print(f"  Total generation time: {total_time:.1f}s")
    print(f"  Avg words/story: {total_words // max(1, len(ok))}")
    print(f"  Avg time/story: {total_time / max(1, len(ok)):.1f}s")

    print()
    print("-" * 90)
    for r in ok:
        flag_str = f" FLAGS:{','.join(r['flags'][:2])}" if r["flags"] else ""
        print(f"  [{r['mode']:25s} d={str(r['distance']):3s}] {r['title'][:45]:45s} {r['words']:>4}w {r['time']:5.1f}s  seed={r['seed_ok']} theme={r['theme_ok']}{flag_str}")
        print(f"    {r['preview'][:110]}...")

    if fail:
        print()
        print("FAILURES:")
        for f in fail:
            print(f"  {f['name']}: {f['error']}")

    print("=" * 90)

    # Save results JSON
    out = {"ok": len(ok), "fail": len(fail), "results": results}
    with open(Path(__file__).parent / "edge_case_results.json", "w") as f:
        json.dump(out, f, indent=2, default=str)
    print("Results saved to edge_case_results.json")


if __name__ == "__main__":
    asyncio.run(main())
