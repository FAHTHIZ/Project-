-- Halyard Team operator (Anchor, Patch, Echo, Tally): follows the player in formation, holds or
-- moves on orders, engages Greyline contractors it can see, reacts with barks, looks at whoever
-- is talking and plays its own voice lines with lip sync. Companions are never taken out: hits
-- make them stagger and take cover for a moment.
local Game = require("scripts/lib/game")
local Combat = require("scripts/lib/combat")
local Actor = require("scripts/lib/actor")
local Squad = require("scripts/lib/squad")
local Dialogue = require("scripts/lib/dialogue")

local Op = {}
Op.who = "Anchor"
Op.role = "lead"
Op.order = "follow"     -- initial order: follow | hold
Op.engage = true        -- fires at visible enemies
Op.surface = "dirt"     -- footstep set

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
    self.entity:set("NavAgent", { speed = self.r.speed })
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

function Op:on_hit(info)
    if info.team == "squad" or (Game.player and info.source and info.source.id == Game.player.id) then
        -- friendly fire: a flinch and a look, nothing else
        self.actor:look_at(Game.camera and Game.camera.world_position or self.entity.position, 1.2)
        if self.actor.face then self.actor.face:set_emotion("surprise", 0.8) end
        return false
    end
    self.hits += 1
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
    if rec and rec.ctl and rec.ctl.down then
        -- pick another seen enemy that is still up
        for _, t in p.seen do
            local r2 = Squad.state().enemies[t.id]
            if r2 and r2.ctl and not r2.ctl.down then return t, p end
        end
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
    -- movement
    if self.mode == "follow" then
        local slot = Squad.slot_point(self.who)
        if slot then
            local d_player = Game.player and flat_dist(e.position, Game.player.position) or 0
            local d_slot = flat_dist(e.position, slot)
            local hold_fire = self.engaged and d_player < 12
            if hold_fire then
                if self.goal then a:halt(); self.goal = nil end
            else
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
                    e:set("NavAgent", { speed = want_speed })
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
    a:param("crouch", self.engaged and not self.goal and (self.r.role == "scout" or self.r.role == "lead") and
        self.stagger_t <= 0)
    a:update(dt)
end

function Op:fire(dt, tp, dist)
    if self.stagger_t > 1.5 then return end
    self.fire_t -= dt
    if self.fire_t > 0 then return end
    local spread = (2.2 + dist * 0.06) / self.r.accuracy
    local _, struck = Squad.shoot(self, tp, { spread = spread, amount = 14, team = "squad", volume = 0.5 })
    if struck then Game.emit("squad_hit", self.who) end
    self.shots += 1
    self.burst += 1
    if self.burst >= 3 then
        self.burst = 0
        self.fire_t = (1.0 + math.random() * 0.8) * self.r.cadence
    else
        self.fire_t = 0.16
    end
    if self.shots % 24 == 0 then
        Dialogue.bark("reload", { cooldown = 10 })
        self.fire_t = 2.2
    end
end

return Op
