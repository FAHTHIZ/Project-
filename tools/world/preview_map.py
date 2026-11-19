# SPDX-License-Identifier: Apache-2.0
"""Top-down design map of Kestrel Valley (hillshade, splat colours, routes, POIs) for review."""
import sys
import numpy as np
from PIL import Image, ImageDraw
import terrain_gen as T
import worldmap as M


def render(H, W, cover, out, scale=2):
    n = H.shape[0]
    gz, gx = np.gradient(H, T.CELL)
    nrm = np.dstack([-gx, np.ones_like(H), -gz]); nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
    L = np.array([-0.5, 0.75, -0.45]); L /= np.linalg.norm(L)
    shade = np.clip(nrm @ L, 0, 1) * 0.75 + 0.25
    cols = np.array([[62, 52, 34], [128, 124, 116], [140, 112, 80], [104, 128, 56]], float)
    c = W @ cols
    c = c * (1 - cover[..., None] * 0.55) + np.array([34, 56, 30]) * cover[..., None] * 0.55
    c *= shade[..., None]
    # contour lines every 10 m
    cl = (np.floor(H / 10) != np.floor(np.roll(H, 1, 0) / 10)) | (np.floor(H / 10) != np.floor(np.roll(H, 1, 1) / 10))
    c[cl] *= 0.7
    img = Image.fromarray(np.clip(c, 0, 255).astype(np.uint8)).resize((n * scale, n * scale), Image.BILINEAR)
    d = ImageDraw.Draw(img)

    def px(x, z):
        return ((x + M.SIZE / 2) / T.CELL * scale, (z + M.SIZE / 2) / T.CELL * scale)
    for poly, col, w in [(M.CREEK, (70, 130, 200), 3), (M.ROAD_IN, (230, 210, 160), 3),
                         (M.ROAD_SERVICE, (230, 210, 160), 3), (M.TRAIL, (250, 120, 60), 2), (M.FENCE, (220, 40, 40), 2)]:
        p = T.catmull(poly, 4)
        d.line([px(x, z) for x, z in p], fill=col, width=w)
    for name, p in M.POIS.items():
        x, y = px(p['x'], p['z'])
        d.ellipse([x - 6, y - 6, x + 6, y + 6], outline=(255, 255, 255), width=2)
        d.text((x + 9, y - 6), name, fill=(255, 255, 255))
    img.save(out)


if __name__ == '__main__':
    H, masks = T.generate()
    cover = T.forest_cover(H, masks)
    W = T.splat(H, masks, cover)
    render(H, W, cover, sys.argv[1] if len(sys.argv) > 1 else '/tmp/map.png')
    print('height range', H.min(), H.max())
