-- SPECIAL OPS first-person player controller.
-- Entity layout (built by tools/scenes/rig.py):
--   Player (CharacterController, Perceptible, AttributeSet health, this script)
--     Head            pitch pivot at eye height
--       Main Camera   Camera; bob/shake/landing offsets are applied here
--         Viewmodel   weapons and the field device (scripts/weapons.luau)
-- Gameplay always runs through this camera. Cinematics take the camera away by switching the
-- primary Camera to a cinematic one and give it back with restore_view(); this script keeps the
-- yaw/pitch so control resumes exactly where it was.
local Game = require("scripts/lib/game")
local Controls = require("scripts/lib/controls")

local P = {}
P.walk_speed = 3.6
P.sprint_speed = 5.8
P.crouch_speed = 1.9
P.aim_speed = 2.2
P.acceleration = 14
P.air_acceleration = 3
P.jump_speed = 4.6
P.eye_height = 1.62
P.crouch_eye = 1.12
P.pitch_limit = 84
P.interact_range = 2.6
P.max_health = 100
P.regen_delay = 4.0
P.regen_rate = 18

-- Interactables live in lib/game.luau so any script can register them before the player starts.
local interactables = Game.interactables

function P:start()
    Game.load_settings()
    Game.player = self.entity
    self.head = self.entity:find_child("Head")
    self.cam = self.head and self.head:find_child("Main Camera")
    -- weapon light (rig.py): starts on at night; the light action toggles it
    self.torch = self.cam and self.cam:find_child("Weapon Light")
    self.torch_on = true
    if self.torch and self.torch.valid then
        local l = self.torch:get("Light")
        self.torch_power = l and l.intensity or 0
    end
    Game.camera = self.cam
    self.yaw = self.entity.rotation.y
    self.pitch = 0
    self.vel = vector.create(0, 0, 0)
    self.bob = 0
    self.land = 0
    self.shake = 0
    self.eye = self.eye_height
    self.air = 0
    self.fov = Game.settings.fov
    self.fov_now = -1
    self.health = self.max_health
    self.since_hit = 99
    self.focus = nil
    self.crouched = false
    self.zoom = 0 -- 0..1 aim-down-sights blend, written by weapons.luau
    Game.player_state = self
end

function P:save_state()
    return { yaw = self.yaw, pitch = self.pitch, health = self.health }
end
function P:load_state(s)
    self.yaw = s.yaw or self.yaw
    self.pitch = s.pitch or 0
    self.health = s.health or self.max_health
    self.vel = vector.create(0, 0, 0)
end

-- Damage from enemies (abstract game value). Returns true when the player is downed.
function P:hurt(amount, from)
    if Game.cinematic or self.health <= 0 then return false end
    self.health = math.max(0, self.health - amount)
    self.since_hit = 0
    self:add_shake(0.35)
    Game.emit("player_hurt", amount, from)
    if self.health <= 0 then
        Game.emit("player_downed")
        return true
    end
    return false
end
Game.hurt_player = function(amount, from)
    local s = Game.player_state
    return s and s:hurt(amount, from)
end

function P:add_shake(a)
    self.shake = math.min(1.0, self.shake + a * Game.settings.camera_shake)
end

-- Look direction in world space.
function P:aim_ray()
    local cp = self.cam.world_position
    local yr, pr = math.rad(self.yaw), math.rad(self.pitch)
    local dir = vector.create(-math.sin(yr) * math.cos(pr), math.sin(pr), -math.cos(yr) * math.cos(pr))
    return cp, dir
end
Game.aim_ray = function()
    local s = Game.player_state
    if s and s.cam then return s:aim_ray() end
    return nil
end

-- Snap the view to face a point (used after cinematics and at checkpoints).
function P:face(point)
    local p = self.entity.position
    local d = point - p
    self.yaw = math.deg(math.atan2(-d.x, -d.z))
    self.pitch = 0
end
Game.face_player = function(point)
    if Game.player_state then Game.player_state:face(point) end
end

-- Riding in a vehicle seat (scripts/vehicle.luau): the body rides the seat marker with gravity
-- and vehicle collision off, the view turns with the vehicle and can look around within the
-- cabin (about 110 degrees either side of straight ahead). dismount() steps out through a door.
local VEHICLE_LAYER_BIT = 64
local RIDE_EYE = 1.24
local function wrap180(a) return (a + 540) % 360 - 180 end

function P:ride(v, seat)
    local cc = self.entity:get("CharacterController")
    if cc and not self.cc_saved then
        self.cc_saved = { gravity_scale = cc.gravity_scale, mask = cc.mask }
        self.entity:set("CharacterController", { gravity_scale = 0,
                                                 mask = bit32.band(cc.mask, bit32.bnot(VEHICLE_LAYER_BIT)) })
    end
    self.riding = { v = v, seat = seat, base = v.yaw }
    self.yaw = v.yaw
    self.pitch = -4
    self.vel = vector.create(0, 0, 0)
    self.crouched = false
    self.entity.position = v:seat_root(seat)
    Game.emit("player_boarded", v.name, seat)
