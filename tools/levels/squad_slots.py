"""Collision-aware start slots for the squad in the interior chapters.

The facility builder used to put the operators on a fixed line 2.2-3.0 m behind the player, 1.3 m
apart. In the 6 m entry tunnels that put the outer operators inside the side walls and the back
rank inside the end wall (Op04: Patch spawned in "Shell Col 67" and fell through the floor).

`place(entities, player_pos, names)` moves each named root entity to the clear slot nearest its
original one: no overlap with any solid box collider (with the capsule radius plus a margin),
floor under it, a clear straight line from the player at chest height, and 0.95 m from the player
and the other operators. Works on plain entity dicts, so it serves both the builder
(`Scene.entities`) and `patch_squad_slots.py` (already-built .vscene files).
"""
import math

RADIUS = 0.3 + 0.12          # CharacterController radius + margin
HEIGHT = 1.76
SPACING = 0.95


def _qmul(a, b):
    x1, y1, z1, w1 = a
    x2, y2, z2, w2 = b
    return (w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2, w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
            w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2, w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2)


def _rot(q, v):
    x, y, z, w = q
    r = _qmul(_qmul(q, (v[0], v[1], v[2], 0.0)), (-x, -y, -z, w))
    return r[0], r[1], r[2]


def _world(e, byid):
    chain = []
    while e:
        chain.append(e)
        e = byid.get(e.get('parent'))
    p, q = (0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0)
    for c in reversed(chain):
        t = c.get('components', {}).get('Transform', {})
        lp = t.get('position', [0, 0, 0])
        lr = t.get('rotation', [0, 0, 0, 1])
        sc = t.get('scale', [1, 1, 1])
        rp = _rot(q, (lp[0], lp[1], lp[2]))
        p = (p[0] + rp[0], p[1] + rp[1], p[2] + rp[2])
        q = _qmul(q, tuple(lr))
    return p, q, sc


def boxes(entities):
    byid = {e['uuid']: e for e in entities}
    out = []
    for e in entities:
        c = e.get('components', {}).get('Collider')
        if not c or c.get('shape') != 'box' or c.get('is_trigger'):
            continue
        p, q, sc = _world(e, byid)
        size = c.get('size', [1, 1, 1])
        off = c.get('offset', [0, 0, 0])
        out.append((p, q, [size[i] * abs(sc[i]) for i in range(3)], off, e.get('name', '')))
    return out


def _local(b, pt):
    p, q, size, off, _ = b
    inv = (-q[0], -q[1], -q[2], q[3])
    l = _rot(inv, (pt[0] - p[0], pt[1] - p[1], pt[2] - p[2]))
    return l[0] - off[0], l[1] - off[1], l[2] - off[2], size


def capsule_hits(bx, pos):
    """Names of solid boxes the standing capsule at `pos` (feet) overlaps, floor excluded."""
    hits = []
    lo, hi = pos[1] + 0.12, pos[1] + HEIGHT
    cy, hy = (lo + hi) / 2, (hi - lo) / 2
    for b in bx:
        x, y, z, s = _local(b, (pos[0], cy, pos[2]))
        if abs(x) < s[0] / 2 + RADIUS and abs(y) < s[1] / 2 + hy and abs(z) < s[2] / 2 + RADIUS:
            hits.append(b[4])
    return hits


def _inside(bx, pt):
    for b in bx:
        x, y, z, s = _local(b, pt)
        if abs(x) <= s[0] / 2 and abs(y) <= s[1] / 2 and abs(z) <= s[2] / 2:
            return True
    return False


def _clear(bx, pos, player, taken):
    if capsule_hits(bx, pos):
        return False
    if not _inside(bx, (pos[0], pos[1] - 0.08, pos[2])):  # floor under the feet
        return False
    for o in [player] + taken:
        if math.hypot(pos[0] - o[0], pos[2] - o[2]) < SPACING:
            return False
    for i in range(1, 12):  # line of sight from the player at chest height
        t = i / 12
        if _inside(bx, (player[0] + (pos[0] - player[0]) * t, player[1] + 1.2, player[2] + (pos[2] - player[2]) * t)):
            return False
    return True


def place(entities, player, names):
    """Moves each root entity in `names` to its nearest clear slot. Returns [(name, old, new)]."""
    bx = boxes(entities)
    roots = {e['name']: e for e in entities if e.get('parent') is None and e.get('name') in names}
    taken, moved = [], []
    for n in names:
        e = roots.get(n)
        if not e:
            continue
        t = e['components']['Transform']
        want = tuple(t['position'])
        best = None
        if _clear(bx, want, player, taken):
            best = want
        else:
            cands = []
            for iz in range(-8, 13):
                for ix in range(-8, 9):
                    c = (player[0] + ix * 0.35, want[1], player[2] + iz * 0.35)
                    d = math.hypot(c[0] - want[0], c[2] - want[2])
                    # prefer behind the player (+z of the start), never further than 4.5 m away
                    if math.hypot(c[0] - player[0], c[2] - player[2]) <= 4.5:
                        cands.append((d + (0.6 if c[2] < player[2] else 0.0), c))
            for _, c in sorted(cands):
                if _clear(bx, c, player, taken):
                    best = c
                    break
        if best is None:
            raise SystemExit(f'squad_slots: no clear start slot for {n} near {want}')
        taken.append(best)
        if best != want:
            t['position'] = [round(best[0], 3), best[1], round(best[2], 3)]
            moved.append((n, want, tuple(t['position'])))
    return moved
