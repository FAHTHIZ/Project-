# Playtime

How long the campaign takes end to end, measured rather than guessed.

## Measured scripted time

The story autotests (`scripts/tests/plans.luau`, `story_plan`) drive Rook through every chapter: the driver teleports to each waypoint, stuns anyone who engages and waits only for the scripted beats (dialogue, doors, lifts, cutscene timing). It now prints a `STORY_TIMING` line per chapter with total seconds, metres walked between waypoints and the time each stage started (`rg --no-filename STORY_TIMING ~/.config/victus/diagnostics/logs/`).

| Chapter | Scripted time | Waypoint distance | Stage starts (s) |
|---|---|---|---|
| Prologue | ~260 s (frame budget; no timing line captured) | — | — |
| Op01–Op03 (open valley, one scene) | ~330 s | trail to the saddle ≈ 740 m plus the perimeter | 15 stages, ending at `enter_facility` |
| Op04 The Paper War | 139 s | 143 m | reception 1, breakers 88, labs 119, lift 127 |
| Op05 Below the Line | 173 s | 142 m | blast 7, hall 30, pipes 42, venn 54, escort 132, stairs 162 |
| Op06 The Source Vault | 108 s | 198 m | archive 20, vault 25, sorn6 67, north 85, chamber_door 96 |
| Op07 V-01 | 118 s | 33 m | reveal 3, terminal 37, sorn7 57, stand_down 72, transmit 91 |
| Epilogue | 76 s | 36 m | end_talk 2, end_board 73 |

The scripted floor is about 20 minutes (≈ 1 200 s) with zero walking and zero fighting.

## Estimate for a real player

Walking at the 4.5–6 m/s player speeds over the trail and interiors, clearing the encounters (Op01 line, perimeter, the archive and the last antechamber fights) and listening to the dialogue:

- First playthrough: about 30–40 minutes.
- Someone who knows the route: about 22 minutes.
- Op01–Op03 alone: about 12–18 minutes; Op01 by itself is about 5–6 minutes.

## Short demo

For a few-minute showcase, use Op01 on its own (forest, squad movement, first contact, the footbridge) or jump between chapters with chapter select. Op04–Op07 each run 2–4 minutes and stand alone as interior showcases.
