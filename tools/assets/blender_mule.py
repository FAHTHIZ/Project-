# SPDX-License-Identifier: Apache-2.0
"""HT-4 "Mule" hero rebuild in Blender: modelled panels and a baked PBR finish.

    blender -b --factory-startup --python tools/assets/blender_mule.py -- <out_dir> [part ...]

Replaces the box-built parts from tools/props/build_vehicle.py with the same files, pivots and
dimensions (tools/scenes/vehicle_layout.json), so vehicle.luau, the seat/door/hatch markers, the
colliders and the cinematics do not change:

  mule_body        side panels cut round real wheel arches, bevelled hood/roof/pillars, upright
                   windscreen frame, round lamps in bezels, tube bumper/brush guard/roof rack,
                   arch flares, rock sliders, hinges, mirrors, mud flaps, antenna; cabin interior
                   (dash with gauge pods and radio stack, console, cushioned seats, cargo bay)
  mule_glass       windscreen + rear quarter windows
  mule_door_<k>    door shells (hinge space: hinge line at x = z = 0, panel to +Z)
  mule_door_glass  one door window shared by the four doors
  mule_hatch       rear hatch (hinge space, hangs to -Y), mule_hatch_glass its window
  mule_wheel       lugged off-road tyre on a steel wheel (hub origin, axle along X)
  mule_steering    steering wheel (column along local +Z)

Every edge is bevelled in geometry (the box build had razor edges that read as CG under the
lamps), then blender_bake.bake_hero bakes AO, edge wear and CC0 ambientCG scan detail into one
material per part (exterior and interior separately), plus a height-driven road-dirt layer.
All geometry is original; the vehicle is not modelled on any real one.
"""
import math
import os
import sys

import bpy
import bmesh
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blender_bake as bk  # noqa: E402

W = 0.97          # half width of the body sides
ROOF = 2.04       # roof skin underside: seated crew helmets reach ~2.0 m (old box roof topped at 2.07)
R_WHEEL = 0.40
AXLE_F, AXLE_R = -1.55, 1.45


def lin(h):
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


# design colours (linear) per material role
COL = {
    'Paint': lin('#4b5444'), 'Clad': lin('#232526'), 'Interior': lin('#34373a'), 'Seat': lin('#3a3a34'),
    'Floor': lin('#1e2021'), 'Trim': lin('#6d7173'), 'Tyre': lin('#1d1d1d'), 'Rim': lin('#3f463a'),
    'Accent': lin('#c48a2c'), 'Plate': lin('#d8d3c4'), 'Gauge': lin('#0d0f10'),
}
PRESETS = {
    'Paint': dict(scan='PaintedMetal004', tile=0.6, contrast=0.12, nor=0.35, rough=0.5, metal=0.15, wear=0.55, paint=True),
    'Accent': dict(scan='PaintedMetal004', tile=0.6, contrast=0.12, nor=0.3, rough=0.45, metal=0.1, wear=0.6, paint=True),
    'Rim': dict(scan='PaintedMetal006', tile=0.3, contrast=0.15, nor=0.4, rough=0.5, metal=0.2, wear=0.7, paint=True),
    'Clad': dict(scan='Plastic006', tile=0.35, contrast=0.3, nor=0.6, rough=0.72, metal=0.0, wear=0.35),
    'Interior': dict(scan='Plastic006', tile=0.3, contrast=0.25, nor=0.5, rough=0.7, metal=0.0, wear=0.3),
    'Seat': dict(scan='Fabric030', tile=0.18, contrast=0.35, nor=0.9, rough=0.9, metal=0.0, wear=0.15),
    'Floor': dict(scan='Rubber004', tile=0.2, contrast=0.3, nor=0.8, rough=0.85, metal=0.0, wear=0.1),
    'Tyre': dict(scan='Rubber004', tile=0.12, contrast=0.35, nor=0.9, rough=0.88, metal=0.0, wear=0.05),
    'Trim': dict(scan='Metal032', tile=0.3, contrast=0.2, nor=0.4, rough=0.38, metal=0.85, wear=0.5),
    'Plate': dict(scan='PaintedMetal004', tile=0.4, contrast=0.1, nor=0.2, rough=0.5, metal=0.1, wear=0.4, paint=True),
    'Gauge': dict(scan='Plastic006', tile=0.2, contrast=0.1, nor=0.2, rough=0.3, metal=0.0, wear=0.0),
}
KEEP_ROLES = ('Lamp', 'Tail', 'Amber', 'Glass')


# --------------------------------------------------------------------------------------------
# coordinates: author in the vehicle frame (x right, y up, -z forward); Blender is z up, and the
# glTF exporter's +Y-up conversion maps Blender (x, y, z) to glTF (x, z, -y).
def V(x, y, z):
    return Vector((x, -z, y))


_mats = {}


def mat(role):
    if role in _mats:
        return _mats[role]
    m = bpy.data.materials.new('mule_' + role)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    if role == 'Glass':
        b.inputs['Base Color'].default_value = (0.16, 0.2, 0.22, 0.38)
        b.inputs['Roughness'].default_value = 0.06
        b.inputs['Alpha'].default_value = 0.38
        m.blend_method = 'BLEND'
    elif role in ('Lamp', 'Tail', 'Amber'):
        e = {'Lamp': (1.0, 0.95, 0.85), 'Tail': (0.9, 0.08, 0.04), 'Amber': (1.0, 0.55, 0.08)}[role]
        b.inputs['Base Color'].default_value = (*e, 1)
        b.inputs['Emission Color'].default_value = (*e, 1)
        b.inputs['Emission Strength'].default_value = {'Lamp': 2.0, 'Tail': 1.4, 'Amber': 0.8}[role]
        b.inputs['Roughness'].default_value = 0.2
    else:
        b.inputs['Base Color'].default_value = (*COL[role], 1)
        b.inputs['Roughness'].default_value = PRESETS[role]['rough']
    _mats[role] = m
    return m


