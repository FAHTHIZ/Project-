# SPDX-License-Identifier: Apache-2.0
"""Storm-night weathering for the shipped human cast (texture-only, in place).

    python3 tools/assets/cast_weather.py            # every sops_*.glb not yet weathered
    python3 tools/assets/cast_weather.py --force    # re-apply on top (do not, it compounds)

The campaign is one rain storm (docs/CAMPAIGN_STORY_BIBLE.md 1A) and every human in it has been
out in it for hours, but the Rocketbox-derived atlases (tools/assets/build_rocketbox_cast.py)
are showroom-clean: digital camo at catalogue contrast, white parade gloves, dry cloth. This pass
edits only the body material's colour and metallic-roughness images; the mesh, UVs, skeleton,
skin, face morphs, clips and the asset UUIDs (.meta) are untouched, so nothing that scripts,
IK or cutscenes rely on can move.

Per texel it uses the bind-pose surface that maps there (height above the soles and normal,
rasterised from the body primitive's triangles into UV space):

- camo:   Halyard uniforms only (characters with a CAST dye): the pattern's luminance contrast
          is cut to 45 % around a local mean and the cloth loses 15 % chroma. Real printed camo
          on worn, wet nylon-cotton reads much flatter than a scanned new uniform; the folds
          stay because they live in the normal map.
- gloves: near-white low-saturation texels on the hands are re-dyed coyote leather.
- damp:   all cloth is rain-darkened (rain falls from above: tops of shoulders, helmet, pack
          and thighs darkest) and loses roughness; soaked below the knee.
- mud:    splash and ground mud from the soles up to the shins, plus kneeling patches on the
          front of the knees, broken up with a fixed-seed fBm so no two characters match.

Skin (warm, saturated) and the face/head material are left alone: wet skin is a shader matter.
A marker in the GLB's asset.extras (sops_weather) keeps the pass from being applied twice.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'characters'))
from gltf_util import read_glb, accessor  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
CHARS = os.path.join(ROOT, 'game', 'assets', 'models', 'characters')
VERSION = 1
# Halyard Team (dyed camo); everyone else gets damp and mud only
CAMO = {'sops_anchor', 'sops_brick', 'sops_tally', 'sops_patch', 'sops_echo', 'sops_explorer'}
# how long each has been out in it: Hollis lives here and Greyline stand watch under cover
EXPOSURE = {'sops_ranger': 0.7, 'sops_greyline_a': 0.6, 'sops_greyline_b': 0.6, 'sops_explorer': 0.8}
COYOTE = np.array([0.42, 0.35, 0.26], np.float32)
MUD = np.array([0.24, 0.19, 0.14], np.float32)


def blur(a, r):
    from scipy.ndimage import gaussian_filter
    a = np.asarray(a, np.float32)
    return gaussian_filter(a, (r, r) + (0,) * (a.ndim - 2), mode='wrap')


def fbm(hw, seed, octaves=5, base=6):
    rng = np.random.default_rng(seed)
    out = np.zeros(hw, np.float32); amp = 1.0; tot = 0.0
    for o in range(octaves):
        k = base * 2 ** o
        g = rng.random((k, k)).astype(np.float32)
        out += amp * np.asarray(Image.fromarray(g, 'F').resize((hw[1], hw[0]), Image.BICUBIC), np.float32)
        tot += amp; amp *= 0.55
    out /= tot
    return (out - out.min()) / max(np.ptp(out), 1e-6)


def surface_maps(j, binc, prim, hw):
    """Rasterise bind-pose height (0..1 of the body), normal.y, normal.z and |x| (m, distance from
    the body's centre plane; the rest pose is an A-pose, so the hands are the widest part) of the
    primitive into an n x n UV map. Returns (h, ny, nz, ax, height_m)."""
    a = prim['attributes']
    P = accessor(j, binc, a['POSITION']); N = accessor(j, binc, a['NORMAL'])
    UV = accessor(j, binc, a['TEXCOORD_0']); I = accessor(j, binc, prim['indices']).reshape(-1, 3)
    y0 = float(P[:, 1].min()); y1 = float(P[:, 1].max())
    hv = (P[:, 1] - y0) / max(y1 - y0, 1e-3)
    chans = []
    for vals in (hv, N[:, 1] * 0.5 + 0.5, N[:, 2] * 0.5 + 0.5, np.abs(P[:, 0])):
        im = Image.new('F', (hw[1], hw[0]), -1.0); d = ImageDraw.Draw(im)
        tv = vals[I].mean(1)
        for t, v in zip(UV[I], tv):
            d.polygon([(float(u * hw[1]), float(w * hw[0])) for u, w in t], fill=float(v))
        chans.append(np.asarray(im, np.float32))
    cover = (chans[0] >= 0).astype(np.float32)
    surface_maps.cover = cover
    # bleed values into the gutters so mip/bilinear sampling at seams sees sensible data
    out = []
    for c in chans:
        c = np.where(cover > 0, c, 0)
        num = blur(c * cover, 6); den = blur(cover, 6)
        filled = np.where(cover > 0, c, num / np.maximum(den, 1e-4))
        out.append(blur(filled, 1.5))
    return out[0], out[1] * 2 - 1, out[2] * 2 - 1, out[3], (y1 - y0)


def smooth(x, a, b):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def to_hsv(rgb):
    hsv = np.asarray(Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8)).convert('HSV'), np.float32) / 255
    return hsv[..., 0], hsv[..., 1], hsv[..., 2]


def weather(stem, rgb, mr, h, ny, nz, ax, height_m):
    n = rgb.shape[:2]
    seed = int(hashlib.sha1(stem.encode()).hexdigest()[:8], 16)
    lin = np.clip(rgb, 0, 1) ** 2.2
    hue, sat, val = to_hsv(rgb)
    lum = lin @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    hy = h * height_m                      # metres above the soles in bind pose
    # warm saturated texels are skin, except below the knees where they are tan boots
    skin = (hue < 0.11) & (sat > 0.25) & (val > 0.25) & (hy > 0.6)
    skin = blur(skin.astype(np.float32), 2) > 0.3
    cloth = (~skin).astype(np.float32)
    if stem in CAMO:
        # flatten the printed pattern around a 12-texel local mean (texel ~1.5 mm on a 2048 atlas)
        mean = blur(lin, 12)
        lm = np.maximum(mean @ np.array([0.2126, 0.7152, 0.0722], np.float32), 1e-4)
        ratio = (lum / lm)[..., None]
        flat = mean * ratio ** 0.45
        g = flat.mean(-1, keepdims=True)
        flat = g + (flat - g) * 0.85
        camo = cloth * (sat < 0.5) * (val > 0.06) * (val < 0.85)
        lin = lin * (1 - camo[..., None]) + flat * camo[..., None]
    # gloves: white leather on the hands -> coyote, keeping the leather's own shading
    hands = smooth(ax, 0.40, 0.45)        # past the wrists in the A-pose
    white = (sat < 0.16) & (val > 0.62)
    gm = blur((white * (hands > 0.3)).astype(np.float32), 1.2)
    rel = (lum / max(float(np.median(lum[white])) if white.any() else 0.7, 1e-3))[..., None]
    lin = lin * (1 - gm[..., None]) + np.clip(COYOTE ** 2.2 * rel, 0, 1) * gm[..., None]
    ex = EXPOSURE.get(stem, 1.0)
    noise = fbm(n, seed)
    fine = fbm(n, seed + 1, octaves=4, base=48)
    # damp: rain from above, soaked below the knee, streaks broken up by noise
    up = np.clip(ny, 0, 1)
    damp = ex * np.clip(0.28 + 0.42 * up ** 1.5 + 0.45 * (1 - smooth(hy, 0.25, 0.55)) + 0.25 * (noise - 0.5), 0, 1)
    damp *= cloth
    lin = lin * (1 - 0.38 * damp[..., None])
    rough = mr[..., 1]
    rough = rough * (1 - 0.38 * damp)
    # mud: splash band from the soles up the shins, and kneeling patches on the front of the knees
    splash = (1 - smooth(hy, 0.10, 0.48)) * smooth(noise * 0.7 + fine * 0.3, 0.24 - 0.3 * (1 - smooth(hy, 0.0, 0.2)), 0.58)
    knee = np.exp(-((hy - 0.5) / 0.07) ** 2) * smooth(nz, 0.35, 0.8) * smooth(noise, 0.35, 0.65)
    mud = np.clip(ex * (splash + 0.8 * knee), 0, 1) * cloth
    mud = mud * (0.75 + 0.25 * fine)
    mud_col = MUD ** 2.2 * (0.8 + 0.4 * fine[..., None])
    lin = lin * (1 - mud[..., None]) + mud_col * mud[..., None]
    # drying mud is rougher, fresh splashes are wet
    rough = rough * (1 - mud) + (0.55 + 0.3 * smooth(hy, 0.0, 0.3)) * mud
    out = np.clip(lin, 0, 1) ** (1 / 2.2)
    mr2 = mr.copy(); mr2[..., 1] = np.clip(rough, 0.04, 1)
    cv = getattr(surface_maps, 'cover', np.ones_like(damp)) > 0
    return out, mr2, dict(damp=float(damp[cv].mean()), mud=float(mud[cv].mean()), gloves=float(gm[cv].mean()))


def jpeg(arr):
    b = io.BytesIO()
    Image.fromarray((np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8), 'RGB').save(b, 'JPEG', quality=92, subsampling=0)
    return b.getvalue()


def load(binc, j, img):
    bv = j['bufferViews'][j['images'][img]['bufferView']]
    o = bv.get('byteOffset', 0)
    return np.asarray(Image.open(io.BytesIO(bytes(binc[o:o + bv['byteLength']]))).convert('RGB'), np.float32) / 255


def rewrite(path, j, binc, replace):
    """Rebuild the binary chunk with some images' bytes replaced; every other view keeps its bytes."""
    import json
    import struct
    img_view = {j['images'][i]['bufferView']: data for i, data in replace.items()}
    for i in replace:
        j['images'][i]['mimeType'] = 'image/jpeg'
    out = bytearray()
    for vi, bv in enumerate(j['bufferViews']):
        o = bv.get('byteOffset', 0)
        data = img_view.get(vi, bytes(binc[o:o + bv['byteLength']]))
        while len(out) % 4:
            out.append(0)
        bv['byteOffset'] = len(out); bv['byteLength'] = len(data)
        out += data
    while len(out) % 4:
        out.append(0)
    j['buffers'] = [{'byteLength': len(out)}]
    js = json.dumps(j, separators=(',', ':')).encode()
    while len(js) % 4:
        js += b' '
    blob = struct.pack('<III', 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(out))
    blob += struct.pack('<II', len(js), 0x4E4F534A) + js + struct.pack('<II', len(out), 0x004E4942) + bytes(out)
    open(path, 'wb').write(blob)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('names', nargs='*')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--dir', default=CHARS, help='folder of sops_*.glb (default: the game cast)')
    ap.add_argument('--preview', help='write before/after atlases to this folder instead of the GLBs')
    a = ap.parse_args(argv)
    names = a.names or sorted(f[:-4] for f in os.listdir(a.dir) if f.startswith('sops_') and f.endswith('.glb'))
    for stem in names:
        path = os.path.join(a.dir, stem + '.glb')
        j, binc = read_glb(path)
        extras = j['asset'].setdefault('extras', {})
        if extras.get('sops_weather') and not a.force:
            print(stem, 'already weathered (v%s)' % extras['sops_weather']); continue
        mi = next(i for i, m in enumerate(j['materials']) if m['name'].endswith('_Body'))
        mat = j['materials'][mi]['pbrMetallicRoughness']
        prim = next(p for m in j['meshes'] for p in m['primitives'] if p.get('material') == mi)
        ci = j['textures'][mat['baseColorTexture']['index']]['source']
        ri = j['textures'][mat['metallicRoughnessTexture']['index']]['source']
        rgb = load(binc, j, ci); mr = load(binc, j, ri)
        n = rgb.shape[:2]
        h, ny, nz, ax, hm = surface_maps(j, binc, prim, n)
        mr0 = mr.shape[:2]
        if mr0 != n:
            mr = np.asarray(Image.fromarray((mr * 255).astype(np.uint8)).resize((n[1], n[0]), Image.LANCZOS), np.float32) / 255
        out, mr2, st = weather(stem, rgb, mr, h, ny, nz, ax, hm)
        print(stem, f'{n[1]}x{n[0]}', ' '.join(f'{k} {v:.3f}' for k, v in st.items()))
        if a.preview:
            os.makedirs(a.preview, exist_ok=True)
            Image.fromarray((np.hstack([rgb, out]) * 255).astype(np.uint8)).save(os.path.join(a.preview, stem + '.jpg'), quality=88)
            continue
        if mr2.shape[:2] != mr0:
            mr2 = np.asarray(Image.fromarray((mr2 * 255).astype(np.uint8)).resize((mr0[1], mr0[0]), Image.LANCZOS), np.float32) / 255
        extras['sops_weather'] = VERSION
        rewrite(path, j, binc, {ci: jpeg(out), ri: jpeg(mr2)})


if __name__ == '__main__':
    main(sys.argv[1:])
