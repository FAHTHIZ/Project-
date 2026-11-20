# Kestrel Valley — scale, pacing and how it compares

Written 2026-11-20 to answer: "how big is the forest meant to be, and is it big enough?"

## What the story says

The story bible (docs/CAMPAIGN_STORY_BIBLE.md, docs/STAGE_01_FOREST.md) never gives a size for the
forest. It is "the natural approach from the available staging area": Hollis guides the team along an
old forestry/service route to a concealed service approach. Nothing in the canon needs a big forest;
it needs a believable approach walk with cover, a cabin, a relay knoll, a ravine and a ridge.

## What is built (tools/world/worldmap.py, docs/world/KESTREL_VALLEY.md)

| Item | Value |
|---|---|
| Terrain | 1024 × 1024 m, one continuous landscape for Ops 01-03 |
| Play width | x ±300 m (PLAY_X) |
| Op01 forest band | z 300 → 0 (≈ 300 m deep, 600 m wide ≈ 18 ha), then ravine −30 → −106, hillside to the saddle at −194 |
| Trail, trailhead → footbridge | ≈ 116 m |
| Trail, trailhead → ravine | ≈ 417 m |
| Trail, trailhead → ridge saddle (end of Op01) | ≈ 740 m |
| Trail, total to the perimeter | ≈ 875 m |
| Trees | ~540 per hectare on a 3.4 m grid, ~27 000 in total |

Walking the 740 m Op01 trail without stopping takes roughly 3-4 minutes. Op01 itself runs ~5.5 minutes
in the scripted autotest (story_op01, 19 800 frames), with talk, the cabin, the relay and two fights.

## How Call of Duty handles it

- Infinity Ward builds campaign spaces at real 1:1 scale. For Modern Warfare (2019) they built the
  townhouse to scale instead of enlarging it for the AI, so it is cramped and blind corners are
  dangerous ([Activision blog](https://blog.activision.com/tw/zh/call-of-duty/2019-09/The-Narrative-of-Modern-Warfare-Part-1),
  [Polygon](https://www.polygon.com/e3/2019/6/11/18661980/call-of-duty-modern-e3-2019-warfare-slow-motion-quick-time-events/)).
- What makes a fight fun is cover density, not area. For MWII's "Dark Water" the fun version was a
  "cover jungle" of containers, and they made the ship four times bigger for it
  ([Activision Blizzard newsroom](https://newsroom.activisionblizzard.com/p/deep-talent-how-infinity-ward-brough),
  [GamingTrend](https://gamingtrend.com/news/take-a-behind-the-scenes-look-at-the-making-of-modern-warfare-iis-dark-water-campaign-mission/)).
- In the newer open sections, each point of interest has "a specific combat that's constructed for the
  player, not just random AI everywhere" ([GamesBeat, Modern Warfare 4](https://gamesbeat.com/how-call-of-duty-modern-warfare-4-weaves-narrative-and-open-world-elements-in-the-single-player-campaign-narrative-interview/)).
  MWIII's Open Combat Missions use enlarged boundaries but few checkpoints
  ([Call of Duty blog](https://www.callofduty.com/blog/2023/08/call-of-duty-modern-warfare-III-campaign-deep-dive-open-combat-missions-intel/)).
- In "All Ghillied Up" (CoD4) the stealth works because enemies react based on distance and angle,
  and the view cone shrinks in grass and baked shadows, rather than using simple trigger boxes
  ([Wikiwand](https://www.wikiwand.com/en/articles/All_Ghillied_Up),
  [IGN](https://www.ign.com/articles/how-all-ghillied-up-changed-call-of-duty-forever-art-of-the-level)).

## Verdict

The forest is not big, and it should not be. 1 km² with a ~740 m route is the right order for one
CoD-style mission. The problem is not area but density: between the cabin and the ravine, Op01 has
only one patrol fight. The plan is to keep the terrain and add authored pockets along the trail:

1. A Greyline search line sweeping the woods with torches between the cabin and the relay. The player
   can stay low and let it pass (see the awareness model below), or fight
   it in the trees.
2. The ravine ambush as a proper "cover jungle": fallen logs, rocks and a washed-out culvert, with the
   contractors bounding (see below).
3. Short calm stretches between pockets, where the squad's chatter and the storm do the work.

Status (2026-11-20):

1. Done. The search line is built at the footbridge, ~120 m from the trailhead, not between the cabin and the relay: the patrol fight already covers that stretch. Autotests op01_line and op01_line_loud.
2. The ravine already had 14-19 large rocks within 20 m of each trail point, more than any forest stretch, so the cover pass started in the woods. `tools/world/world_scene.py` `COVER_POCKETS` places 30 pieces of seeded cover:
   - footbridge/line: 7 pieces (5 boulders, 2 deadfall);
   - cabin -> relay: 23 pieces (6 boulders, 17 deadfall).

   The pieces are photoscanned rock_b boulders at x1.2-1.45 (1.5-1.8 m) and deadfall (two log_a crossed, ~1.1 m). They sit every 9-12 m on alternating sides, 3-7 m and 11-16 m off the path, and are kept 4.5 m clear of every patrol leg, 2.6 m from the trail and clear of the creek. Before this pass, those stretches had 2-5 logs and at most one large rock within 20 m.

## Real-world infantry behaviour the AI follows

- Rushes of 3-5 s from cover to cover ("I'm up, he sees me, I'm down")
  ([FM 3-21.8 / InfantryDrills](https://infantrydrills.com/manuals/fm-atp-3-21-8-infantry-rifle-platoon-squad-2024/movement-and-maneuver/tactical-movement-approach-march/movement-techniques/),
  [USMC patrolling](https://www.trngcmd.marines.mil/Portals/207/Docs/FMTBE/Student%20Materials/FMST/204.pdf)).
- Bounding overwatch: one element is always stopped to cover the one that moves; the two swap
  ([FM 3-21.9](https://www.globalsecurity.org/military/library/policy/army/fm/3-21-9/chap3.htm),
  [Wikipedia: fire and movement](https://en.wikipedia.org/wiki/Fire_and_movement)).
- Calls of "Moving" and "Set" between the two elements
  ([TFR field guide](https://www.scribd.com/document/1006731864/TFR-Basic-Infantry-Skills-Field-Guide)).

Implemented for Greyline in enemy.luau (BUILD_AND_TEST_LOG "Bounding overwatch").

## Awareness model (enemy.luau `E:notice_rate`)

A contractor who can see a target does not react at once. Awareness builds per second at
`1.8 × (1 − d/24)² + 0.04` (d in metres; under 4 m, or when hit, recognition is instant), multiplied by:

| Condition | × |
|---|---|
| target crouched (player, or an operator kneeling) | 0.45 |
| target still / sprinting | 0.55 / 1.8 |
| player's weapon light on | 2.4 |
| inside this contractor's rail-light beam (≤ 18 m, ~18° cone) | 2.6 |
| lightning flash in progress | 4 |
| contractor already searching | 1.6 |
| a group mate already fighting | 3 |

At 0.4 the contractor stops, stares at the spot and says a `grey_huh_*` line, then walks over to look. At 1.0 he
engages. Awareness decays at 0.22/s out of sight. Examples: at 18 m, crouched, still and with the light off it
takes ~11 s of unbroken view to raise a "huh"; standing with the light on, ~0.3 s to "huh" and ~2.5 s to a fight.
