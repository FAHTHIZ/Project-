-- SPECIAL OPS cinematic director (docs/CAMPAIGN_AND_CINEMATICS.md sections 4 and 7).
--
-- One entity per cutscene carries a SequencePlayer (the VICTUS Sequencer, docs/SEQUENCER.md) and
-- this script; its children are the shot cameras. The .vseq timeline owns camera positions, cuts,
-- animation clips, audio one-shots and event keys. This script owns what a timeline cannot:
--
--   * input and camera ownership (Game.cinematic), letterbox and fades (Game.present);
--   * dialogue: event key `line` with payload = line id queues a priority-3 line (subtitles,
--     lip sync and listener eye-lines come from lib/dialogue);
--   * operated cameras: `aim` maps a camera name to a target entity name, and that camera's
--     rotation follows the target with a damped pan, like a camera operator; `focus_y` offsets
--     the aim point (head height);
--   * skip after a grace period (hold the skip action 0.5 s): the mission's on_skip applies the
--     scene's end state (no flag, item or checkpoint is ever skipped), then control returns;
--   * pause: the timeline pauses with the pause menu, so camera, audio and dialogue stay in step;
--   * hand-off: the timeline's last camera cut goes to the child camera "Handoff" (it has no
--     transform track, because the Sequencer writes tracked transforms after scripts every frame).
--     The script starts it at the previous shot's pose and eases it onto the first-person
--     camera's exact pose and FOV, then the gameplay camera takes over with no visible cut.
--   * per-shot atmosphere: `fog_shots` ("Cam Valley=0.004,Cam Yard=0.008") sets the scene
--     Environment's fog density while that camera is live (cut = snap), so establishing shots can
--     show the landmarks that gameplay fog hides at that distance; the scene's own density
--     returns with the hand-off. Keyed by camera, not by event, so a seek shows the same frame.
--   * world streaming: a shot camera that carries a VICTUS StreamingSource (authored disabled)
--     is enabled for the length of the cutscene, so the world cells it looks at (a watchtower or
--     the facility 400 m from the player) are loaded before the cut, and disabled on finish, so
--     gameplay streams around the player alone again.
--
-- Scripts:  Game.cinematics[id]:play({ on_event = fn(name, payload), on_skip = fn(), done = fn() })
--           Game.cinematics[id]:playing()
local Game = require("scripts/lib/game")
local Controls = require("scripts/lib/controls")
local Dialogue = require("scripts/lib/dialogue")

local C = {}
C.id = ""
C.sequence = ""
C.handoff = 1.2       -- seconds at the end spent easing onto the first-person view (0 = cut)
C.grace = 1.0         -- skip becomes available after this
C.skip_hold = 0.5
C.letterbox = true
C.fog_shots = ""

Game.cinematics = Game.cinematics or {}
-- shared with hud.luau, which may start after this script
Game.present = Game.present or { letterbox = 0, fade = 0, title = nil, subtitle_title = nil, skip_hint = false }

local function smooth(t) t = math.clamp(t, 0, 1); return t * t * (3 - 2 * t) end
local function wrap(a) return (a + 540) % 360 - 180 end

function C:start()
    if self.id == "" then self.id = self.entity.name end
    Game.cinematics[self.id] = self
    self.cams = {}
    for _, ch in self.entity:children() do
        if ch:has("Camera") then self.cams[ch.name] = ch end
    end
    self.streamers = {}
    for _, cam in self.cams do
        if cam:has("StreamingSource") then table.insert(self.streamers, cam) end
    end
    self.active = false
    self.aim = {}
    self.view = {}
    self.fog = {}
    for name, v in string.gmatch(self.fog_shots, "([^=,]+)=([%d%.]+)") do self.fog[name] = tonumber(v) end
end

