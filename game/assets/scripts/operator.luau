-- Halyard Team operator (Anchor, Patch, Echo, Tally): follows the player in formation, holds or
-- moves on orders, engages Greyline contractors it can see, reacts with barks, looks at whoever
-- is talking and plays its own voice lines with lip sync. Companions are never taken out: hits
-- make them stagger and take cover for a moment. In a firefight near the player (follow mode),
-- each operator finds real cover against the contractor it is fighting (lib/tactics.luau) within
-- 14 m of the player, ducks between bursts there and moves again if the cover stops covering.
local Game = require("scripts/lib/game")
local Combat = require("scripts/lib/combat")
local Actor = require("scripts/lib/actor")
local Squad = require("scripts/lib/squad")
local Dialogue = require("scripts/lib/dialogue")
local Tactics = require("scripts/lib/tactics")

local Op = {}
Op.who = "Anchor"
Op.role = "lead"
Op.order = "follow"     -- initial order: follow | hold
Op.engage = true        -- fires at visible enemies
Op.surface = "auto"     -- footstep set: auto (ray down) or dirt/grass/gravel/mud/concrete/metal/wood
Op.ride = ""            -- vehicle name to start seated in (with `seat`)
Op.seat = ""

function Op:start()
    self.r = Squad.ROSTER[self.who] or Squad.ROSTER.Anchor
    self.key = self.r.key
    self.actor = Actor.new(self.entity, #self.who * 7919 + string.byte(self.who, 1))
    self.actor.surface = self.surface
    if self.actor.face then self.actor.face:set_emotion(self.r.emotion, 9999) end
    self.mode = self.order
    self.hold_point = self.entity.position
    self.goal = nil
    self.repath_t = 0
    self.fire_t = 1 + math.random()
    self.burst = 0
    self.shots = 0
    self.engaged = false
    self.engaged_t = 0
    self.stagger_t = 0
    self.idle_t = 0
    self.hits = 0
    self.actor:set_speed(self.r.speed)
    local a = self.actor
    Dialogue.register(self.key, {
        entity = self.entity, voice = a.voice, face = a.face,
        look_at = function(p) a:look_at(p, 0.6) end,
        talk = function(on) a:talk(on) end,
        can_speak = function() return true end,
    })
    Squad.register(self.who, self)
    Combat.register(self.entity, function(info) return self:on_hit(info) end)
end

-- Orders from Squad.order ----------------------------------------------------------------------
function Op:set_order(mode, point, opts)
    self.mode = mode
    self.goal = nil
    if mode == "hold" then
        self.hold_point = self.entity.position
        self.actor:halt()
    elseif mode == "move" then
        self.hold_point = point or self.entity.position
        self.actor:go(self.hold_point)
        self.goal = self.hold_point
    end
    self.face_point = opts and opts.face and opts.face[self.who] or (opts and opts.face_all)
end

-- Teleport for checkpoints and cinematics.
function Op:place(pos, yaw)
    self.actor:place(pos, yaw)
    self.goal = nil
    self.hold_point = pos
end

-- Vehicle occupancy -----------------------------------------------------------------------------
-- Seated occupants ride the seat marker (no gravity, no collision with the vehicle layer). The
-- exit is staged: open the door, swing out toward it, stand up onto the ground outside, turn
-- and push the door shut, then walk to the regroup point.
local VEHICLE_LAYER_BIT = 64

local function smooth(t) t = math.clamp(t, 0, 1); return t * t * (3 - 2 * t) end
local function lerp_yaw(a, b, t) return a + (((b - a) + 540) % 360 - 180) * t end

function Op:set_ride(on)
    local cc = self.entity:get("CharacterController")
    if not cc then return end
    if on then
        self.cc_saved = self.cc_saved or { gravity_scale = cc.gravity_scale, mask = cc.mask }
        self.entity:set("CharacterController", { gravity_scale = 0,
                                                 mask = bit32.band(cc.mask, bit32.bnot(VEHICLE_LAYER_BIT)) })
    elseif self.cc_saved then
        self.entity:set("CharacterController", self.cc_saved)
        self.cc_saved = nil
    end
end

function Op:board(v, seat)
    self.vehicle = v
    self.seat = seat
    self.mode = "vehicle"
    self.vphase = "seated"
    self.vt = 0
    self.goal = nil
    self:set_ride(true)
    local a = self.actor
    a.seated = true
    a.seated_pose = nil
    a.hold_yaw = true
    a:param("seated", true)
    a:place(v:seat_root(seat), v:seat_yaw())
end

-- opts: regroup (world point), face (world point), close (default true), delay (s)
function Op:exit_vehicle(door, opts)
    if self.mode ~= "vehicle" then return end
    opts = opts or {}
    self.exit = { door = door, regroup = opts.regroup, face = opts.face, close = opts.close ~= false,
                  delay = opts.delay or 0 }
    self.vphase = "wait"
    self.vt = 0
end

function Op:in_vehicle() return self.mode == "vehicle" end
function Op:exit_done() return self.mode ~= "vehicle" and self.exit == nil end

function Op:update_vehicle(dt)
    local v, a, x = self.vehicle, self.actor, self.exit
    self.vt += dt
    local ph = self.vphase
    if ph == "seated" or ph == "wait" then
        a:place(v:seat_root(self.seat), v:seat_yaw())
        if ph == "wait" and self.vt >= x.delay then
            v:set_door(x.door, true)
            self.vphase = "door"; self.vt = 0
        end
    elseif ph == "door" then
        a:place(v:seat_root(self.seat), v:seat_yaw())
        a:look_at(v:door_point(x.door) + vector.create(0, 1.0, 0), 0.5)
        if v:door_open(x.door) or self.vt > 1.0 then self.vphase = "swivel"; self.vt = 0 end
    elseif ph == "swivel" then
        local k = smooth(self.vt / 0.75)
        local p0, p1 = v:seat_root(self.seat), v:sill_root(self.seat, x.door)
        a:place(p0 + (p1 - p0) * k, lerp_yaw(v:seat_yaw(), v:door_out_yaw(x.door), k))
        if self.vt >= 0.75 then
            self.vphase = "stand"; self.vt = 0
            a.seated_pose = false
            a:param("seated", false)
            self.stand_from = p1
        end
    elseif ph == "stand" then
        -- SitStand: lean (0..0.35 s) then rise; the body travels out over the sill while rising
        local k = smooth((self.vt - 0.15) / 0.95)
        local p1 = v:door_point(x.door)
        local p = self.stand_from + (p1 - self.stand_from) * k
        a:place(p, v:door_out_yaw(x.door))
        if self.vt >= 1.15 then
            a.seated = false
            self:set_ride(false)
            self.vphase = x.close and "turn" or "leave"; self.vt = 0
        end
    elseif ph == "turn" then
        -- turn back toward the door and push it shut
        local dp = v.doors[x.door].pivot.world_position
        local d = dp - self.entity.position
        local want = math.deg(math.atan2(d.x, d.z))
        a.yaw = lerp_yaw(a.yaw, want, math.min(1, dt * 6))
        self.entity.rotation = vector.create(0, a.yaw, 0)
        if self.vt > 0.45 and not x.pushed then
            x.pushed = true
            a:trigger("interact")
        end
        if self.vt > 0.8 and not x.shut then x.shut = true; v:set_door(x.door, false) end
        if self.vt > 1.25 then self.vphase = "leave"; self.vt = 0 end
    elseif ph == "leave" then
        a.hold_yaw = false
        self.vehicle = nil
        self.exit = nil
        if x.regroup then
            self:set_order("move", x.regroup, { face_all = x.face })
        else
            self:set_order("hold", nil, { face_all = x.face })
        end
        Game.emit("vehicle_exited", self.who, x.door)
        return
    end
    a.focus = nil
    a.aim_want = 0
    a:update(dt)
end

function Op:on_hit(info)
    if info.team == "squad" or (Game.player and info.source and info.source.id == Game.player.id) then
        -- friendly fire: a flinch, a look and a word about it (scripts/lib/reactions.luau)
        if info.source and Game.player and info.source.id == Game.player.id then Game.emit("friendly_hit", self.r.key) end
        self.actor:look_at(Game.camera and Game.camera.world_position or self.entity.position, 1.2)
        if self.actor.face then self.actor.face:set_emotion("surprise", 0.8) end
        return false
    end
    self.hits += 1
    self.hit_t = time.now()
    Game.emit("operator_hit", self.r.key)
    if self.stagger_t <= 0 then
        self.actor:trigger("stumble")
        self.stagger_t = 2.4
        if self.actor.face then self.actor.face:set_emotion("concern", 2.0) end
    end
    return false
end

-- Perception ----------------------------------------------------------------------------------
function Op:visible_enemy()
    local p = self.entity:perception()
    if not p or not p.target or not p.target.valid then return nil, p end
    local rec = Squad.state().enemies[p.target.id]
    if rec and rec.ctl and (rec.ctl.down or rec.ctl.parley or rec.ctl.dormant) then
        -- pick another seen enemy that is still up
        for _, t in p.seen do
            local r2 = Squad.state().enemies[t.id]
            if r2 and r2.ctl and not (r2.ctl.down or r2.ctl.parley or r2.ctl.dormant) then return t, p end
        end
        return nil, p
    end
    -- weapons tight on contractors who have not noticed anyone: the squad does not start the fight
    -- unless the player fires first (or the contractor goes alert)
    if rec and rec.ctl and rec.ctl.state == "patrol" and time.now() - (Squad.state().player_shot_t or -100) > 15 then
        return nil, p
    end
    if p.visible then return p.target, p end
    return nil, p
end

local function flat_dist(a, b)
    local d = a - b
    return math.sqrt(d.x * d.x + d.z * d.z)
end

function Op:update(dt)
    if Game.paused then return end
    local a = self.actor
    local e = self.entity
    if self.stagger_t > 0 then self.stagger_t -= dt end
    if self.ride ~= "" and not self.boarded then
        local v = Game.vehicles and Game.vehicles[self.ride]
        if v and v.seats and v.entity.valid and v.started_frame then self.boarded = true; self:board(v, self.seat) end
    end
    if self.mode == "vehicle" then return self:update_vehicle(dt) end
    -- combat awareness
    local target, per = nil, nil
    if self.engage and not Game.cinematic then target, per = self:visible_enemy() end
    if target then
        if not self.engaged then
            self.engaged = true
            Dialogue.bark("contact", { cooldown = 8 })
            Game.emit("squad_contact", self.who)
        end
        self.engaged_t = 3.0
        self.last_target = target
    elseif self.engaged then
        self.engaged_t -= dt
        if self.engaged_t <= 0 then
            self.engaged = false
            if #Squad.active_enemies() == 0 then Dialogue.bark("clear", { cooldown = 12 }) end
        end
    end
    -- bounding overwatch: answer a mate's "Moving!" a beat later
    if self.cover_call_t and time.now() >= self.cover_call_t then
        self.cover_call_t = nil
        if self.engaged then Dialogue.bark("covering", { speaker = self.key, cooldown = 6, ttl = 2.0 }) end
    end
    -- movement
    if self.mode == "follow" then
        local slot = Squad.slot_point(self.who)
        if slot then
            local d_player = Game.player and flat_dist(e.position, Game.player.position) or 0
            local d_slot = flat_dist(e.position, slot)
            local hold_fire = self.engaged and d_player < 12
            if hold_fire then
                self:combat_move(dt)
            else
                self.cover_goal, self.in_cover = nil, nil
                self.repath_t -= dt
                if d_slot > 1.4 and (not self.goal or flat_dist(slot, self.goal) > 1.2) and self.repath_t <= 0 then
                    local p = nav.available() and nav.nearest(slot, vector.create(3, 4, 3)) or slot
                    if p and a:go(p) then self.goal = p end
                    self.repath_t = 0.35
                elseif self.goal and d_slot < 0.6 then
                    a:halt(); self.goal = nil
                end
                -- catch up quicker when far behind
                local want_speed = d_player > 9 and self.r.speed * 1.35 or self.r.speed
                if want_speed ~= self.cur_speed then
                    self.actor:set_speed(want_speed)
                    self.cur_speed = want_speed
                end
            end
        end
    elseif self.mode == "move" then
        if self.goal and a:arrived() then
            self.goal = nil
            Game.emit("squad_arrived", self.who)
        end
    end
    -- aim / focus
    if target and target.valid then
        local tp = target.world_position + vector.create(0, 1.25, 0)
        a.focus = target.position
        a.aim_want = 1
        local muzzle = a:muzzle_ray()
        local d = tp - muzzle
        a.aim_pitch = math.deg(math.atan2(d.y, math.sqrt(d.x * d.x + d.z * d.z)))
        self:fire(dt, tp, flat_dist(e.position, target.position))
    else
        a.aim_want = self.engaged and 0.6 or 0
        a.aim_pitch = 0
        if self.face_point and self.mode ~= "follow" and not self.goal then
            a.focus = self.face_point
        elseif self.mode == "follow" and not self.goal and Game.player then
            -- idle in formation: face the way the player is looking
            local ps = Game.player_state
            if ps then
                local y = math.rad(ps.yaw)
                a.focus = e.position + vector.create(-math.sin(y), 0, -math.cos(y)) * 5
            end
        else
            a.focus = nil
        end
    end
    if not self.engaged then self.cover_goal, self.in_cover = nil, nil end
    local crouch = self.engaged and not self.goal and (self.r.role == "scout" or self.r.role == "lead") and self.stagger_t <= 0
    if self.in_cover and not self.goal then crouch = self.fire_t > 0.45 or self.stagger_t > 0 end
    -- quiet moves: when the player gets low, the team takes a knee at each halt too
    if not self.engaged and not self.goal and Game.player_state and Game.player_state.crouched then crouch = true end
    self.crouching = crouch
    a:param("crouch", crouch)
    a:update(dt)
end

-- Follow-mode firefight close to the player: get into cover against the current threat.
function Op:combat_move(dt)
    local a, e = self.actor, self.entity
    local now = time.now()
    if self.cover_goal then
        if a:arrived() or flat_dist(e.position, self.cover_goal) < 0.9 or now > self.cover_until then
            a:halt()
            self.goal = nil
            self.in_cover = self.cover_goal
            self.cover_goal = nil
            self.actor:set_speed(self.r.speed)
            self.cur_speed = self.r.speed
            if self.overwatch_by then
                self.overwatch_by.overwatch_until = nil
                self.overwatch_by = nil
            end
            if math.random() < 0.4 then Dialogue.bark("set", { speaker = self.key, cooldown = 8, ttl = 1.5 }) end
            Game.emit("squad_in_cover", self.who)
        end
        return
    end
    local t = self.last_target
    if not (t and t.valid) then
        if self.goal then a:halt(); self.goal = nil end
        return
    end
    if self.goal and not self.in_cover then a:halt(); self.goal = nil end
    if now < (self.cover_check or 0) then return end
    self.cover_check = now + 1.1 + math.random() * 0.7
    local threat = t.position
    local eye = threat + vector.create(0, 1.55, 0)
    if self.in_cover and not Tactics.exposed(eye, self.in_cover, e) then return end
    if not Tactics.exposed(eye, e.position, e) then
        self.in_cover = e.position
        return
    end
    local avoid = {}
    Squad.each(function(_, m)
        if m ~= self and (m.cover_goal or m.in_cover) then table.insert(avoid, m.cover_goal or m.in_cover) end
    end)
    local pp = Game.player and Game.player.position or e.position
    table.insert(avoid, pp)   -- not the player's spot
    -- one man up at a time (FM 3-21.8 bounding overwatch): wait while a mate is mid-rush, unless
    -- rounds are landing on this one
    local rushing = false
    Squad.each(function(_, m) if m ~= self and m.cover_goal then rushing = true end end)
    if rushing and now - (self.hit_t or -100) > 1.5 then
        self.cover_check = now + 0.6
        return
    end
    local c = Tactics.find_cover(e.position, threat, { radius = 7, ignore = e, avoid = avoid, min_threat = 5 })
    if c and flat_dist(c, pp) < 14 then
        self.cover_goal, self.in_cover = c, nil
        self.cover_until = now + 4.5   -- a 3-5 s rush: "I'm up, he sees me, I'm down"
        self.goal = c
        local sp = self.r.speed * 1.4
        self.actor:set_speed(sp)
        self.cur_speed = sp
        a:go(c)
        -- the nearest engaged, set mate covers the move with faster fire
        local by, bd = nil, 22
        Squad.each(function(_, m)
            if m ~= self and m.engaged and not m.cover_goal and m.mode ~= "vehicle" then
                local d = flat_dist(m.entity.position, e.position)
                if d < bd then by, bd = m, d end
            end
        end)
        if by then
            by.overwatch_until = now + 4.5
            by.cover_call_t = now + 0.8
            self.overwatch_by = by
            Dialogue.bark("moving", { speaker = self.key, cooldown = 5, ttl = 1.5 })
            Game.emit("squad_bound", { who = self.who, by = by.who })
        else
            Dialogue.bark("cover", { speaker = self.key, cooldown = 12, ttl = 2.5 })
            Game.emit("squad_bound", { who = self.who })
        end
    end
end

function Op:fire(dt, tp, dist)
    if self.stagger_t > 1.5 then return end
    self.fire_t -= dt
    if self.fire_t > 0 then return end
    local spread = (2.2 + dist * 0.06) / self.r.accuracy
    local _, struck = Squad.shoot(self, tp, { spread = spread, amount = 14, team = "squad", volume = 0.5,
                                                 sound = self.r.sound })
    if struck then Game.emit("squad_hit", self.who) end
    self.shots += 1
    self.burst += 1
    if self.burst >= 3 then
        self.burst = 0
        if self.overwatch_until and time.now() < self.overwatch_until then
            self.fire_t = (0.45 + math.random() * 0.3) * self.r.cadence   -- covering a mate's rush
        else
            self.fire_t = (1.0 + math.random() * 0.8) * self.r.cadence
        end
    else
        self.fire_t = 0.16
    end
    if self.shots % 24 == 0 then
        Dialogue.bark("reload", { speaker = self.key, cooldown = 10 })
        self.fire_t = 2.2
    end
end

return Op
