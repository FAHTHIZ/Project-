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
    -- Movement (camera-relative), with acceleration.
    local want = vector.create(0, 0, 0)
    local sprint = false
    if playing then
        local m = Controls.move()
        if Controls.pressed("crouch") then self.crouched = not self.crouched end
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
        else self.entity:jump(self.jump_speed) end
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
