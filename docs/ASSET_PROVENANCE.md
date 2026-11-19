# Asset Provenance and Licences

Every shipped asset is listed here with its origin. "Original (generated)" means the asset is produced by a script in this repository from code alone, with no third-party art input; regenerate it with the listed command. Licence for original assets: Apache-2.0 (same as the game code), owner FAHTHIZ.

| Asset(s) | Origin | Generator / source | Licence |
|---|---|---|---|
| `game/assets/models/characters/sops_explorer.glb`, `sops_ranger.glb` | Original (generated) meshes. Skeleton, inverse bind matrices and the clips Idle/Walk/Run/Jump/Fall/Land/Interact are read from VICTUS's `victus_vanguard_02.glb` (VICTUS, Apache-2.0); Stumble/GetUp/Scan/Talk/Wave/Inspect are authored in the generator | `tools/characters/build_humans.py` | Apache-2.0 |
| `game/assets/models/env/*.glb` (trees, ferns, shrubs, grass, rocks, log, stump, trail marker, sign, sensor post, pack, fence, field device) | Original (generated) | `tools/props/build_forest.py` | Apache-2.0 |
| `game/assets/textures/env/*.png` (ground layers) and the textures embedded in the env GLBs | Original (generated, procedural noise and drawing) | `tools/props/build_forest.py` | Apache-2.0 |
| `game/assets/models/weapons/*.glb` (PC-7 Lantern carbine body/cell, SP-2 Wren sidearm body/slide/cell, gloved first-person hands, pulse bolt, stun target) | Original (generated); fictional designs, not modelled on any real firearm | `tools/props/build_weapons.py` | Apache-2.0 |
| `game/assets/audio/weapons/*.wav`, `audio/ui/*.wav`, `audio/foley/*.wav` (pulse shots, cell swaps, charge whine, impacts, target fold, scanner ping, footsteps, cloth, landing, UI ticks) | Original (synthesised from code: oscillators, filtered noise, envelopes; no recordings or samples) | `tools/audio/build_sfx.py` | Apache-2.0 |
| `game/assets/models/characters/victus_vanguard_01.glb`, `_02.glb`, `anim/characters/vanguard_locomotion.vanim`, template scripts, `audio/impact.wav`, `textures/ground_grid.png`, materials, shader | VICTUS 3D template (`victus new --template 3d`) | VICTUS `bc0ce15` | Apache-2.0 (VICTUS) |

Authoring tools: Python 3, NumPy, Pillow (no assets from them; libraries only).
