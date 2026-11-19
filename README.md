# SPECIAL OPS — VICTUS Field Demonstration

**A landscape, mobile-first first-person cinematic shooter campaign built to demonstrate what the VICTUS engine can actually do.**

This repository is the game project, not another engine. VICTUS is the engine. The first physical performance target is the owner's **Infinix Hot 10S, 6 GB RAM variant**. Desktop and emulator workflows are also required, but PC is not the design target.

> **Current state:** the repository contains the VICTUS game project, scenes, scripts, generated assets, test scenes and development evidence. The complete campaign and tone are specified in the story bible and production documents; full mission integration, physical-device validation and final packaging remain production work. Do not infer a finished campaign or Android release from the existence of development scenes or passing automated tests.

## Start here — autonomous coding agent

Read these documents before implementation:

1. [AGENTS.md](AGENTS.md) — operating contract and completion rules.
2. [Project brief](docs/PROJECT_BRIEF.md) — product, story, camera, gameplay loop and stage plan.
3. [VICTUS engine audit](docs/VICTUS_ENGINE_AUDIT.md) — verified features and real gaps.
4. [Stage 01: Forest](docs/STAGE_01_FOREST.md) — detailed analysis of the four supplied video references.
5. [Hot 10S mobile target and controls](docs/MOBILE_TARGET_AND_CONTROLS.md) — device constraints, landscape UI, input and validation.
6. [Characters, animation and dialogue](docs/CHARACTERS_ANIMATION_AUDIO.md) — existing V-01/V-02, human character needs, facial motion and voice pipeline.
7. [Campaign and cinematics](docs/CAMPAIGN_AND_CINEMATICS.md) — playable operation route, first-person direction and cinematic cutscene requirements.
8. [Campaign story bible](docs/CAMPAIGN_STORY_BIBLE.md) — complete Operation Iron Veil narrative from briefing to credits.
9. [Squad banter and ambience](docs/SQUAD_BANTER_AND_AMBIENCE.md) — dark-comedy voice, sample lines, environmental scares and sound design.
10. [Operators and fictional weapon design](docs/OPERATORS_AND_WEAPON_DESIGN.md) — operator costumes, character research and the fictional shooter art/gameplay scope.
11. [Production plan](docs/PRODUCTION_PLAN.md) — dependency-ordered build, narrative integration and test work.
12. [Research register](docs/RESEARCH_REGISTER.md) — source URLs, dates, licensing and unresolved questions.
13. [Build and test log](docs/BUILD_AND_TEST_LOG.md) — the evidence record for builds, devices, tests and profiling.

## Non-negotiable direction

- **Landscape first.** Android orientation, camera composition and interface are landscape.
- **Mobile first, not mobile later.** The Hot 10S is the first physical target. No performance claim is valid until tested on that handset.
- Stage 01 follows the supplied misty-forest references. Preserve their atmosphere, not their portrait video framing.
- The experience is a first-person cinematic military campaign with squad-led dark comedy and limited scare-comedy: explore, fight authored non-lethal encounters, complete operations with a recurring full squad (player plus three or four allied operators), and move through the forest, perimeter, facility, bunker and a substantial basement. Teammates accompany the player, trade character-specific banter and react to unsettling wildlife and mechanical sounds. The story's stakes stay serious; this is not a horror game.
- Gameplay remains first-person; frequent, purposeful in-engine cutscenes deliver squad moments, major location reveals, the bunker/basement discoveries and the V-01 ending. Cutscene cameras may use external angles, then return control to first-person.
- Build original operator costumes and fictional game weapons with a real playable shooter loop. Weapon research is limited to fictional visual design, animation, sound and abstract game balance; do not add real-world weapon instructions or copied military insignia.
- Use VICTUS through its normal project, scene, asset, scripting, animation, physics, audio, UI and export workflows. Do not make a parallel renderer or copy the engine into this repository.
- The final reveal uses the existing **Vanguard V-01** as the VICTUS dummy: an ordinary dummy awkwardly positioned behind a chair. It is not an AI mastermind or boss. V-02 may appear as a secondary character.
- Build original fictional primary/secondary game weapons and a separate non-weapon field utility device for scanning, illumination and object interaction.
- Every third-party asset, voice, font, sound, tool and dataset needs a source and license record before it ships.

## Repository map

```
AGENTS.md
README.md
docs/
  PROJECT_BRIEF.md
  VICTUS_ENGINE_AUDIT.md
  STAGE_01_FOREST.md
  MOBILE_TARGET_AND_CONTROLS.md
  CHARACTERS_ANIMATION_AUDIO.md
  CAMPAIGN_AND_CINEMATICS.md
  CAMPAIGN_STORY_BIBLE.md
  SQUAD_BANTER_AND_AMBIENCE.md
  OPERATORS_AND_WEAPON_DESIGN.md
  PRODUCTION_PLAN.md
  RESEARCH_REGISTER.md
  BUILD_AND_TEST_LOG.md
```

The agent should create a normal VICTUS game project, its scenes, scripts, metadata, assets, tests and packaging configuration after checking the live engine repository. Generated build output must stay out of Git.

## What "finished" means

A complete playable campaign—not a mock-up, isolated environment render, single-stage demo or pile of assets. It must boot on the target phone, run in landscape, support multitouch and gamepad, deliver a complete first-person shooter campaign from the forest through the perimeter, facility, bunker and lower basement to the V-01 chair reveal, include its authored cutscenes and real dialogue audio with subtitles, save progress, and pass repeatable gameplay and packaging tests. It must package through VICTUS and have repeatable automated tests. Final reports must separate tested facts from targets and unknowns.