-- Sets the Environment fog density for the live shot (nil = the scene's own value).
function C:shot_fog(cam_name)
    local e = scene.find("Environment")
    if not e then return end
    local env = e:get("Environment")
    if not env then return end
    if self.base_fog == nil then self.base_fog, self.base_vol = env.fog_density, env.volumetric_density or 0 end
    local want = (cam_name and self.fog[cam_name]) or self.base_fog
    if math.abs((env.fog_density or 0) - want) > 1e-6 then
        env.fog_density = want
        -- the froxel volume thins in proportion (it carries the rain haze near the lens)
        if self.base_fog > 0 then env.volumetric_density = self.base_vol * math.min(1, want / self.base_fog) end
        e:set("Environment", env)
    end
end

function C:playing() return self.active end

-- Starts the cutscene. opts: on_event(name, payload), on_skip(), done(skipped), aim = {cam = target}
function C:play(opts)
    opts = opts or {}
    self.opts = opts
    self.aim = opts.aim or {}
    self.focus_y = opts.focus_y or 1.55
    self.view = {}
    self.t = 0
    self.held = 0
    self.skipped = false
    self.finishing = false
    self.fade_out = nil
    self.handoff_t = nil
    self.last_cam = nil
    self.blend_from = nil
    self.entity:play_sequence(self.sequence ~= "" and self.sequence or nil)
    local st = self.entity:sequence_state()
    self.duration = st and st.duration or 0
    self.active = true
    self:stream(true)
    Game.cinematic = true
    Game.cinematic_id = self.id
    Game.present.skip_hint = false
    if Game.player_state then Game.player_state.vel = vector.create(0, 0, 0) end
    Game.emit("cinematic_started", self.id)
    return st ~= nil and st.valid
end

function C:camera_entity()
    local st = self.entity:sequence_state()
    if not st or st.camera == "" then return nil end
    local name = string.match(st.camera, "([^/]+)$") or st.camera
    return self.cams[name] or scene.find(name)
end

function C:on_sequence_event(name, payload)
    if not self.active then return end
    -- the Sequencer may deliver a key to the target's script and the player's script; when both
    -- are this entity, take it once
    local key = name .. "|" .. tostring(payload)
    if self.last_event == key and self.last_event_t == self.t then return end
    self.last_event, self.last_event_t = key, self.t
    if name == "line" then
        Dialogue.say(payload, { priority = 3, interrupt = true })
    elseif name == "fade" then
        self.fade_to = tonumber(payload) or 1
    elseif name == "title" then
        Game.present.title = payload ~= "" and payload or nil
    elseif name == "subtitle_title" then
        Game.present.subtitle_title = payload ~= "" and payload or nil
    end
    if self.opts.on_event then self.opts.on_event(name, payload) end
    Game.emit("cinematic_event", self.id, name, payload)
end

-- Aim operated cameras at their targets (damped pan and tilt).
function C:operate(dt)
    for cam_name, target_name in self.aim do
        local cam = self.cams[cam_name]
        local tgt = scene.find(target_name)
        if cam and tgt and tgt.valid then
            local d = tgt.world_position + vector.create(0, self.focus_y, 0) - cam.world_position
            local yaw = math.deg(math.atan2(-d.x, -d.z))
            local pitch = math.deg(math.atan2(d.y, math.sqrt(d.x * d.x + d.z * d.z)))
            local v = self.view[cam_name]
            if not v then v = { yaw = yaw, pitch = pitch }; self.view[cam_name] = v end
            local k = 1 - math.exp(-4.0 * dt)
            v.yaw = v.yaw + wrap(yaw - v.yaw) * k
            v.pitch = v.pitch + (pitch - v.pitch) * k
            cam.rotation = vector.create(v.pitch, v.yaw, 0)
        end
    end
end

-- Hand-off: ease the Handoff camera from the previous shot's pose onto the first-person pose.
function C:blend_to_player(u)
    local cam = self.cams["Handoff"]
    local ps = Game.player_state
    if not cam or not ps or not ps.cam then return end
    if not self.blend_from then
        local src = self.last_cam or cam
        local c = src:get("Camera")
        self.blend_from = { cam = cam, pos = src.world_position, rot = src.rotation, fov = c.fov_y,
                            own_fov = cam:get("Camera").fov_y }
    end
    local b = self.blend_from
    local k = smooth(u)
    local to_pos = ps.cam.world_position
    local to_rot = vector.create(ps.pitch or 0, ps.yaw or 0, 0)
    b.cam.position = b.pos + (to_pos - b.pos) * k
    b.cam.rotation = vector.create(b.rot.x + wrap(to_rot.x - b.rot.x) * k, b.rot.y + wrap(to_rot.y - b.rot.y) * k,
                                   b.rot.z * (1 - k))
    local c = b.cam:get("Camera")
    c.fov_y = b.fov + ((Game.settings.fov or 70) - b.fov) * k
    b.cam:set("Camera", c)
end

function C:stream(on)
    for _, cam in self.streamers do
        local s = cam:get("StreamingSource")
        s.enabled = on
        cam:set("StreamingSource", s)
    end
end

function C:finish()
    if not self.active then return end
    self.active = false
    self:stream(false)
    self.entity:stop_sequence()
    if self.blend_from then
        local c = self.blend_from.cam:get("Camera")
        c.fov_y = self.blend_from.own_fov
        self.blend_from.cam:set("Camera", c)
        self.blend_from = nil
    end
    if Game.restore_view then Game.restore_view() end
    self:shot_fog(nil)
    Game.cinematic = false
    Game.cinematic_id = nil
    Game.present.skip_hint = false
    Game.present.title = nil
    Game.present.subtitle_title = nil
    Controls.poll()
    Game.emit("cinematic_finished", self.id, self.skipped)
    if self.opts.done then self.opts.done(self.skipped) end
end

function C:skip()
    if self.skipped or not self.active then return end
    self.skipped = true
    Dialogue.clear(0)
    self.fade_out = 0
end

function C:update(dt)
    local pres = Game.present
    if not self.active then
        if Game.cinematic_id == nil then
            pres.letterbox = Game.damp(pres.letterbox, 0, 5, dt)
            if not self.fade_hold then pres.fade = Game.damp(pres.fade, 0, 4, dt) end
        end
        return
    end
    -- pause follows the pause menu
    local st = self.entity:sequence_state()
    local paused = Game.paused == true
    if st and st.paused ~= paused then self.entity:pause_sequence(paused) end
    if paused then return end

    self.t += dt
    pres.letterbox = Game.damp(pres.letterbox, self.letterbox and 1 or 0, 3, dt)
    if self.fade_to then
        pres.fade = Game.damp(pres.fade, self.fade_to, 6, dt)
        if math.abs(pres.fade - self.fade_to) < 0.01 then pres.fade = self.fade_to; self.fade_to = nil end
    end

    -- skip: hold after the grace period; fade to black, apply end state, return control
    pres.skip_hint = self.t > self.grace and not self.skipped
    if pres.skip_hint and Controls.down("skip") then
        self.held += dt
        if self.held >= self.skip_hold then self:skip() end
    else
        self.held = 0
    end
    if self.fade_out then
        self.fade_out += dt
        pres.fade = math.min(1, self.fade_out / 0.25)
        if self.fade_out >= 0.3 then
            if self.opts.on_skip then self.opts.on_skip() end
            self:finish()
            pres.fade = 1
        end
        return
    end

    self:operate(dt)
    st = self.entity:sequence_state()
    if not st then self:finish(); return end
    local dur = st.duration
    local cur = self:camera_entity()
    if cur and cur.name ~= "Handoff" then self.last_cam = cur end
    if cur and next(self.fog) then self:shot_fog(cur.name) end
    if cur and cur.name == "Handoff" and self.handoff > 0 then
        self.handoff_t = (self.handoff_t or 0) + dt
        self:blend_to_player(self.handoff_t / self.handoff)
    end
    if st.finished or (dur > 0 and st.time >= dur) then self:finish() end
end

return C
