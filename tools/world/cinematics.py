# SPDX-License-Identifier: Apache-2.0
"""Kestrel Valley story cinematics: camera rigs and VICTUS Sequencer timelines (docs/SEQUENCER.md
in the engine, docs/CAMPAIGN_AND_CINEMATICS.md section 4 here).

    python3 tools/world/chapters.py      (calls add_prologue for the prologue scene)

Each cutscene is one entity carrying a SequencePlayer and scripts/cinematic.luau; its children are
the world-space shot cameras plus "Handoff" (the director eases that one onto the first-person view
at the end). Shots inside or beside the moving Mule use cameras parented to "Mule Chassis", so they
ride the vehicle's sprung pitch and roll like a camera rigged to the car. The .vseq owns camera
moves, cuts and the timing of every line, lightning strike and drive cue; the mission director
(scripts/missions/kestrel.luau) reacts to the events.

Arrival (prologue opening, 02:40): Lamplight's tasking plays over the geography of the operation:
the valley under the storm, the Greyline fence line and its searchlights, the floodlit yard and the
portal into the mountain, then the squad in the Mule pulling out of the staging camp, and the cut
hands off to Rook in the rear middle seat.
"""
from __future__ import annotations
import json, math, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GAME = ROOT / 'game'
SEQ_DIR = GAME / 'assets' / 'seq'

import sys  # noqa: E402
sys.path.insert(0, str(ROOT / 'tools' / 'scenes'))
from vscene import quat_euler, transform, script, uid  # noqa: E402


def voice_durations():
    """Line id -> seconds, from the rendered voice data (scripts/lib/voice_data.luau)."""
    txt = (GAME / 'assets/scripts/lib/voice_data.luau').read_text()
    return {m.group(1): float(m.group(2)) for m in re.finditer(r'V\["([^"]+)"\] = \{.*?\bd = ([0-9.]+)', txt)}


def look(src, dst):
    dx, dy, dz = (dst[0] - src[0], dst[1] - src[1], dst[2] - src[2])
    yaw = math.degrees(math.atan2(-dx, -dz))
    pitch = math.degrees(math.atan2(dy, math.hypot(dx, dz)))
    return quat_euler(pitch, yaw, 0)


def r3(v):
    return [round(float(x), 3) for x in v]


class Timeline:
    def __init__(self):
        self.tracks = {}
        self.cuts = []
        self.events = []

    def shot(self, cam, t0, t1, p0, a0, p1=None, a1=None, interp='smooth'):
        """Camera `cam` from (p0 looking at a0) at t0 to (p1 looking at a1) at t1, cut to at t0."""
        p1 = p1 or p0
        a1 = a1 or a0
        tr = self.tracks.setdefault(cam, {'type': 'transform', 'name': cam, 'target': cam,
                                          'position': [], 'rotation': []})
        tr['position'] += [{'t': round(t0, 3), 'v': r3(p0), 'interp': interp}, {'t': round(t1, 3), 'v': r3(p1)}]
        tr['rotation'] += [{'t': round(t0, 3), 'v': look(p0, a0), 'interp': interp}, {'t': round(t1, 3), 'v': look(p1, a1)}]
        self.cuts.append({'t': round(t0, 3), 'camera': cam})

    def cut(self, cam, t):
        self.cuts.append({'t': round(t, 3), 'camera': cam})

    def event(self, t, name, payload=''):
        self.events.append({'t': round(t, 3), 'name': name, 'payload': payload})

    def doc(self, duration):
        tracks = list(self.tracks.values())
        tracks.append({'type': 'camera', 'name': 'Cuts', 'keys': sorted(self.cuts, key=lambda k: k['t'])})
        tracks.append({'type': 'event', 'name': 'Story', 'keys': sorted(self.events, key=lambda k: k['t'])})
        return {'version': 1, 'duration': round(duration, 3), 'tracks': tracks}


def camera(fov, far=1500.0):
    return {'projection': 'perspective', 'fov_y': fov, 'ortho_height': 10, 'near': 0.04, 'far': far,
            'primary': False}


def lines(tl, t, ids, D, gap=0.4):
    """Key `line` events back to back from t; returns {id: (start, end)} and the end time."""
    at = {}
    for i in ids:
        tl.event(t, 'line', i)
        at[i] = (t, t + D[i])
        t += D[i] + gap
    return at, t


