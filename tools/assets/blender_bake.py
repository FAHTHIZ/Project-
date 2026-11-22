# SPDX-License-Identifier: Apache-2.0
"""Blender-side hero texture bake for hard-surface props (used by blender_pc7.py).

bake_hero(ob, size, presets, keep, name) turns a joined, multi-material hard-surface mesh into
one textured PBR material plus the materials named in `keep` (emissive parts):

1. smart-project a fresh UV layer (becomes TEXCOORD_0);
2. Cycles bakes, per texel: material id, ambient occlusion, a bevel-normal edge mask, the box-
   projected CC0 scan (luminance + roughness) of each material's preset, and a tangent-space
   normal map (bevel-rounded edges + scan micro normal);
3. numpy composites base colour (design colour x scan detail, cavity grime from AO, edge wear
   that lightens polymer and exposes bare metal under paint) and metallic-roughness;
4. the textured material replaces every non-kept slot (fewer draw calls on the phone).

presets: material name -> dict(scan=<ambientCG id>, tile=m, contrast, wear, nor, metal, rough,
color=(linear rgb)). Scan files come from tools/assets/ambientcg.py's cache (CC0).
"""
import glob
import math
import os

import bpy
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE = os.path.join(ROOT, '.cache', 'ambientcg')


def scan(asset, role):
    tag = {'diff': '_Color', 'nor': '_NormalGL', 'rough': '_Roughness'}[role]
    hit = sorted(glob.glob(os.path.join(CACHE, asset, '1K', f'*{tag}.jpg')))
    if not hit:
        raise SystemExit(f'missing scan {asset} {role}: run python3 tools/assets/ambientcg.py {asset}')
    im = bpy.data.images.load(hit[0], check_existing=True)
    if role != 'diff':
        im.colorspace_settings.name = 'Non-Color'
    return im


def new_image(name, size, float_buf=True):
    im = bpy.data.images.new(name, size, size, alpha=False, float_buffer=float_buf)
    im.colorspace_settings.name = 'Non-Color'
    return im


def _box_tex(nt, image, tile):
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (1 / tile, 1 / tile, 1 / tile)
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector'])
    tx = nt.nodes.new('ShaderNodeTexImage')
    tx.image = image
    tx.projection = 'BOX'
    tx.projection_blend = 0.25
    nt.links.new(mp.outputs['Vector'], tx.inputs['Vector'])
    return tx


def _bake(ob, kind, target, setup, samples=8, margin=8):
    """setup(material, node_tree, index) wires the material for this pass; returns nothing."""
    saved = []
    for i, slot in enumerate(ob.material_slots):
        m = slot.material
        nt = m.node_tree
        saved.append((m, [(l.from_socket, l.to_socket) for l in nt.links], [n.name for n in nt.nodes]))
        setup(m, nt, i)
        tn = nt.nodes.new('ShaderNodeTexImage')
        tn.image = target
        tn.name = '__bake_target'
        nt.nodes.active = tn
    sc = bpy.context.scene
    sc.cycles.samples = samples
    sc.render.bake.margin = margin
    sc.render.bake.use_clear = True
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    if kind == 'NORMAL':
        bpy.ops.object.bake(type='NORMAL', normal_space='TANGENT', uv_layer='bake')
    elif kind == 'AO':
        bpy.ops.object.bake(type='AO', uv_layer='bake')
    else:
        bpy.ops.object.bake(type='EMIT', uv_layer='bake')
    # restore each material: drop the pass nodes, relink the originals
    for m, links, names in saved:
        nt = m.node_tree
        for n in list(nt.nodes):
            if n.name not in names:
                nt.nodes.remove(n)
        for l in list(nt.links):
            nt.links.remove(l)
        for a, b in links:
            nt.links.new(a, b)
    return np.array(target.pixels[:], dtype=np.float32).reshape(target.size[1], target.size[0], 4)


def _emit(nt, sock_or_value):
    out = nt.nodes['Material Output']
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Strength'].default_value = 1.0
    if isinstance(sock_or_value, tuple):
        em.inputs['Color'].default_value = (*sock_or_value, 1)
    else:
        nt.links.new(sock_or_value, em.inputs['Color'])
    for l in list(out.inputs['Surface'].links):
        nt.links.remove(l)
    nt.links.new(em.outputs['Emission'], out.inputs['Surface'])


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def to_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)


