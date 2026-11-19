-- Shared body control for human NPCs (squad operators, Greyline contractors, civilians).
-- Entity layout (tools/scenes/actors.py):
--   <Root>  CharacterController, NavAgent (rotate off), Perceptible, Script
--     Voice           AudioSource (spatial, voice bus) at mouth height
--     Body            Animator (anim/characters/human.vanim) + skeleton
--       ... Chest > Carry (third-person PC-7, Grip R / Grip L IK targets, Carry Muzzle)
--       ... Head (look_at IK)
-- The actor faces its movement direction while walking and its focus point otherwise, blends the
-- carried weapon between low-ready and aim, drives the head IK and the face, and plays footsteps.
local Game = require("scripts/lib/game")
local Face = require("scripts/lib/face")

local Actor = {}
Actor.__index = Actor

-- Carry (child of Body, character space: +Z forward, +X the character's left). Low-ready sits at
-- the right hip with the muzzle down and across; aim raises it to the right shoulder.
local READY_P, AIM_P = vector.create(-0.07, 1.14, 0.27), vector.create(-0.13, 1.42, 0.34)
local SEAT_P = vector.create(-0.02, 0.62, 0.36)

local function lerpv(a, b, t) return a + (b - a) * t end

-- Facing yaw (deg) of an entity whose model faces +Z (euler .y is ambiguous past 90 degrees).
function Actor.yaw_of(e)
    local f = e.forward
    return math.deg(math.atan2(-f.x, -f.z))
end

function Actor.new(entity, seed)
    local self = setmetatable({}, Actor)
    self.entity = entity
    self.body = entity:find_child("Body")
    self.voice = entity:find_child("Voice")
    if type(seed) ~= "number" then
        local h = 7
        for i = 1, #entity.name do h = (h * 31 + string.byte(entity.name, i)) % 1000003 end
        seed = h
    end
    self.seed = seed
    self.face = self.body and Face.new(self.body, seed)
    self.head = self.body and Face.find_named(self.body, "Head")
    self.carry = self.body and Face.find_named(self.body, "Carry")
    self.muzzle = self.carry and self.carry:find_child("Carry Muzzle")
    self.hand_l = self.body and Face.find_named(self.body, "Hand.L")
    self.yaw = Actor.yaw_of(entity)
    self.aim = 0          -- 0 low ready .. 1 aiming
    self.aim_want = 0
    self.aim_pitch = 0
    self.focus = nil      -- world point to face when standing
    self.look = nil       -- world point for the head/eyes (expires)
    self.look_t = 0
    self.look_w = 0
    self.step_dist = 0
    self.last_pos = entity.position
    self.gesture_t = 0
    self.talking = false
    self.speed_now = 0
    self.frozen = false
    return self
end

function Actor:param(name, v)
    if self.body then self.body:set_anim_param(name, v) end
end
function Actor:trigger(name)
    if self.body then self.body:anim_trigger(name) end
end

-- Left-arm gestures release the support hand from the weapon for their duration.
function Actor:gesture(name, seconds)
    self:trigger(name)
    self.gesture_t = seconds or 1.5
end

function Actor:look_at(point, seconds)
    self.look = point
    self.look_t = seconds or 1.0
end

function Actor:talk(on)
    self.talking = on
    self:param("talk", on and self.aim < 0.3)
end

function Actor:go(point)
    self.goal = point
    return self.entity:set_destination(point)
end
function Actor:halt()
    self.goal = nil
    self.entity:stop()
end
function Actor:arrived()
    local n = self.entity:nav_state()
    return (not n) or (not n.has_destination) or n.reached
end

-- Teleport (checkpoints, cinematics).
function Actor:place(pos, yaw)
    self.entity:stop()
    self.entity.position = pos
    if yaw then self.yaw = yaw end
    self.entity.rotation = vector.create(0, self.yaw, 0)
    self.last_pos = pos
end

local function wrap(a) return (a + 540) % 360 - 180 end

function Actor:update(dt)
    local e = self.entity
    local v = e.velocity
    local flat = vector.create(v.x, 0, v.z)
    local spd = vector.magnitude(flat)
    self.speed_now = Game.damp(self.speed_now, spd, 10, dt)
    -- facing
    local want = nil
    if spd > 0.5 and self.aim < 0.5 then
        want = math.deg(math.atan2(flat.x, flat.z))
    elseif self.focus then
        local d = self.focus - e.position
        if d.x * d.x + d.z * d.z > 0.04 then want = math.deg(math.atan2(d.x, d.z)) end
    end
    if self.hold_yaw then want = nil end -- a vehicle or cinematic owns the body yaw
    if want then
        local diff = wrap(want - self.yaw)
        local rate = (spd > 0.5) and 300 or 200
        self.yaw += math.clamp(diff, -rate * dt, rate * dt)
        e.rotation = vector.create(0, self.yaw, 0)
    end
    -- animation parameters (the walk cycle matches about 1.15 m/s per blend unit)
    self:param("speed", self.speed_now * 1.0)
    local cs = e:character_state()
    -- a seated rider has no ground under the controller (gravity off); keep the graph out of Fall
    if cs then self:param("grounded", cs.grounded or self.seated == true) end
    -- seated_pose = false lets the rider stand (SitStand) while still attached to the vehicle
    self:param("seated", self.seated == true and self.seated_pose ~= false)
    -- carried weapon pose
    self.aim = Game.damp(self.aim, self.aim_want, 8, dt)
    -- seated: rifle upright between the knees (follows the Sit clip's lowered hips)
    self.sit_w = Game.damp(self.sit_w or 0, (self.seated and self.seated_pose ~= false) and 1 or 0, 5, dt)
    if self.carry and self.carry.valid then
        local cpos = lerpv(READY_P, AIM_P, self.aim)
        cpos = lerpv(cpos, SEAT_P, self.sit_w)
        self.carry.position = cpos
        -- muzzle direction in character space (look_at works in the parent's space, -Z forward)
        local p = math.rad(self.aim_pitch)
        local ready_dir = vector.create(0.34, -0.66, 0.67)
        local aim_dir = vector.create(0, math.sin(p), math.cos(p))
        local dir = vector.normalize(lerpv(lerpv(ready_dir, aim_dir, self.aim), vector.create(0.05, 0.96, 0.28), self.sit_w))
        self.carry:look_at(cpos + dir * 2)
    end
    -- support hand
    if self.gesture_t > 0 then
        self.gesture_t -= dt
    end
    if self.hand_l and self.hand_l.valid and self.carry then
        local want_w = (self.gesture_t > 0 or (self.talking and self.aim < 0.3)) and 0 or 1
        self.hand_w = Game.damp(self.hand_w or 1, want_w, 10, dt)
        if math.abs(self.hand_w - want_w) < 0.02 then self.hand_w = want_w end
        if self.hand_w ~= self.hand_w_set then
            self.hand_w_set = self.hand_w
            self.hand_l:set("IKConstraint", { weight = self.hand_w })
        end
    end
    -- head look
    if self.look_t > 0 then self.look_t -= dt end
    local look = (self.look_t > 0) and self.look or nil
    if not look and self.focus and self.aim > 0.5 then look = self.focus end
    self.look_w = Game.damp(self.look_w, look and 0.85 or 0, 4, dt)
    if self.head and self.head.valid then
        if look then self.look_point = look end
        if self.look_point then self.head:set_ik_target(self.look_point, self.look_w) end
    end
    if self.face then
        local cam = Game.camera
        self.face:update(dt, look, self.yaw, cam and cam.world_position)
    end
    -- footsteps
    local moved = vector.magnitude(e.position - self.last_pos)
    self.last_pos = e.position
    if cs and cs.grounded and moved < 1 and not self.seated then
        self.step_dist += moved
        local stride = spd > 3 and 1.25 or 0.8
        if self.step_dist > stride then
            self.step_dist = 0
            local cam = Game.camera
            if cam and vector.magnitude(e.position - cam.world_position) < 18 then
                local surface = self.surface or "dirt"
                audio.play("audio/foley/step_" .. surface .. "_" .. math.random(0, 3) .. ".wav",
                           { position = e.position, volume = 0.35, pitch = 0.92 + math.random() * 0.16, bus = "sfx",
                             max_instances = 6 })
            end
        end
    end
end

-- Muzzle position and forward direction of the carried weapon.
function Actor:muzzle_ray()
    if self.muzzle and self.muzzle.valid then
        return self.muzzle.world_position
    end
    return self.entity.position + vector.create(0, 1.4, 0)
end

return Actor