end

-- Step out through `door` (fl/fr/rl/rr): slide to the door, stand up outside, then walk control
-- returns. `face` is an optional world point to turn toward while stepping out.
function P:dismount(door, face)
    local r = self.riding
    if not r then return end
    r.exit = { door = door, t = 0, from = self.entity.position, face = face }
    r.v:set_door(door, true)
end

function P:in_vehicle() return self.riding ~= nil end

function P:update_ride(dt, playing)
    local r = self.riding
    local v = r.v
    -- turn with the vehicle
    local dv = wrap180(v.yaw - r.base)
    r.base = v.yaw
    self.yaw += dv
    local x = r.exit
    if not x then
        local rel = wrap180(self.yaw - v.yaw)
        if math.abs(rel) > 110 then self.yaw = v.yaw + math.clamp(rel, -110, 110) end
        self.entity.position = v:seat_root(r.seat)
        self.vel = vector.create(0, 0, 0)
        return RIDE_EYE
    end
    x.t += dt
    -- 0..0.6 s wait for the door; 0.6..1.6 slide to the sill; 1.6..2.6 rise and step out
    local function sm(t) t = math.clamp(t, 0, 1); return t * t * (3 - 2 * t) end
    local sill = v:sill_root(r.seat, x.door)
    local out = v:door_point(x.door)
    local eye = RIDE_EYE
    if x.t < 0.6 then
        self.entity.position = v:seat_root(r.seat)
    elseif x.t < 1.6 then
        self.entity.position = x.from + (sill - x.from) * sm((x.t - 0.6) / 1.0)
        if x.face then
            local d = out - self.entity.position
            local want = math.deg(math.atan2(-d.x, -d.z))
            self.yaw += wrap180(want - self.yaw) * math.min(1, dt * 3)
        end
    else
        local k = sm((x.t - 1.6) / 1.0)
        self.entity.position = sill + (out - sill) * k
        eye = RIDE_EYE + (self.eye_height - RIDE_EYE) * k
        if x.face then
            local d = x.face - self.entity.position
            local want = math.deg(math.atan2(-d.x, -d.z))
            self.yaw += wrap180(want - self.yaw) * math.min(1, dt * 2.5)
        end
    end
    if x.t >= 2.6 then
        if self.cc_saved then
            self.entity:set("CharacterController", self.cc_saved)
            self.cc_saved = nil
        end
        self.riding = nil
        Game.emit("player_dismounted", v.name, x.door)
        return nil
    end
    return eye
end

function P:find_focus()
    local origin, dir = self:aim_ray()
    local hit = physics.raycast(origin, dir, self.interact_range, nil, self.entity)
    local best = nil
    if hit and hit.entity then
        local e = hit.entity
        while e and e.valid do
            local r = interactables[e.id]
            if r and r.enabled then best = r; break end
            e = e.parent
        end
    end
    if not best then
        -- Forgiving fallback for touch: nearest enabled interactable in a narrow cone.
        local bestd = 1.7
        for _, r in interactables do
            if r.enabled and r.entity.valid then
                local to = r.entity.world_position - origin
                local d = vector.magnitude(to)
                if d < bestd and d > 0.01 and vector.dot(to / d, dir) > 0.8 then
                    best = r
                    bestd = d
                end
            end
        end
    end
    return best
end