def add_prologue(doc, P, ground):
    """Adds the Arrival cutscene to a prologue scene document (entities appended in place)."""
    D = voice_durations()
    ents = doc['entities']
    chassis = next(e for e in ents if e['name'] == 'Mule Chassis')
    tl = Timeline()

    at, t_end = lines(tl, 1.2, ['pro_01', 'pro_02', 'pro_02b', 'pro_03', 'pro_04', 'pro_05', 'pro_06', 'pro_07'], D)

    def g(x, z, up):
        return (x, ground(x, z) + up, z)

    # A  the valley under the storm, from above the staging camp, looking north up the valley
    s, e = at['pro_01']
    tl.shot('Cam Valley', 0.0, at['pro_02'][0], g(-34, 548, 64), g(-10, 250, 6), g(-30, 520, 58), g(-6, 230, 4))
    tl.event(0.0, 'fade', '0')
    tl.event(1.6, 'title', 'KESTREL VALLEY')
    tl.event(1.6, 'subtitle_title', 'Northline border  -  02:40')
    tl.event(3.4, 'strike', '1.6')
    tl.event(7.4, 'title', '')
    tl.event(7.4, 'subtitle_title', '')
    # B  the Greyline fence line: a watchtower searchlight sweeping the strip in the rain
    tw = P['tower_0']
    s, e = at['pro_02']
    tl.shot('Cam Fence', s - 0.4, at['pro_02b'][0], (tw[0] + 30, tw[1] - 2.0, tw[2] + 34), (tw[0], tw[1] + 1.5, tw[2]),
            (tw[0] + 24, tw[1] - 2.5, tw[2] + 30), (tw[0] - 2, tw[1] + 1.0, tw[2]))
    # C  the compound yard under sodium lights: contractors on patrol, trucks, containers
    s, e = at['pro_02b']
    yd = P['poi_compound']
    tl.shot('Cam Yard', s - 0.4, at['pro_03'][0], (yd[0] + 52, yd[1] + 14, yd[2] + 40), (yd[0] - 6, yd[1] + 1, yd[2] - 6),
            (yd[0] + 40, yd[1] + 11, yd[2] + 34), (yd[0] - 10, yd[1] + 1, yd[2] - 12))
    tl.event(s + 4.0, 'strike', '3.5')
    # D  the portal into the mountain: Kestrel Station, closed six years ago
    s, e = at['pro_03']
    ff = P['facility_front']
    tl.shot('Cam Portal', s - 0.4, at['pro_04'][0], (ff[0] + 6, ff[1] + 2.2, ff[2] + 26), (ff[0], ff[1] + 3.0, ff[2] - 6),
            (ff[0] + 3, ff[1] + 1.9, ff[2] + 15), (ff[0], ff[1] + 3.0, ff[2] - 6))
    tl.event(s + 6.5, 'drive', '')       # the Mule pulls out of the camp, off screen
    # E  inside the Mule: Tally (rear right) and the name Kestrel
    s, e = at['pro_04']
    # Tally sits taller than Echo: the Echo framing (aim 1.6) cut his head off at the top of frame
    tl.shot('Cam Tally', s - 0.4, e + 0.2, (0.04, 1.58, -0.2), (0.5, 1.74, 0.62), (0.06, 1.59, -0.14), (0.5, 1.74, 0.62))
    # F  Echo (rear left), deadpan
    s, e = at['pro_05']
    tl.shot('Cam Echo', s - 0.2, e + 0.2, (-0.06, 1.52, -0.12), (-0.5, 1.6, 0.62), (-0.08, 1.53, -0.06), (-0.5, 1.6, 0.62))
    # G  the Mule's headlights on the forestry road (roadside low angle, then a chase)
    s, e = at['pro_06']
    tl.shot('Cam Chase', s - 0.2, s + 5.2, (2.6, 1.1, -6.0), (0.0, 1.0, 1.0), (3.4, 1.0, -5.0), (0.0, 1.1, 1.5))
    tl.shot('Cam Rear', s + 5.2, e + 0.3, (-1.9, 2.5, 7.5), (0.0, 1.2, -6.0), (-1.6, 2.3, 6.6), (0.0, 1.1, -6.0))
    # H  Anchor at the wheel, the road through the windscreen
    s, e = at['pro_07']
    tl.shot('Cam Anchor', s - 0.2, e + 0.1, (0.34, 1.56, -0.64), (-0.46, 1.62, -0.4), (0.3, 1.55, -0.6), (-0.46, 1.6, -0.42))
    # hand-off: ease onto Rook's eyes in the rear middle seat
    t_hand = e + 0.1
    tl.cut('Handoff', t_hand)
    duration = t_hand + 1.6

    seq = tl.doc(duration)
    SEQ_DIR.mkdir(parents=True, exist_ok=True)
    (SEQ_DIR / 'prologue_arrival.vseq').write_text(json.dumps(seq, indent=1) + '\n')

    root_id = uid('cine/arrival')
    ents.append({'uuid': root_id, 'name': 'Arrival Cinematic', 'components': {
        'Transform': transform(),
        'SequencePlayer': {'sequence': 'seq/prologue_arrival.vseq', 'play_on_start': False, 'loop': False,
                           'speed': 1.0, 'enabled': True},
        # establishing shots see 150-400 m: gameplay fog (0.018/m) would leave only grey there
        'Script': script('scripts/cinematic.luau', id='arrival', handoff=1.4, grace=1.0,
                         fog_shots='Cam Valley=0.0045,Cam Fence=0.007,Cam Yard=0.006,Cam Portal=0.008')}})
    world_cams = {'Cam Valley': 52.0, 'Cam Fence': 42.0, 'Cam Yard': 44.0, 'Cam Portal': 40.0, 'Handoff': 60.0}
    for name, fov in world_cams.items():
        ents.append({'uuid': uid(f'cine/arrival/{name}'), 'name': name, 'parent': root_id,
                     'components': {'Transform': transform(), 'Camera': camera(fov)}})
    for name, fov in {'Cam Tally': 50.0, 'Cam Echo': 50.0, 'Cam Chase': 46.0, 'Cam Rear': 50.0, 'Cam Anchor': 52.0}.items():
        ents.append({'uuid': uid(f'cine/arrival/{name}'), 'name': name, 'parent': chassis['uuid'],
                     'components': {'Transform': transform(), 'Camera': camera(fov)}})
    return duration
