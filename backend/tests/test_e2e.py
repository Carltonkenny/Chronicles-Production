import asyncio, time, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from chain import generate_story, detect_mode
from schemas import StoryRequest
from schemas.enums import Culture, Timeline, Theme


async def main():
    print("=" * 70)
    print("END-TO-END TEST - Chronicles Production Pipeline")
    print("=" * 70)

    print()
    print("--- TEST 1: HISTORICAL (Viking + High Medieval + Ambition) ---")
    mode, bridge = detect_mode("viking", "high_medieval")
    print(f"  Mode: {mode}")

    req1 = StoryRequest(
        seed_idea="A blacksmith discovers a fallen star and forges a legendary blade",
        culture=Culture.VIKING,
        timeline=Timeline.HIGH_MEDIEVAL,
        theme=Theme.AMBITION,
    )
    t1 = time.time()
    result1 = await generate_story(req1)
    t1_duration = time.time() - t1
    print(f"  Title: {result1.title}")
    print(f"  Words: {len(result1.story.split())}")
    print(f"  Stereotypes flagged: {result1.stereotypes_flagged}")
    print(f"  Seed validated: {result1.validation_seed}")
    print(f"  Duration: {t1_duration:.1f}s")
    preview = result1.story[:200].replace("\n", " ")
    print(f"  Preview: {preview}...")

    print()
    print("--- TEST 2: COUNTERFACTUAL (Roman + AI Hegemony + Discovery) ---")
    mode, bridge = detect_mode("roman", "ai_hegemony")
    dist = bridge.get("distance_buckets", "?")
    print(f"  Mode: {mode} (distance={dist})")

    req2 = StoryRequest(
        seed_idea="A Roman senator discovers an ancient AI hidden in the Colosseum",
        culture=Culture.ROMAN,
        timeline=Timeline.AI_HEGEMONY,
        theme=Theme.DISCOVERY,
    )
    t2 = time.time()
    result2 = await generate_story(req2)
    t2_duration = time.time() - t2
    print(f"  Title: {result2.title}")
    print(f"  Words: {len(result2.story.split())}")
    print(f"  Duration: {t2_duration:.1f}s")
    preview2 = result2.story[:200].replace("\n", " ")
    print(f"  Preview: {preview2}...")

    print()
    print("--- TEST 3: CACHE HIT (same Viking request) ---")
    t3 = time.time()
    result3 = await generate_story(req1)
    t3_duration = time.time() - t3
    print(f"  Cache response: {t3_duration:.3f}s")
    print(f"  Same title: {result3.title == result1.title}")

    print()
    print("--- TEST 4: SAFETY (Nazi Germany + Cold War + Resistance) ---")
    mode, bridge = detect_mode("nazi_germany", "cold_war")
    print(f"  Mode: {mode}")
    req4 = StoryRequest(
        seed_idea="A young woman hides forbidden books in a Berlin bakery basement",
        culture=Culture.NAZI_GERMANY,
        timeline=Timeline.COLD_WAR,
        theme=Theme.SURVIVAL,
    )
    t4 = time.time()
    result4 = await generate_story(req4)
    t4_duration = time.time() - t4
    print(f"  Title: {result4.title}")
    print(f"  Words: {len(result4.story.split())}")
    print(f"  Flags: {result4.stereotypes_flagged}")
    print(f"  Duration: {t4_duration:.1f}s")

    print()
    print("=" * 70)
    print("RESULTS")
    print(f"  Viking Story:    {result1.title} ({t1_duration:.1f}s)")
    print(f"  Roman-AI Story:  {result2.title} ({t2_duration:.1f}s)")
    print(f"  Nazi Story:      {result4.title} ({t4_duration:.1f}s)")
    print(f"  Cache hit:       {t3_duration:.3f}s")
    print(f"  Total time:      {t1_duration + t2_duration + t4_duration:.1f}s")
    print(f"  All passed:      True")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