function P:update(dt)
    if not self.cam then return end
    local s = Game.settings
    Controls.poll()
    local playing = Game.playing()
    local cc_state = self.entity.grounded
    -- Look.
    if playing then
        local look = Controls.look()
        local sens = (1 - self.zoom * (1 - s.aim_sensitivity)) * (self.zoom_sens or 1)
        self.yaw = self.yaw - look.x * sens
        self.pitch = Game.clamp(self.pitch - look.y * sens, -self.pitch_limit, self.pitch_limit)
    end
    local ride_eye = nil
    if self.riding then ride_eye = self:update_ride(dt, playing) end
    if ride_eye then
        self.eye = Game.damp(self.eye, ride_eye, 10, dt)
        self.head.position = vector.create(0, self.eye, 0)
        self.head.rotation = vector.create(self.pitch, 0, 0)
        self.cam.position = vector.create(0, 0, 0)
        self.cam.rotation = vector.create(0, 0, 0)
        self.entity.rotation = vector.create(0, self.yaw, 0)
        self.focus = nil
        Game.focus = nil
        self.ground_speed = 0
        if self.fov_now < 0 and not Game.cinematic then
            local c = self.cam:get("Camera")
            c.fov_y = s.fov
            c.primary = true
            self.cam:set("Camera", c)
            self.fov = s.fov
            self.fov_now = s.fov
        end
        return
    end
    -- Movement (camera-relative), with acceleration.
    local want = vector.create(0, 0, 0)
    local sprint = false
    if playing then
        local m = Controls.move()
        if Controls.pressed("crouch") then self.crouched = not self.crouched end
        if Controls.pressed("light") and self.torch and self.torch.valid then
            self.torch_on = not self.torch_on
            local l = self.torch:get("Light")
            if l then l.intensity = self.torch_on and self.torch_power or 0; self.torch:set("Light", l) end
            audio.play("audio/foley/torch_click.wav", { bus = "sfx", volume = 0.5 })
        end
        sprint = Controls.down("sprint") and m.y > 0.3 and self.zoom < 0.3
        if sprint then self.crouched = false end
        local speed = self.walk_speed
        if self.crouched then speed = self.crouch_speed
        elseif sprint then speed = self.sprint_speed end
        speed = Game.lerp(speed, math.min(speed, self.aim_speed), self.zoom)
        local yr = math.rad(self.yaw)
        local fwd = vector.create(-math.sin(yr), 0, -math.cos(yr))
        local right = vector.create(math.cos(yr), 0, -math.sin(yr))
        want = (fwd * m.y + right * m.x) * speed
    end
    self.sprinting = sprint
    local accel = cc_state and self.acceleration or self.air_acceleration
    self.vel = self.vel + (want - self.vel) * (1 - math.exp(-accel * dt))
    self.entity:move_character(self.vel)
    if playing and Controls.pressed("jump") and cc_state then
        if self.crouched then self.crouched = false
        else self.entity:jump(self.jump_speed); Game.emit("player_jumped") end
    end
    -- Landing dip.
    if cc_state and self.air > 0.25 then self.land = math.min(1, self.air * 0.6) end
    self.air = cc_state and 0 or self.air + dt
    self.land = Game.damp(self.land, 0, 7, dt)
    -- Body yaw on the root; pitch on the head; eye height eases between stand and crouch.
    self.entity.rotation = vector.create(0, self.yaw, 0)
    self.eye = Game.damp(self.eye, self.crouched and self.crouch_eye or self.eye_height, 10, dt)
    local hv = self.entity.velocity
    local ground_speed = vector.magnitude(vector.create(hv.x, 0, hv.z))
    self.ground_speed = ground_speed
    local bob_amp = (s.head_bob and s.camera_shake > 0) and 1 or 0
    if cc_state and ground_speed > 0.4 then
        self.bob = self.bob + dt * (5.5 + ground_speed * 0.9)
    end
    local bob_scale = math.min(1, ground_speed / self.walk_speed) * bob_amp * (1 - self.zoom * 0.85)
    local bob_y = math.abs(math.sin(self.bob)) * 0.035 * bob_scale - self.land * 0.12
    local bob_x = math.cos(self.bob) * 0.02 * bob_scale
    self.shake = Game.damp(self.shake, 0, 6, dt)
    local sh = self.shake * self.shake
    local t = time.now()
    local shake_p = (math.sin(t * 61) + math.sin(t * 37)) * 0.9 * sh
    local shake_y = (math.sin(t * 53) + math.sin(t * 29)) * 0.9 * sh
    self.head.position = vector.create(0, self.eye, 0)
    self.head.rotation = vector.create(self.pitch + shake_p, 0, 0)
    self.cam.position = vector.create(bob_x, bob_y, 0)
    self.cam.rotation = vector.create(0, shake_y, bob_x * 25)
    -- Field of view: base, sprint widen, aim narrow (weapons.luau writes zoom_fov).
    local fov = s.fov + (sprint and 6 or 0)
    if self.zoom > 0 then fov = Game.lerp(fov, self.zoom_fov or (s.fov * 0.72), self.zoom) end
    self.fov = Game.damp(self.fov, fov, 12, dt)
    if math.abs(self.fov - self.fov_now) > 0.05 and not Game.cinematic then
        local c = self.cam:get("Camera")
        c.fov_y = self.fov
        c.primary = true
        self.cam:set("Camera", c)
        self.fov_now = self.fov
    end
    -- Health regeneration.
    self.since_hit = self.since_hit + dt
    if self.health > 0 and self.health < self.max_health and self.since_hit > self.regen_delay then
        self.health = math.min(self.max_health, self.health + self.regen_rate * dt)
    end
    -- Interaction focus and use.
    self.focus = playing and self:find_focus() or nil
    Game.focus = self.focus
    if self.focus and Controls.pressed("interact") then
        local r = self.focus
        if r.fn then r.fn(self.entity) end
        events.emit("interact", { by = self.entity }, r.entity)
        Game.emit("interacted", r.entity)
    end
end

-- Hand the camera back after a cinematic: primary camera, FOV re-applied, input cleared.
Game.restore_view = function()
    local s = Game.player_state
    if not s or not s.cam then return end
    s.fov_now = -1
    s.vel = vector.create(0, 0, 0)
    local c = s.cam:get("Camera")
    c.primary = true
    s.cam:set("Camera", c)
end

return P
