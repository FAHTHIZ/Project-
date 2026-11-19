# SPDX-License-Identifier: Apache-2.0
"""Kestrel Valley master map: the authored layout that every world tool reads.

World frame: metres, +X east, -Z north, +Y up. The terrain spans x, z in [-512, 512].
The campaign runs south to north through one continuous landscape:

  south edge    ranger road enters through a gap in the southern hills
  Op01 forest   trailhead turnout (vehicle arrival, trunk) -> footpath through dense mixed forest
                -> creek footbridge -> Ranger Hollis's cabin clearing -> relay mast on a knoll
                -> rock ravine (ambush) -> forest thins on the lower hillside
  hillside      switchbacks across open upland meadow and outcrops to the ridge saddle overlook
  Op02          north slope down to the perimeter: cleared strip, fence, towers, gate
  Op03          compound plateau and the facility entrance cut into the northern mountain
  service road  the ranger road continues east of the ridge over a low saddle to the gate
                (the squad vehicle's route between operations)

Everything here is data; worldgen.py turns it into the heightfield, splat, vegetation and
scenes. Points are (x, z); heights are produced by the generator unless given.
"""
from __future__ import annotations

SIZE = 1024.0          # terrain x/z extent (m)
HEIGHT = 300.0         # metres for a normalized height of 1.0 (peaks reach ~280 m)
RES = 513              # samples per side (2 m spacing)

# Height profile along z (south +, north -): the valley floor rises to the ridge, dips to the
# perimeter plateau, then climbs into the northern mountain.
PROFILE_Z = [512, 470, 420, 300, 180, 60, -20, -110, -185, -230, -290, -330, -425, -455, -512]
PROFILE_H = [78, 58, 34, 25, 21, 26, 36, 62, 100, 88, 74, 70, 71, 112, 178]

# Ranger road: south gap -> trailhead turnout (Op01 arrival).
ROAD_IN = [(-30, 540), (-44, 490), (-70, 445), (-58, 400), (-74, 350), (-66, 318), (-58, 300)]
# Service road: trailhead -> east saddle -> perimeter gate -> compound -> facility apron.
ROAD_SERVICE = [(-58, 300), (-20, 292), (40, 278), (110, 252), (170, 206), (214, 140), (238, 60),
                (252, -30), (248, -110), (232, -175), (205, -235), (160, -282), (100, -318),
                (52, -340), (36, -362), (22, -395), (8, -428), (0, -446)]
ROAD_WIDTH = 5.0

# Footpath (Op01 -> hillside -> Op02 approach).
TRAIL = [(-54, 296), (-44, 274), (-26, 252), (-12, 232), (2, 214), (12, 201), (24, 186), (40, 166),
         (52, 146), (60, 128), (58, 112), (44, 92), (22, 74), (-4, 58), (-26, 42), (-40, 24),
         (-42, 6), (-34, -14), (-22, -34), (-12, -52), (-4, -72), (4, -92), (10, -110),
         # hillside switchbacks: legs run across the fall line (east-west) so the path climbs the
         # ~30 m face at a walkable pitch instead of straight up it
         (-4, -117), (-28, -121), (-44, -127), (-34, -134), (-8, -138), (20, -142), (36, -148),
         (24, -156), (0, -161), (-20, -167), (-24, -175), (-8, -182), (0, -192),
         (8, -206), (18, -222), (30, -244), (40, -268), (46, -292), (52, -316)]
TRAIL_WIDTH = 1.8

# Creek: flows west, crossing the footpath at the footbridge.
CREEK = [(420, 120), (330, 150), (250, 178), (170, 196), (90, 206), (12, 201), (-60, 214),
         (-140, 232), (-230, 246), (-320, 252), (-430, 262), (-540, 270)]
CREEK_WIDTH = 3.2
FOOTBRIDGE = ((12, 201), 'NW-SE')

# Rock ravine on the trail (Op01 ambush): walls rise either side of this stretch.
RAVINE = [(-26, -30), (-16, -48), (-6, -68), (2, -88), (8, -106)]

# Points of interest: name -> (x, z, flatten radius, extra)
POIS = {
    'camp':       dict(x=-20, z=486, r=16, note='Prologue: Halyard staging camp beside the ranger road'),
    'trailhead':  dict(x=-60, z=302, r=15, note='Turnout where the Mule parks; trunk scene; trail sign'),
    'cabin':      dict(x=62, z=124, r=15, note="Ranger Hollis's cabin, woodpile, water tank"),
    'relay':      dict(x=-42, z=16, r=8, raise_=13.0, raise_r=38, note='Relay mast on the knoll'),
    'ravine':     dict(x=-4, z=-70, r=0, note='Ambush: Greyline contractors on the rim'),
    'saddle':     dict(x=0, z=-194, r=9, note='Ridge saddle overlook: first view of the perimeter'),
    'gate':       dict(x=48, z=-342, r=14, note='Perimeter gate and guard hut'),
    'compound':   dict(x=10, z=-385, r=0, note='Compound yard'),
    'facility':   dict(x=0, z=-448, r=12, h=70.6, fall=16, note='Facility entrance portal in the mountain face'),
}

# Perimeter: fence line (west to east) and cleared strip half-width.
FENCE = [(-230, -332), (-120, -338), (-40, -341), (48, -342), (140, -336), (232, -326)]
FENCE_CLEAR = 14.0
COMPOUND = dict(x0=-150, x1=170, z0=-430, z1=-346, h=70.5)

# Vegetation regions: forest cover fraction by z, thinned on the hillside, sparse on the north slope.
FOREST_Z = [512, 420, 120, 0, -60, -120, -175, -205, -260, -320, -512]
FOREST_C = [0.95, 1.0, 1.0, 0.95, 0.75, 0.38, 0.12, 0.05, 0.14, 0.0, 0.0]

# Play area boundary (soft): mountains rise outside this, trees stay dense out there.
PLAY_X = 300.0