def bake_hero(ob, size, presets, keep, name, out_dir=None, ao_distance=0.02, edge_radius=0.0014,
              normal_radius=0.0012, dirt=None):
    """ao_distance/edge_radius/normal_radius default to weapon scale (metres). dirt: optional
    dict(top=<height m>, color=(linear rgb), amount=0..1) for a road-dirt layer that thickens
    toward the ground (object-space up), broken up by noise; used by the vehicle."""
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.use_denoising = False
    sc.world = sc.world or bpy.data.worlds.new('w')
    sc.world.light_settings.distance = ao_distance  # AO reach in metres
    me = ob.data
    for uv in list(me.uv_layers):
        me.uv_layers.remove(uv)
    me.uv_layers.new(name='bake')
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.004, area_weight=0.0, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.004, rotate=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    slots = [s.material for s in ob.material_slots]
    idx = {m.name: i for i, m in enumerate(slots)}

    # 1. material id (R = index / 32)
    tid = new_image(name + '_id', size)
    ids = _bake(ob, 'EMIT', tid, lambda m, nt, i: _emit(nt, (i / 32.0, 0.0, 0.0)), samples=1, margin=4)
    mid = np.rint(ids[..., 0] * 32).astype(np.int32)

    # 2. ambient occlusion (local, 2 cm)
    tao = new_image(name + '_ao', size)
    ao = _bake(ob, 'AO', tao, lambda m, nt, i: None, samples=24)[..., 0]

    # 3. edge mask from bevel normal vs true normal
    def edge_setup(m, nt, i):
        bv = nt.nodes.new('ShaderNodeBevel')
        bv.samples = 8
        bv.inputs['Radius'].default_value = edge_radius
        geo = nt.nodes.new('ShaderNodeNewGeometry')
        dot = nt.nodes.new('ShaderNodeVectorMath')
        dot.operation = 'DOT_PRODUCT'
        nt.links.new(bv.outputs['Normal'], dot.inputs[0])
        nt.links.new(geo.outputs['Normal'], dot.inputs[1])
        inv = nt.nodes.new('ShaderNodeMath')
        inv.operation = 'SUBTRACT'
        inv.inputs[0].default_value = 1.0
        nt.links.new(dot.outputs['Value'], inv.inputs[1])
        mul = nt.nodes.new('ShaderNodeMath')
        mul.operation = 'MULTIPLY'
        mul.inputs[1].default_value = 6.0
        nt.links.new(inv.outputs['Value'], mul.inputs[0])
        comb = nt.nodes.new('ShaderNodeCombineColor')
        nt.links.new(mul.outputs['Value'], comb.inputs[0])
        _emit(nt, comb.outputs['Color'])
    tedge = new_image(name + '_edge', size)
    edge = _bake(ob, 'EMIT', tedge, edge_setup, samples=4)[..., 0]

    # 4. scan detail: R = luminance, G = roughness (box projected per material preset)
    def detail_setup(m, nt, i):
        p = presets.get(m.name)
        if not p:
            _emit(nt, (0.5, 0.5, 0.0))
            return
        d = _box_tex(nt, scan(p['scan'], 'diff'), p['tile'])
        r = _box_tex(nt, scan(p['scan'], 'rough'), p['tile'])
        bw = nt.nodes.new('ShaderNodeRGBToBW')
        nt.links.new(d.outputs['Color'], bw.inputs['Color'])
        comb = nt.nodes.new('ShaderNodeCombineColor')
        nt.links.new(bw.outputs['Val'], comb.inputs[0])
        nt.links.new(r.outputs['Color'], comb.inputs[1])
        _emit(nt, comb.outputs['Color'])
    tdet = new_image(name + '_det', size)
    det = _bake(ob, 'EMIT', tdet, detail_setup, samples=1)

    # 5. tangent-space normal: bevel-rounded edges perturbed by the scan normal
    def normal_setup(m, nt, i):
        bsdf = nt.nodes.get('Principled BSDF')
        p = presets.get(m.name)
        if not bsdf or not p:
            return
        n = _box_tex(nt, scan(p['scan'], 'nor'), p['tile'])
        nm = nt.nodes.new('ShaderNodeNormalMap')
        nm.inputs['Strength'].default_value = p.get('nor', 0.6)
        nt.links.new(n.outputs['Color'], nm.inputs['Color'])
        bv = nt.nodes.new('ShaderNodeBevel')
        bv.samples = 8
        bv.inputs['Radius'].default_value = normal_radius
        nt.links.new(nm.outputs['Normal'], bv.inputs['Normal'])
        nt.links.new(bv.outputs['Normal'], bsdf.inputs['Normal'])
    tnor = new_image(name + '_normal', size)
    _bake(ob, 'NORMAL', tnor, normal_setup, samples=8)

    # 6. optional albedo pass for presets without a design colour (imported, already textured models)
    alb = None
    if any(p.get('color') is None for p in presets.values()):
        def albedo_setup(m, nt, i):
            bsdf = nt.nodes.get('Principled BSDF')
            if not bsdf:
                _emit(nt, (0.5, 0.5, 0.5))
                return
            bc = bsdf.inputs['Base Color']
            src = bc.links[0].from_socket if bc.links else None
            _emit(nt, src if src is not None else tuple(bc.default_value[:3]))
        talb = new_image(name + '_alb', size)
        alb = _bake(ob, 'EMIT', talb, albedo_setup, samples=1)[..., :3]

    # 7. optional height pass for the dirt layer (object-space up / 4 in R)
    height = None
    if dirt:
        def height_setup(m, nt, i):
            geo = nt.nodes.new('ShaderNodeNewGeometry')
            sep = nt.nodes.new('ShaderNodeSeparateXYZ')
            nt.links.new(geo.outputs['Position'], sep.inputs['Vector'])
            mul = nt.nodes.new('ShaderNodeMath')
            mul.operation = 'MULTIPLY'
            mul.inputs[1].default_value = 0.25
            nt.links.new(sep.outputs['Z'], mul.inputs[0])
            comb = nt.nodes.new('ShaderNodeCombineColor')
            nt.links.new(mul.outputs['Value'], comb.inputs[0])
            _emit(nt, comb.outputs['Color'])
        th = new_image(name + '_h', size)
        height = _bake(ob, 'EMIT', th, height_setup, samples=1)[..., 0] * 4.0 + dirt.get('y0', 0.0)

    # composite ------------------------------------------------------------------------------
    h, w = mid.shape
    base = np.zeros((h, w, 3), np.float32)
    rough = np.full((h, w), 0.5, np.float32)
    metal = np.zeros((h, w), np.float32)
    lum, srough = det[..., 0], det[..., 1]
    grime = np.power(np.clip(1 - ao, 0, 1), 1.3)
    rng = np.random.default_rng(7)
    # low-frequency wear breakup in UV space (blurred noise; seams hidden by the scan detail)
    nz = rng.random((h // 16 + 1, w // 16 + 1)).astype(np.float32)
    nz = np.kron(nz, np.ones((16, 16), np.float32))[:h, :w]
    k = 9
    pad = np.pad(nz, k, mode='edge')
    cs = pad.cumsum(0).cumsum(1)
    nz = (cs[2 * k:, 2 * k:] - cs[:-2 * k, 2 * k:] - cs[2 * k:, :-2 * k] + cs[:-2 * k, :-2 * k]) / (2 * k) ** 2
    nz = (nz - nz.min()) / max(1e-6, nz.max() - nz.min())
    for mname, i in idx.items():
        sel = mid == i
        if not sel.any():
            continue
        p = presets.get(mname)
        if not p:
            bsdf = slots[i].node_tree.nodes.get('Principled BSDF')
            c = bsdf.inputs['Base Color'].default_value if bsdf else (0.5, 0.5, 0.5, 1)
            base[sel] = c[:3]
            continue
        l = lum[sel]
        lm = float(np.median(l)) or 0.5
        src = np.array(p['color'], np.float32)[None, :] if p.get('color') is not None else alb[sel]
        col = src * np.clip(1 + p['contrast'] * (l / lm - 1), 0.5, 1.6)[:, None]
        g = grime[sel]
        col *= (1 - 0.5 * g)[:, None]
        wmask = smoothstep(0.32, 0.75, edge[sel] * (0.45 + 1.1 * nz[sel])) * p['wear']
        if p.get('paint'):
            bare = np.array([0.36, 0.37, 0.38], np.float32)[None, :]  # bare steel under chipped paint
            col = col * (1 - wmask[:, None]) + bare * wmask[:, None]
            metal[sel] = p['metal'] * (1 - wmask) + 0.85 * wmask
        else:
            hi = np.clip(col * 1.9 + 0.035, 0, 1)                    # scuffed, lighter polymer / polished metal
            col = col * (1 - wmask[:, None]) + hi * wmask[:, None]
            metal[sel] = p['metal']
        base[sel] = col
        sr = srough[sel]
        srm = float(np.median(sr)) or 0.5
        r = p['rough'] * np.power(np.clip(sr / srm, 0.3, 2.5), 0.6) + 0.14 * g - 0.18 * wmask
        rough[sel] = np.clip(r, 0.12, 0.95)

    if dirt and height is not None:
        # thick near the ground, thinning out by `top`; patchy (low-frequency noise) and speckled
        fine = rng.random((h, w)).astype(np.float32)
        k2 = 2
        pad = np.pad(fine, k2, mode='edge')
        cs = pad.cumsum(0).cumsum(1)
        fine = (cs[2 * k2:, 2 * k2:] - cs[:-2 * k2, 2 * k2:] - cs[2 * k2:, :-2 * k2] + cs[:-2 * k2, :-2 * k2]) / (2 * k2) ** 2
        fine = (fine - fine.min()) / max(1e-6, fine.max() - fine.min())
        hm = 1.0 - smoothstep(0.15, dirt['top'], height)
        dm = np.clip(hm * (0.55 + 0.9 * nz) - 0.25 * fine, 0, 1) * dirt.get('amount', 0.8)
        dm = smoothstep(0.08, 0.7, dm) * dirt.get('amount', 0.8)
        dm += grime * 0.25 * hm          # dirt settles in the crevices first
        dm = np.clip(dm, 0, 1)
        for mname, i in idx.items():
            if presets.get(mname) is None:
                dm[mid == i] = 0.0
        mud = np.array(dirt['color'], np.float32)[None, None, :] * (0.8 + 0.4 * fine[..., None])
        base = base * (1 - dm[..., None]) + mud * dm[..., None]
        rough = rough * (1 - dm) + 0.88 * dm
        metal = metal * (1 - dm)

    out_base = new_image(name + '_base', size, float_buf=False)
    out_base.colorspace_settings.name = 'sRGB'
    px = np.ones((h, w, 4), np.float32)
    px[..., :3] = to_srgb(base)
    out_base.pixels[:] = px.ravel()
    out_mr = new_image(name + '_mr', size, float_buf=False)
    px = np.ones((h, w, 4), np.float32)
    px[..., 0] = np.clip(ao * 0.5 + 0.5, 0, 1)
    px[..., 1] = rough
    px[..., 2] = metal
    out_mr.pixels[:] = px.ravel()
    nor8 = new_image(name + '_nrm', size, float_buf=False)
    nor8.pixels[:] = tnor.pixels[:]
    for im in (out_base, out_mr, nor8):
        im.pack()

    # final material ---------------------------------------------------------------------------
    m = bpy.data.materials.new(name + '_Baked')
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes['Principled BSDF']
    tb = nt.nodes.new('ShaderNodeTexImage'); tb.image = out_base
    nt.links.new(tb.outputs['Color'], bsdf.inputs['Base Color'])
    tm = nt.nodes.new('ShaderNodeTexImage'); tm.image = out_mr
    sep = nt.nodes.new('ShaderNodeSeparateColor')
    nt.links.new(tm.outputs['Color'], sep.inputs['Color'])
    nt.links.new(sep.outputs['Green'], bsdf.inputs['Roughness'])
    nt.links.new(sep.outputs['Blue'], bsdf.inputs['Metallic'])
    tn = nt.nodes.new('ShaderNodeTexImage'); tn.image = nor8
    nm = nt.nodes.new('ShaderNodeNormalMap')
    nt.links.new(tn.outputs['Color'], nm.inputs['Color'])
    nt.links.new(nm.outputs['Normal'], bsdf.inputs['Normal'])
    # slot 0 becomes the baked material; kept (emissive) slots are remapped after it
    kept = [s for s in slots if s.name in keep]
    remap = {}
    new_slots = [m] + kept
    for i, s in enumerate(slots):
        remap[i] = 1 + kept.index(s) if s in kept else 0
    mi = np.zeros(len(me.polygons), np.int32)
    me.polygons.foreach_get('material_index', mi)
    mi = np.array([remap[int(v)] for v in mi], np.int32)
    me.materials.clear()
    for s in new_slots:
        me.materials.append(s)
    me.polygons.foreach_set('material_index', mi)
    me.update()
    if out_dir:
        for im, suffix in ((out_base, 'base'), (out_mr, 'mr'), (nor8, 'nrm')):
            im.filepath_raw = os.path.join(out_dir, f'{name}_{suffix}.png')
            im.file_format = 'PNG'
            im.save()
    return m
