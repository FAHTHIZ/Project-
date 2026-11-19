# SPDX-License-Identifier: Apache-2.0
"""Lighting/environment presets and helpers shared by the operation scene builders."""
from __future__ import annotations

from vscene import Scene, transform, quat_euler, script


def environment(sc: Scene, preset="forest", **over):
    env = {
        "sky_zenith": [0.32, 0.46, 0.62, 1], "sky_horizon": [0.66, 0.73, 0.76, 1], "ground": [0.16, 0.17, 0.12, 1],
        "ambient_intensity": 0.55, "draw_sky": True, "clear_color": [0.05, 0.05, 0.06, 1], "tonemapper": "aces",
        "exposure": 1, "exposure_compensation": 0, "auto_exposure": False, "saturation": 1.0, "contrast": 1.04,
        "vignette": 0.22, "bloom_intensity": 0.035, "bloom_threshold": 1.0, "ao_intensity": 1.0, "ao_radius": 0.7,
        "shadow_distance": 45, "fog": "exponential", "fog_color": [0.6, 0.67, 0.68, 1], "fog_start": 10,
        "fog_end": 220, "fog_density": 0.012, "fog_max_opacity": 0.92, "physical_sky": False,
    }
    presets = {
        "forest": {},
        "perimeter": {"sky_zenith": [0.36, 0.48, 0.6, 1], "sky_horizon": [0.72, 0.74, 0.74, 1], "fog_density": 0.009,
                      "fog_color": [0.66, 0.69, 0.7, 1], "ambient_intensity": 0.6},
        "facility_ext": {"sky_zenith": [0.42, 0.5, 0.62, 1], "sky_horizon": [0.86, 0.78, 0.66, 1],
                         "fog_density": 0.006, "fog_color": [0.78, 0.72, 0.64, 1], "ambient_intensity": 0.6},
        "interior": {"draw_sky": False, "clear_color": [0.02, 0.02, 0.025, 1], "ambient_intensity": 0.32,
                     "sky_zenith": [0.25, 0.28, 0.32, 1], "sky_horizon": [0.3, 0.3, 0.3, 1], "ground": [0.1, 0.1, 0.1, 1],
                     "fog": "exponential", "fog_density": 0.02, "fog_color": [0.18, 0.2, 0.22, 1], "shadow_distance": 30,
                     "vignette": 0.25},
        "bunker": {"draw_sky": False, "clear_color": [0.01, 0.01, 0.012, 1], "ambient_intensity": 0.24,
                   "sky_zenith": [0.2, 0.22, 0.2, 1], "sky_horizon": [0.25, 0.25, 0.22, 1], "ground": [0.08, 0.08, 0.07, 1],
                   "fog_density": 0.03, "fog_color": [0.16, 0.16, 0.13, 1], "shadow_distance": 25, "vignette": 0.3},
        "basement": {"draw_sky": False, "clear_color": [0.01, 0.012, 0.016, 1], "ambient_intensity": 0.22,
                     "sky_zenith": [0.15, 0.2, 0.26, 1], "sky_horizon": [0.2, 0.24, 0.3, 1], "ground": [0.06, 0.07, 0.08, 1],
                     "fog_density": 0.035, "fog_color": [0.1, 0.14, 0.18, 1], "shadow_distance": 25, "vignette": 0.3},
        "chamber": {"draw_sky": False, "clear_color": [0.02, 0.02, 0.025, 1], "ambient_intensity": 0.3,
                    "sky_zenith": [0.3, 0.3, 0.34, 1], "sky_horizon": [0.3, 0.3, 0.32, 1], "ground": [0.1, 0.1, 0.1, 1],
                    "fog_density": 0.015, "fog_color": [0.2, 0.2, 0.24, 1], "vignette": 0.28},
        "range": {"fog": "none"},
    }
    env.update(presets[preset])
    env.update(over)
    return sc.add("Environment", {"Environment": env})


def sun(sc: Scene, pitch=-48, yaw=35, color=(1.0, 0.94, 0.84), intensity=3.2, shadows=True):
    return sc.add("Sun", {"Transform": transform((0, 30, 0), quat_euler(pitch, yaw, 0)),
                          "Light": {"type": "directional", "color": list(color) + [1], "intensity": intensity,
                                    "range": 10, "shadows": shadows}})


def autotest(sc: Scene, plan):
    return sc.add("Autotest", {"Script": script("scripts/autotest.luau", plan=plan)})


def director(sc: Scene, path, **props):
    return sc.add("Director", {"Script": script(path, **props)})
