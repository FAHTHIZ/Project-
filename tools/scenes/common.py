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
        # Kestrel Valley, 02:40-05:30: overcast storm night. Moonlight leaks through the cloud
        # deck as a weak blue key; the sky glows faintly at the horizon (town light under the
        # cloud). Rain, wet ground with puddles, low ground fog lit by lamps and searchlights.
        "night_storm": {
            "sky_zenith": [0.010, 0.013, 0.020, 1], "sky_horizon": [0.040, 0.046, 0.056, 1],
            "ground": [0.012, 0.013, 0.012, 1], "ambient_intensity": 0.55,
            "clear_color": [0.01, 0.012, 0.016, 1], "exposure": 1.0, "exposure_compensation": 1.6,
            "auto_exposure": False, "saturation": 0.86, "contrast": 1.08, "vignette": 0.3,
            "bloom_intensity": 0.06, "bloom_threshold": 0.9, "shadow_distance": 40,
            "fog": "exponential", "fog_color": [0.030, 0.035, 0.042, 1], "fog_start": 4, "fog_end": 260,
            "fog_density": 0.018, "fog_max_opacity": 0.96,
            "precipitation": "rain", "precipitation_intensity": 0.85, "precipitation_wind": [2.2, 0.0, 1.1],
            "precipitation_radius": 15.0, "precipitation_brightness": 1.6, "precipitation_opacity": 0.0,
            "wetness": 0.8, "puddles": 0.42, "puddle_size": 2.6, "precipitation_ripples": 1.0,
            "precipitation_splashes": 0.8,
            "volumetric_fog": True, "volumetric_density": 0.022, "volumetric_height": 4.0,
            "volumetric_falloff": 0.08, "volumetric_albedo": [0.72, 0.76, 0.82, 1], "volumetric_anisotropy": 0.62,
            "volumetric_distance": 140.0, "volumetric_sun": 0.6, "volumetric_ambient": 0.5,
            "volumetric_local_lights": 1.4, "volumetric_temporal": 0.9,
        },
        # 05:52 epilogue: the storm has passed east, low cloud breaking, cold blue-grey dawn
        "dawn": {
            "sky_zenith": [0.20, 0.25, 0.34, 1], "sky_horizon": [0.62, 0.52, 0.46, 1], "ground": [0.07, 0.08, 0.07, 1],
            "ambient_intensity": 0.6, "exposure_compensation": 0.4, "saturation": 0.9, "contrast": 1.06,
            "fog_color": [0.46, 0.48, 0.52, 1], "fog_start": 8, "fog_end": 400, "fog_density": 0.008,
            "fog_max_opacity": 0.9, "precipitation": "rain", "precipitation_intensity": 0.08,
            "wetness": 0.7, "puddles": 0.42, "puddle_size": 2.6, "precipitation_ripples": 0.2,
            "volumetric_fog": True, "volumetric_density": 0.012, "volumetric_height": 6.0, "volumetric_falloff": 0.06,
            "volumetric_albedo": [0.9, 0.88, 0.86, 1], "volumetric_anisotropy": 0.7, "volumetric_distance": 160.0,
        },
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