class Part:
    """Collects bmesh pieces per material role, each bevelled on its own, then one object."""

    def __init__(self, name):
        self.name = name
        self.obs = []

    def _ob(self, bm, role, bevel, segs=2, smooth=False, sub=0):
        me = bpy.data.meshes.new(self.name + '_' + role)
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new(me.name, me)
        bpy.context.scene.collection.objects.link(ob)
        me.materials.append(mat(role))
        if bevel > 0:
            md = ob.modifiers.new('bv', 'BEVEL')
            md.width = bevel
            md.segments = segs
            md.limit_method = 'ANGLE'
            md.angle_limit = math.radians(35)
            md.harden_normals = True
            md.miter_outer = 'MITER_ARC'
        if sub:
            md = ob.modifiers.new('sub', 'SUBSURF')
            md.levels = sub
            md.render_levels = sub
        if smooth or bevel > 0:
            for p in me.polygons:
                p.use_smooth = True
        self.obs.append(ob)
        return ob

    # primitives --------------------------------------------------------------------------
    def box(self, lo, hi, role, bevel=0.012, segs=2):
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        c = [(lo[i] + hi[i]) / 2 for i in range(3)]
        s = [abs(hi[i] - lo[i]) for i in range(3)]
        for v in bm.verts:
            p = v.co
            v.co = V(c[0] + p.x * s[0], c[1] + p.z * s[1], c[2] - p.y * s[2])
        bevel = min(bevel, min(s) * 0.45)
        return self._ob(bm, role, bevel, segs)

    def hexa(self, pts, role, bevel=0.012, segs=2):
        """8 corners: bottom quad then top quad, same winding (vehicle frame)."""
        bm = bmesh.new()
        vs = [bm.verts.new(V(*p)) for p in pts]
        for f in ((0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
            try:
                bm.faces.new([vs[i] for i in f])
            except ValueError:
                pass
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        return self._ob(bm, role, bevel, segs)

    def prism_x(self, zy, x0, x1, role, bevel=0.012, segs=2):
        """Polygon in the side plane (z, y), extruded across x0..x1 (concave outlines are fine)."""
        bm = bmesh.new()
        a = [bm.verts.new(V(x0, y, z)) for z, y in zy]
        b = [bm.verts.new(V(x1, y, z)) for z, y in zy]
        n = len(zy)
        bm.faces.new(a)
        bm.faces.new(b[::-1])
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new([a[i], a[j], b[j], b[i]])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        return self._ob(bm, role, bevel, segs)

    def prism_z(self, xy, z0, z1, role, bevel=0.012, segs=2):
        """Polygon in the cross-section plane (x, y), extruded along z0..z1."""
        bm = bmesh.new()
        a = [bm.verts.new(V(x, y, z0)) for x, y in xy]
        b = [bm.verts.new(V(x, y, z1)) for x, y in xy]
        n = len(xy)
        bm.faces.new(a)
        bm.faces.new(b[::-1])
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new([a[i], a[j], b[j], b[i]])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        return self._ob(bm, role, bevel, segs)

    def cyl(self, p0, p1, r, role, segs=16, bevel=0.0, cap=True):
        bm = bmesh.new()
        a, b = V(*p0), V(*p1)
        d = b - a
        L = d.length
        bmesh.ops.create_cone(bm, cap_ends=cap, segments=segs, radius1=r, radius2=r, depth=L)
        q = Vector((0, 0, 1)).rotation_difference(d.normalized())
        for v in bm.verts:
            v.co = q @ v.co + (a + b) / 2
        return self._ob(bm, role, bevel, 1, smooth=True)

    def tube(self, pts, r, role, segs=10):
        """Bent tube through vehicle-frame points (bumpers, guards, rack)."""
        cu = bpy.data.curves.new(self.name + '_tube', 'CURVE')
        cu.dimensions = '3D'
        cu.bevel_depth = r
        cu.bevel_resolution = max(1, segs // 4)
        cu.use_fill_caps = True
        sp = cu.splines.new('POLY')
        sp.points.add(len(pts) - 1)
        for i, p in enumerate(pts):
            sp.points[i].co = (*V(*p), 1)
        ob = bpy.data.objects.new(cu.name, cu)
        bpy.context.scene.collection.objects.link(ob)
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.select_all(action='DESELECT')
        ob.select_set(True)
        bpy.ops.object.convert(target='MESH')
        ob = bpy.context.view_layer.objects.active
        ob.data.materials.clear()
        ob.data.materials.append(mat(role))
        for p in ob.data.polygons:
            p.use_smooth = True
        self.obs.append(ob)
        return ob

    def lathe(self, prof, segs, role, axis_x=True, smooth=True):
        """Surface of revolution of [(radius, axial)] about the X axis (vehicle frame)."""
        bm = bmesh.new()
        rings = []
        for k in range(segs):
            t = 2 * math.pi * k / segs
            rings.append([bm.verts.new(V(ax, r * math.cos(t), r * math.sin(t))) for r, ax in prof])
        for k in range(segs):
            r0, r1 = rings[k], rings[(k + 1) % segs]
            for i in range(len(prof) - 1):
                bm.faces.new([r0[i], r0[i + 1], r1[i + 1], r1[i]])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        return self._ob(bm, role, 0.0, smooth=smooth)

    def rounded(self, c, half, role, sub=2, bevel=0.0):
        """Cushion: a box smoothed by subdivision (seats, armrests)."""
        lo = [c[i] - half[i] for i in range(3)]
        hi = [c[i] + half[i] for i in range(3)]
        ob = self.box(lo, hi, role, bevel=0.0)
        md = ob.modifiers.new('sub', 'SUBSURF')
        md.levels = sub
        md.render_levels = sub
        for p in ob.data.polygons:
            p.use_smooth = True
        return ob

    def join(self):
        bpy.ops.object.select_all(action='DESELECT')
        for o in self.obs:
            o.select_set(True)
        bpy.context.view_layer.objects.active = self.obs[0]
        bpy.ops.object.convert(target='MESH')  # applies the modifiers
        bpy.ops.object.join()
        ob = bpy.context.view_layer.objects.active
        ob.name = self.name
        # merge by distance would weld separate pieces' bevel seams; keep pieces separate
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.quads_convert_to_tris(quad_method='BEAUTY', ngon_method='BEAUTY')
        bpy.ops.object.mode_set(mode='OBJECT')
        return ob


def arc(zc, yc, r, a0, a1, n):
    return [(zc + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             yc + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def arch_flare(p, zc, sx):
    """Black arch flare: a ring sector over the tyre that runs down to the sill line."""
    ro, ri = 0.58, 0.49
    outer = [(zc - ro, 0.44)] + arc(zc, 0.42, ro, 180, 0, 18) + [(zc + ro, 0.44)]
    inner = [(zc + ri, 0.44)] + arc(zc, 0.42, ri, 0, 180, 18) + [(zc - ri, 0.44)]
    zy = outer + inner
    x0, x1 = (W - 0.03, W + 0.06) if sx > 0 else (-W - 0.06, -W + 0.03)
    # a ring sector is concave; split it into quads along the arc so each face is convex
    for i in range(len(outer) - 1):
        o0, o1 = outer[i], outer[i + 1]
        j = len(inner) - 1 - i
        i0, i1 = inner[j], inner[j - 1]
        p.prism_x([o0, o1, i1, i0], x0, x1, 'Clad', bevel=0.006, segs=1)


# --------------------------------------------------------------------------------------------
def body_exterior(p):
    for sx in (-1, 1):
        x0, x1 = (W - 0.06, W) if sx > 0 else (-W, -W + 0.06)
        # front fender side: real arch cut round the front tyre, top follows the hood line
        zy = [(-2.40, 0.50), (-2.07, 0.50)] + arc(AXLE_F, 0.42, 0.49, 180, 0, 20) + \
             [(-1.03, 0.50), (-1.03, 1.15), (-2.40, 1.05)]
        p.prism_x(zy, x0, x1, 'Paint', bevel=0.014)
        # rear quarter below the window line, arch round the rear tyre
        zy = [(0.95, 0.50), (0.96, 0.50)] + arc(AXLE_R, 0.42, 0.49, 180, 0, 20) + \
             [(1.95, 0.50), (2.40, 0.50), (2.40, 1.25), (0.95, 1.25)]
        p.prism_x(zy, x0, x1, 'Paint', bevel=0.014)
        # rear quarter window frame: C pillar, D pillar, sill and header
        p.box((x0, 1.25, 0.95), (x1, ROOF, 1.11), 'Paint')
        p.box((x0, 1.25, 2.25), (x1, ROOF, 2.40), 'Paint')
        p.box((x0, 1.25, 1.1), (x1, 1.31, 2.26), 'Paint', bevel=0.008)
        p.box((x0, 1.86, 1.1), (x1, ROOF, 2.26), 'Paint', bevel=0.008)
        # B pillar between the doors, and the sill under them
        p.box((x0, 0.50, -0.07), (x1, ROOF, 0.03), 'Paint', bevel=0.01)
        p.box((x0 - (0.01 if sx < 0 else 0), 0.44, -1.03), (x1 + (0.01 if sx > 0 else 0), 0.53, 0.96), 'Clad',
              bevel=0.012)
        # A pillar along the near-upright windscreen
        xa0, xa1 = (W - 0.08, W) if sx > 0 else (-W, -W + 0.08)
        p.hexa([(xa0, 1.13, -1.07), (xa1, 1.13, -1.07), (xa1, 1.13, -0.99), (xa0, 1.13, -0.99),
                (xa0, ROOF, -0.91), (xa1, ROOF, -0.91), (xa1, ROOF, -0.83), (xa0, ROOF, -0.83)], 'Paint', bevel=0.01)
        # roof side rail and rain gutter over the door openings
        p.box((x0, ROOF - 0.06, -0.92), (x1, ROOF + 0.02, 0.96), 'Paint', bevel=0.01)
        gx = sx * (W + 0.012)
        p.box((gx - 0.012, ROOF + 0.0, -0.9), (gx + 0.012, ROOF + 0.03, 2.38), 'Paint', bevel=0.006)
        # exterior door hinges (two per door, on the body side of each hinge line)
        for hz in (-1.03, -0.03):
            for hy in (0.78, 1.08):
                hx = sx * (W + 0.006)
                p.box((hx - 0.012, hy - 0.05, hz - 0.035), (hx + 0.012, hy + 0.05, hz + 0.03), 'Clad', bevel=0.005)
                p.cyl((hx + sx * 0.014, hy - 0.06, hz - 0.005), (hx + sx * 0.014, hy + 0.06, hz - 0.005), 0.011, 'Trim',
                      segs=8)
        # arch flares, rock slider tube, mud flaps
        for zc in (AXLE_F, AXLE_R):
            arch_flare(p, zc, sx)
        rx = sx * (W + 0.08)
        p.tube([(sx * (W - 0.02), 0.42, -1.0), (rx, 0.42, -0.92), (rx, 0.42, 0.88), (sx * (W - 0.02), 0.42, 0.96)],
               0.035, 'Clad')
        for z in (-0.6, 0.0, 0.6):
            p.cyl((sx * (W - 0.05), 0.42, z), (rx, 0.42, z), 0.022, 'Clad', segs=8)
        fx = sx * 0.84
        p.box((fx - 0.13, 0.14, 2.02), (fx + 0.13, 0.46, 2.04), 'Clad', bevel=0.004)
        # mirror: arm off the A-pillar foot and a rounded head
        mx = sx * (W + 0.05)
        p.cyl((sx * (W - 0.01), 1.22, -1.0), (mx, 1.36, -1.02), 0.012, 'Clad', segs=8)
        p.cyl((sx * (W - 0.01), 1.5, -0.97), (mx, 1.42, -1.0), 0.010, 'Clad', segs=8)
        p.rounded((sx * (W + 0.1), 1.39, -1.01), (0.055, 0.1, 0.022), 'Clad', sub=1)
        # amber unit stripe and side marker
        sxx = (W, W + 0.003) if sx > 0 else (-W - 0.003, -W)
        p.box((sxx[0], 1.0, 1.25), (sxx[1], 1.05, 2.3), 'Accent', bevel=0.0)
        p.box((sxx[0] + sx * 0.002, 0.85, -2.3), (sxx[1] + sx * 0.002, 0.9, -2.22), 'Amber', bevel=0.004)

    # roof: crowned skin with a stiffening rib pattern
    p.hexa([(-W, ROOF - 0.04, -0.92), (W, ROOF - 0.04, -0.92), (W, ROOF - 0.04, 2.40), (-W, ROOF - 0.04, 2.40),
            (-W + 0.04, ROOF + 0.04, -0.88), (W - 0.04, ROOF + 0.04, -0.88), (W - 0.04, ROOF + 0.04, 2.36),
            (-W + 0.04, ROOF + 0.04, 2.36)], 'Paint', bevel=0.03, segs=3)
    for z in (-0.3, 0.4, 1.1, 1.8):
        p.box((-W + 0.12, ROOF + 0.035, z - 0.04), (W - 0.12, ROOF + 0.055, z + 0.04), 'Paint', bevel=0.012)
    # roof rack: perimeter tube on six legs, four cross bars
    ry = ROOF + 0.15
    p.tube([(-0.86, ry, -0.66), (0.86, ry, -0.66), (0.86, ry, 2.24), (-0.86, ry, 2.24), (-0.86, ry, -0.66)], 0.019,
           'Clad')
    for z in (0.1, 0.8, 1.5):
        p.cyl((-0.86, ry, z), (0.86, ry, z), 0.016, 'Clad', segs=8)
    for sx in (-1, 1):
        for z in (-0.6, 0.8, 2.18):
            p.box((sx * 0.86 - 0.025, ROOF + 0.03, z - 0.03), (sx * 0.86 + 0.025, ry, z + 0.03), 'Clad', bevel=0.006)
    # antenna mount and whip, rear left corner
    p.cyl((-0.8, ROOF + 0.04, 2.25), (-0.8, ROOF + 0.12, 2.25), 0.03, 'Clad', segs=10)
    p.cyl((-0.8, ROOF + 0.12, 2.25), (-0.8, ROOF + 1.25, 2.25), 0.004, 'Clad', segs=5)

    # hood with a raised centre panel, latches, cowl under the windscreen
    p.hexa([(-W + 0.01, 1.0, -2.41), (W - 0.01, 1.0, -2.41), (W - 0.01, 1.1, -1.06), (-W + 0.01, 1.1, -1.06),
            (-W + 0.02, 1.05, -2.41), (W - 0.02, 1.05, -2.41), (W - 0.02, 1.15, -1.06), (-W + 0.02, 1.15, -1.06)],
           'Paint', bevel=0.02, segs=3)
    p.hexa([(-0.5, 1.04, -2.3), (0.5, 1.04, -2.3), (0.5, 1.14, -1.15), (-0.5, 1.14, -1.15),
            (-0.44, 1.075, -2.28), (0.44, 1.075, -2.28), (0.44, 1.175, -1.17), (-0.44, 1.175, -1.17)], 'Paint',
           bevel=0.02, segs=2)
    for sx in (-1, 1):
        p.box((sx * 0.8 - 0.03, 0.96, -2.43), (sx * 0.8 + 0.03, 1.03, -2.405), 'Clad', bevel=0.006)
    p.box((-W + 0.02, 1.1, -1.09), (W - 0.02, 1.17, -1.0), 'Clad', bevel=0.01)
    for sx in (-1, 1):  # wiper arms parked on the cowl
        p.cyl((sx * 0.2, 1.17, -1.04), (sx * 0.2 - 0.36, 1.2, -1.02), 0.007, 'Clad', segs=6)
    # windscreen frame cross members
    p.box((-W + 0.06, 1.12, -1.09), (W - 0.06, 1.17, -1.0), 'Paint', bevel=0.01)
    p.box((-W + 0.06, ROOF - 0.07, -0.93), (W - 0.06, ROOF, -0.84), 'Paint', bevel=0.01)

    # nose: grille panel with recessed slots, round headlamps in bezels, indicators
    p.box((-W, 0.53, -2.45), (W, 1.03, -2.36), 'Paint', bevel=0.015)
    p.box((-0.46, 0.6, -2.47), (0.46, 0.98, -2.44), 'Clad', bevel=0.004)
    for i in range(9):
        x = -0.4 + i * 0.1
        p.box((x - 0.022, 0.61, -2.49), (x + 0.022, 0.97, -2.455), 'Paint', bevel=0.008)
    for sx in (-1, 1):
        cx = sx * 0.7
        p.cyl((cx, 0.84, -2.49), (cx, 0.84, -2.43), 0.115, 'Trim', segs=24, bevel=0.006)
        p.cyl((cx, 0.84, -2.497), (cx, 0.84, -2.49), 0.092, 'Lamp', segs=24)
        p.cyl((sx * 0.86, 0.66, -2.47), (sx * 0.86, 0.66, -2.44), 0.035, 'Amber', segs=12)
    # front bumper: heavy steel box with tow hooks, brush guard tubes
    p.box((-1.0, 0.34, -2.62), (1.0, 0.56, -2.42), 'Clad', bevel=0.02)
    for sx in (-1, 1):
        x = sx * 0.62
        p.tube([(x, 0.4, -2.62), (x, 0.4, -2.7), (x, 0.5, -2.7), (x, 0.5, -2.62)], 0.016, 'Trim')
        p.tube([(sx * 0.55, 0.56, -2.56), (sx * 0.55, 0.98, -2.56), (sx * 0.42, 1.04, -2.5)], 0.024, 'Clad')
    p.tube([(-0.55, 0.98, -2.56), (0.55, 0.98, -2.56)], 0.024, 'Clad')
    p.tube([(-0.55, 0.78, -2.56), (0.55, 0.78, -2.56)], 0.02, 'Clad')
    p.box((-0.85, 0.26, -2.45), (0.85, 0.32, -1.4), 'Clad', bevel=0.02)          # skid plate
    p.box((-0.9, 0.32, -2.3), (0.9, 0.42, 2.3), 'Clad', bevel=0.01)               # underbody

    # rear face round the hatch opening, loading lip, lamps, bumper step, plate
    for sx in (-1, 1):
        x0, x1 = (0.84, W) if sx > 0 else (-W, -0.84)
        p.box((x0, 0.53, 2.32), (x1, ROOF, 2.40), 'Paint', bevel=0.012)
        p.box((sx * 0.905 - 0.05, 1.22, 2.395), (sx * 0.905 + 0.05, 1.56, 2.42), 'Clad', bevel=0.008)
        p.box((sx * 0.905 - 0.038, 1.42, 2.415), (sx * 0.905 + 0.038, 1.54, 2.425), 'Tail', bevel=0.004)
        p.box((sx * 0.905 - 0.038, 1.33, 2.415), (sx * 0.905 + 0.038, 1.41, 2.425), 'Amber', bevel=0.004)
        p.box((sx * 0.905 - 0.038, 1.24, 2.415), (sx * 0.905 + 0.038, 1.32, 2.425), 'Gauge', bevel=0.004)
    p.box((-0.84, 0.53, 2.30), (0.84, 0.74, 2.40), 'Paint', bevel=0.012)
    p.box((-1.0, 0.36, 2.40), (1.0, 0.6, 2.56), 'Clad', bevel=0.02)
    p.box((-0.6, 0.6, 2.42), (0.6, 0.61, 2.54), 'Trim', bevel=0.003)                # tread plate on the step
    p.box((-0.2, 0.43, 2.56), (0.2, 0.55, 2.565), 'Plate', bevel=0.003)
    p.tube([(0.5, 0.4, 2.56), (0.5, 0.4, 2.64), (0.5, 0.5, 2.64), (0.5, 0.5, 2.56)], 0.016, 'Trim')
    p.cyl((0.985, 0.98, 1.9), (0.995, 0.98, 1.9), 0.05, 'Clad', segs=14)          # fuel filler cap


def body_interior(p):
    p.box((-0.9, 0.5, -1.0), (0.9, 0.56, 1.12), 'Floor', bevel=0.005)
    p.box((-0.9, 0.56, -1.07), (0.9, 1.02, -0.99), 'Interior', bevel=0.01)          # firewall
    # dash: sloped top, gauge binnacle in front of the driver, radio stack in the centre
    p.prism_x([(-1.0, 0.98), (-0.74, 0.98), (-0.7, 1.12), (-0.8, 1.2), (-0.99, 1.21)], -0.92, 0.92, 'Interior',
              bevel=0.015)
    p.hexa([(-0.66, 1.12, -0.86), (-0.22, 1.12, -0.86), (-0.22, 1.12, -0.74), (-0.66, 1.12, -0.74),
            (-0.64, 1.25, -0.88), (-0.24, 1.25, -0.88), (-0.24, 1.25, -0.8), (-0.64, 1.25, -0.8)], 'Interior',
           bevel=0.012)
    for gx in (-0.54, -0.34):
        p.cyl((gx, 1.18, -0.78), (gx, 1.18, -0.75), 0.05, 'Gauge', segs=16)
        p.cyl((gx, 1.18, -0.751), (gx, 1.18, -0.748), 0.042, 'Plate', segs=16)
    p.box((-0.15, 0.72, -0.98), (0.15, 1.12, -0.72), 'Interior', bevel=0.01)
    for i, y in enumerate((1.04, 0.96, 0.88)):
        p.box((-0.12, y - 0.03, -0.73), (0.12, y + 0.03, -0.71), 'Gauge', bevel=0.004)
        p.box((-0.1 + 0.05 * i, y - 0.006, -0.712), (-0.08 + 0.05 * i, y + 0.006, -0.706), 'Amber', bevel=0.0)
    # console and transmission tunnel with a shifter
    p.box((-0.16, 0.56, -0.95), (0.16, 0.84, -0.1), 'Interior', bevel=0.02)
    p.cyl((0.0, 0.84, -0.6), (0.0, 1.02, -0.66), 0.012, 'Trim', segs=8)
    p.rounded((0.0, 1.04, -0.665), (0.025, 0.025, 0.025), 'Clad', sub=2)
    p.box((-0.9, ROOF - 0.03, -0.9), (0.9, ROOF - 0.01, 2.3), 'Interior', bevel=0.004)             # headliner
    for sx in (-1, 1):                                                           # quarter trim, grab handles
        p.box((sx * 0.9 - 0.012, 0.56, 1.1), (sx * 0.9 + 0.012, 1.22, 2.3), 'Interior', bevel=0.005)
        p.tube([(sx * 0.88, 1.84, -0.3), (sx * 0.84, 1.8, -0.28), (sx * 0.84, 1.8, -0.06), (sx * 0.88, 1.84, -0.04)],
               0.012, 'Clad')
    # front seats: cushion, back, headrest on a frame base
    for x in (-0.44, 0.44):
        p.rounded((x, 0.9, -0.38), (0.24, 0.07, 0.25), 'Seat', sub=2)
        p.hexa([(x - 0.24, 0.96, -0.2), (x + 0.24, 0.96, -0.2), (x + 0.24, 0.96, -0.06), (x - 0.24, 0.96, -0.06),
                (x - 0.22, 1.62, -0.14), (x + 0.22, 1.62, -0.14), (x + 0.22, 1.62, -0.02), (x - 0.22, 1.62, -0.02)],
               'Seat', bevel=0.05, segs=3)
        p.rounded((x, 1.73, -0.08), (0.12, 0.07, 0.05), 'Seat', sub=2)
        for dx in (-0.06, 0.06):
            p.cyl((x + dx, 1.6, -0.08), (x + dx, 1.67, -0.08), 0.007, 'Trim', segs=6)
        p.box((x - 0.18, 0.56, -0.56), (x + 0.18, 0.83, -0.2), 'Clad', bevel=0.015)
    # rear bench (three places) and its back / the bay divider
    p.rounded((0, 0.9, 0.62), (0.8, 0.07, 0.25), 'Seat', sub=2)
    p.hexa([(-0.8, 0.96, 0.84), (0.8, 0.96, 0.84), (0.8, 0.96, 0.98), (-0.8, 0.96, 0.98),
            (-0.78, 1.6, 0.9), (0.78, 1.6, 0.9), (0.78, 1.6, 1.0), (-0.78, 1.6, 1.0)], 'Seat', bevel=0.05, segs=3)
    for x in (-0.5, 0.0, 0.5):
        p.rounded((x, 1.71, 0.95), (0.12, 0.06, 0.045), 'Seat', sub=2)
    p.box((-0.8, 0.56, 0.4), (0.8, 0.83, 0.86), 'Clad', bevel=0.015)
    p.box((-0.9, 0.56, 1.0), (0.9, 1.32, 1.1), 'Interior', bevel=0.01)
    # cargo bay: raised floor with load rails, wheel tubs, tie-down rings
    p.box((-0.9, 0.56, 1.1), (0.9, 0.74, 2.32), 'Interior', bevel=0.006)
    p.box((-0.84, 0.74, 1.12), (0.84, 0.752, 2.3), 'Floor', bevel=0.002)
    for z in (1.4, 1.8, 2.15):
        p.box((-0.8, 0.752, z - 0.012), (0.8, 0.77, z + 0.012), 'Trim', bevel=0.004)
    for sx in (-1, 1):
        p.rounded((sx * 0.74, 0.84, AXLE_R), (0.12, 0.1, 0.36), 'Interior', sub=1)
        for z in (1.2, 2.2):
            p.tube([(sx * 0.82, 0.76, z - 0.03), (sx * 0.82, 0.8, z), (sx * 0.82, 0.76, z + 0.03)], 0.006, 'Trim')


def glass(p):
    # windscreen in the near-upright frame, rear quarter windows
    p.hexa([(-0.89, 1.15, -1.03), (0.89, 1.15, -1.03), (0.89, 1.15, -1.01), (-0.89, 1.15, -1.01),
            (-0.89, ROOF - 0.05, -0.89), (0.89, ROOF - 0.05, -0.89), (0.89, ROOF - 0.05, -0.87),
            (-0.89, ROOF - 0.05, -0.87)], 'Glass', bevel=0.0)
    for sx in (-1, 1):
        x = sx * 0.955
        p.box((x - 0.006, 1.29, 1.1), (x + 0.006, 1.87, 2.26), 'Glass', bevel=0.0)


def door(p, side, front):
    """Hinge space: hinge line at x = z = 0, the panel runs to +Z, outer skin at x = 0."""
    L = 0.96 if front else 0.94
    s = -1 if side == 'l' else 1
    xi = -s * 0.07
    lo, hi = min(0.0, xi), max(0.0, xi)
    # lower door: skin with a pressed horizontal swage line, top capping rail at the belt
    p.box((lo, 0.5, 0.005), (hi, 1.18, L - 0.005), 'Paint', bevel=0.016, segs=3)
    sw = (0.0, s * 0.008) if s > 0 else (s * 0.008, 0.0)
    p.box((sw[0], 0.86, 0.04), (sw[1], 0.9, L - 0.04), 'Paint', bevel=0.004)
    p.box((lo, 1.16, 0.005), (hi, 1.21, L - 0.005), 'Paint', bevel=0.012)
    # window frame: front post, rear post, header
    fi, fo = (lo + 0.012, hi - 0.012)
    p.box((fi, 1.2, 0.005), (fo, ROOF - 0.02, 0.16), 'Paint', bevel=0.01)
    p.box((fi, 1.2, L - 0.06), (fo, ROOF - 0.02, L - 0.005), 'Paint', bevel=0.01)
    p.box((fi, ROOF - 0.08, 0.005), (fo, ROOF - 0.02, L - 0.005), 'Paint', bevel=0.01)
    # window seals
    p.box((fi + 0.01, 1.19, 0.16), (fo - 0.01, 1.215, L - 0.06), 'Clad', bevel=0.004)
    # inner door card with an armrest pull and a speaker grille
    ci = (min(xi, xi - s * 0.014), max(xi, xi - s * 0.014))
    p.box((ci[0], 0.56, 0.04), (ci[1], 1.15, L - 0.04), 'Interior', bevel=0.01)
    p.rounded((xi - s * 0.04, 0.98, L * 0.55), (0.03, 0.025, L * 0.28), 'Interior', sub=1)
    p.cyl((xi - s * 0.016, 0.7, L * 0.35), (xi - s * 0.022, 0.7, L * 0.35), 0.07, 'Clad', segs=16)
    # outer handle in a recessed cup, lock barrel; lower cladding
    hx = s * 0.004
    p.box((hx - 0.008, 1.03, L - 0.24), (hx + 0.008, 1.09, L - 0.1), 'Clad', bevel=0.006)
    p.rounded((s * 0.016, 1.06, L - 0.17), (0.01, 0.014, 0.06), 'Trim', sub=1)
    p.box((lo - (0.006 if s < 0 else 0), 0.5, 0.005), (hi + (0.006 if s > 0 else 0), 0.6, L - 0.005), 'Clad',
          bevel=0.01)


def door_glass(p):
    p.box((-0.006, 1.21, 0.16), (0.006, ROOF - 0.08, 0.89), 'Glass', bevel=0.0)


HATCH_K = (1.16 + 0.12) / 1.16    # hatch hangs from the lifted hinge to the unchanged loading lip


def hatch(p):
    k = HATCH_K
    p.box((-0.84, -1.16 * k, -0.02), (0.84, -0.62 * k, 0.05), 'Paint', bevel=0.016, segs=3)
    p.box((-0.84, -0.62 * k, -0.02), (-0.73, 0.0, 0.05), 'Paint', bevel=0.012)
    p.box((0.73, -0.62 * k, -0.02), (0.84, 0.0, 0.05), 'Paint', bevel=0.012)
    p.box((-0.84, -0.09 * k, -0.02), (0.84, 0.0, 0.05), 'Paint', bevel=0.012)
    p.box((-0.8, -1.12 * k, -0.05), (0.8, -0.64 * k, -0.02), 'Interior', bevel=0.008)
    # swage line, handle in a cup, plate, rubber stops, hinge knuckles at the roof
    p.box((-0.8, -0.95 * k, 0.05), (0.8, -0.92 * k, 0.058), 'Paint', bevel=0.004)
    p.box((-0.14, -0.76 * k, 0.05), (0.14, -0.69 * k, 0.06), 'Clad', bevel=0.006)
    p.rounded((0, -0.725 * k, 0.066), (0.1, 0.012, 0.008), 'Trim', sub=1)
    p.box((-0.12, -0.84 * k, 0.05), (0.12, -0.78 * k, 0.056), 'Plate', bevel=0.002)
    p.box((-0.84, -1.16 * k, 0.05), (0.84, -1.1 * k, 0.065), 'Clad', bevel=0.008)
    for sx in (-1, 1):
        p.cyl((sx * 0.55 - 0.08, 0.0, 0.03), (sx * 0.55 + 0.08, 0.0, 0.03), 0.022, 'Clad', segs=10)
        p.box((sx * 0.62 - 0.03, -1.12 * k, -0.06), (sx * 0.62 + 0.03, -1.06 * k, -0.04), 'Clad', bevel=0.006)


def hatch_glass(p):
    k = HATCH_K
    p.box((-0.73, -0.62 * k, 0.008), (0.73, -0.09 * k, 0.02), 'Glass', bevel=0.0)


def wheel(p):
    R, Wd = R_WHEEL, 0.28
    h = Wd / 2
    # carcass: sidewall bulge, rounded shoulders, slightly crowned crown
    prof = [(0.255, -h + 0.02), (0.3, -h), (0.35, -h - 0.004), (0.375, -h + 0.012), (0.39, -h + 0.035),
            (0.394, -h * 0.5), (0.396, 0.0), (0.394, h * 0.5), (0.39, h - 0.035), (0.375, h - 0.012),
            (0.35, h + 0.004), (0.3, h), (0.255, h - 0.02)]
    p.lathe(prof, 36, 'Tyre')
    # mud-terrain lugs: two staggered rows of chunky blocks that wrap over the shoulders
    n = 26
    for k in range(n):
        for row, (x0, x1) in enumerate(((-h + 0.004, -0.012), (0.012, h - 0.004))):
            t = 2 * math.pi * (k + 0.5 * row) / n
            a, b = (x0, x1)
            bm = bmesh.new()
            w = 0.022
            pts = []
            for xa in (a, b):
                for dt in (-w, w):
                    for rr in (R - 0.006, R + 0.016):
                        # shoulders: the outer end of each lug drops down the sidewall
                        drop = 0.02 if abs(xa) > h - 0.02 else 0.0
                        r_ = rr - drop
                        ang = t + dt / R + (0.012 if xa > 0 else -0.012) * (1 if row else -1)
                        pts.append(V(xa, r_ * math.cos(ang), r_ * math.sin(ang)))
            vs = [bm.verts.new(q) for q in pts]
            bmesh.ops.convex_hull(bm, input=vs)
            ob = p._ob(bm, 'Tyre', 0.0, 0)   # unbevelled: the bake carries the edge wear
    # steel wheel: dished disc, rim flanges, eight lug nuts, hub cap
    rim = [(0.255, -h + 0.02), (0.262, -h + 0.03), (0.262, -h + 0.06), (0.24, -h + 0.07), (0.235, -0.04),
           (0.2, 0.02), (0.12, 0.035), (0.09, 0.03), (0.0, 0.03)]
    p.lathe(rim, 28, 'Rim')
    p.lathe([(0.255, h - 0.02), (0.262, h - 0.03), (0.262, h - 0.06), (0.24, h - 0.07), (0.2, h - 0.08)], 28, 'Rim')
    for k in range(8):
        t = 2 * math.pi * k / 8
        y, z = 0.075 * math.cos(t), 0.075 * math.sin(t)
        p.cyl((0.03, y, z), (0.05, y, z), 0.013, 'Trim', segs=6)
    for k in range(6):   # vent holes read as dark recesses in the disc
        t = 2 * math.pi * (k + 0.5) / 6
        y, z = 0.165 * math.cos(t), 0.165 * math.sin(t)
        p.cyl((0.005, y, z), (0.03, y, z), 0.028, 'Clad', segs=8)
    p.cyl((0.03, 0, 0), (0.07, 0, 0), 0.045, 'Rim', segs=16, bevel=0.006)


def steering(p):
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=False, radius=0.18, segments=32)
    me = bpy.data.meshes.new('ring')
    bm.to_mesh(me)
    bm.free()
    # torus from a curve circle (smooth grip)
    cu = bpy.data.curves.new('ringc', 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = 0.016
    cu.bevel_resolution = 3
    sp = cu.splines.new('POLY')
    pts = [(0.18 * math.cos(2 * math.pi * i / 32), 0.18 * math.sin(2 * math.pi * i / 32), 0.0) for i in range(32)]
    sp.points.add(len(pts) - 1)
    for i, q in enumerate(pts):
        sp.points[i].co = (*V(*q), 1)
    sp.use_cyclic_u = True
    ob = bpy.data.objects.new('ringo', cu)
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.ops.object.convert(target='MESH')
    ob = bpy.context.view_layer.objects.active
    ob.data.materials.append(mat('Clad'))
    for f in ob.data.polygons:
        f.use_smooth = True
    p.obs.append(ob)
    for ang in (0, 2.3, 3.98):
        d = (math.cos(ang), math.sin(ang))
        p.cyl((d[0] * 0.035, d[1] * 0.035, 0.0), (d[0] * 0.17, d[1] * 0.17, 0.0), 0.013, 'Clad', segs=8)
    p.cyl((0, 0, -0.012), (0, 0, 0.03), 0.055, 'Clad', segs=20, bevel=0.008)
    p.cyl((0, 0, -0.016), (0, 0, -0.012), 0.03, 'Accent', segs=16)
    p.cyl((0, 0, 0.03), (0, 0, 0.32), 0.028, 'Clad', segs=8)


# --------------------------------------------------------------------------------------------
SIZES = {'mule_body_ext': 1024, 'mule_body_int': 1024, 'mule_door': 512, 'mule_hatch': 512, 'mule_wheel': 512,
         'mule_steering': 256}


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _mats.clear()


def baked(build, name, size, dirt=True, y0=0.0, **kw):
    p = Part(name)
    build(p, **kw)
    ob = p.join()
    tris = len(ob.data.polygons)
    if all(s.material.name.split('_', 1)[1] in KEEP_ROLES for s in ob.material_slots):
        return ob, tris
    presets = {}
    keep = set()
    for s in ob.material_slots:
        role = s.material.name.split('_', 1)[1]
        if role in KEEP_ROLES:
            keep.add(s.material.name)
        else:
            presets[s.material.name] = dict(PRESETS[role], color=COL[role])
    d = dict(top=0.95, color=lin('#5a4a38'), amount=0.85, y0=y0) if dirt else None
    bk.bake_hero(ob, size, presets, keep, name, os.environ.get('MULE_DEBUG'), ao_distance=0.18,
                 edge_radius=0.006, normal_radius=0.004, dirt=d)
    for a in list(ob.data.color_attributes):
        ob.data.color_attributes.remove(a)
    return ob, tris


def export(obs, path):
    bpy.ops.object.select_all(action='DESELECT')
    for o in obs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = obs[0]
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_tangents=True,
                              export_yup=True, export_apply=True, export_image_format='AUTO')


def build_all(out, only):
    report = []

    def want(n):
        return not only or n in only

    if want('mule_body'):
        reset()
        a, ta = baked(body_exterior, 'mule_body_ext', SIZES['mule_body_ext'])
        b, tb = baked(body_interior, 'mule_body_int', SIZES['mule_body_int'], dirt=False)
        export([a, b], os.path.join(out, 'mule_body.glb'))
        report.append(('mule_body', ta + tb))
    if want('mule_glass'):
        reset()
        a, t = baked(glass, 'mule_glass', 0)
        export([a], os.path.join(out, 'mule_glass.glb'))
        report.append(('mule_glass', t))
    for key in ('fl', 'fr', 'rl', 'rr'):
        n = 'mule_door_' + key
        if want(n):
            reset()
            a, t = baked(door, n, SIZES['mule_door'], side=key[1], front=key[0] == 'f')
            export([a], os.path.join(out, n + '.glb'))
            report.append((n, t))
    for n, fn in (('mule_door_glass', door_glass), ('mule_hatch_glass', hatch_glass)):
        if want(n):
            reset()
            a, t = baked(fn, n, 0)
            export([a], os.path.join(out, n + '.glb'))
            report.append((n, t))
    if want('mule_hatch'):
        reset()
        a, t = baked(hatch, 'mule_hatch', SIZES['mule_hatch'], y0=2.02)
        export([a], os.path.join(out, 'mule_hatch.glb'))
        report.append(('mule_hatch', t))
    if want('mule_wheel'):
        reset()
        a, t = baked(wheel, 'mule_wheel', SIZES['mule_wheel'], dirt=False)
        export([a], os.path.join(out, 'mule_wheel.glb'))
        report.append(('mule_wheel', t))
    if want('mule_steering'):
        reset()
        a, t = baked(steering, 'mule_steering', SIZES['mule_steering'], dirt=False)
        export([a], os.path.join(out, 'mule_steering.glb'))
        report.append(('mule_steering', t))
    for n, t in report:
        print(f'MULE {n:18s} {t:6d} tris', flush=True)


if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    os.makedirs(argv[0], exist_ok=True)
    build_all(argv[0], set(argv[1:]))
