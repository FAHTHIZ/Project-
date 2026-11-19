-- Greyline contractor. Patrols between waypoints, turns toward noises, engages what it sees after
-- a human reaction delay with short bursts, searches the last known position, and drops to its
-- knees with hands up when its stun pool is spent (non-lethal; no injury is depicted).
--
-- Script properties:
--   patrol   "x,z;x,z;..." waypoints (empty = stand guard facing the spawn yaw)
--   voice    "greyline1" / "greyline2" / "" - dialogue speaker key for this contractor's barks
--   alert    start alerted (ambush groups)
--   group    name shared by contractors that alert each other
--   stun     stun pool (Sorn has a deeper one)
--   dormant  start out of the level; the mission calls e:wake(pos, yaw) when they arrive
--
-- Mission hooks: e.parley = true holds fire (and the squad holds theirs) while someone talks; a
-- hit breaks it. e:surrender() kneels without a stun. e:retreat(points) walks off under parley.
local Game = require("scripts/lib/game")
local Combat = require("scripts/lib/combat")
local Actor = require("scripts/lib/actor")
local Squad = require("scripts/lib/squad")
local Dialogue = require("scripts/lib/dialogue")

local E = {}
E.patrol = ""
E.voice = ""
E.alert = false
E.group = ""
E.stun = 60
E.surface = "dirt"
E.accuracy = 1.0
E.dormant = false

local groups = {}
local groups_scene = nil
local function group_of(name)
    local cur = scene.current()
    if cur ~= groups_scene then groups = {}; groups_scene = cur end
    groups[name] = groups[name] or {}
    return groups[name]
end

local function parse_points(s)
    local pts = {}
    for pair in string.gmatch(s, "[^;]+") do
        local x, z = string.match(pair, "([%-%d%.]+)%s*,%s*([%-%d%.]+)")
        if x then table.insert(pts, vector.create(tonumber(x), 0, tonumber(z))) end
    end
    return pts
end

local function flat_dist(a, b)
    local d = a - b
    return math.sqrt(d.x * d.x + d.z * d.z)
end

function E:start()
    self.actor = Actor.new(self.entity)
    self.actor.surface = self.surface
    self.points = parse_points(self.patrol)
    self.pi = 1
    self.state = self.alert and "alert" or "patrol"
    self.st = 0
    self.pool = self.stun
    self.down = false
    self.react = 0
    self.fire_t = 0
    self.burst = 0
    self.wait = 1 + math.random() * 2
    self.home = self.entity.position
    self.home_yaw = Actor.yaw_of(self.entity)
    self.actor:set_speed(1.6)
    if self.group ~= "" then table.insert(group_of(self.group), self) end
    Squad.register_enemy(self.entity, self)
    Combat.register(self.entity, function(info) return self:on_hit(info) end)
    Combat.on_noise(function(pos, radius, source) self:on_noise(pos, radius, source) end)
    self.parley = false
    if self.dormant then
        self.wake_home = self.entity.position
        self.entity.position = vector.create(self.home.x, -400, self.home.z)
        self.entity:set("Perceptible", { enabled = false })
    end
    if self.voice ~= "" then
        local a = self.actor
        Dialogue.register(self.voice, {
            entity = self.entity, voice = a.voice, face = nil,
            look_at = function(p) a:look_at(p, 0.6) end,
            can_speak = function() return (not self.down) or self.surrendered end,
        })
    end
end

function E:say(kind)
    if self.voice == "" or self.down then return end
    Dialogue.bark(kind, { prefix = "grey_", speaker = self.voice, cooldown = 7 })
end

function E:alert_group(pos)
    if self.group == "" then return end
    for _, o in group_of(self.group) do
        if o ~= self and not o.down and o.state == "patrol" then
            o:investigate(pos, 0.4 + math.random() * 0.5)
        end
    end
end

function E:investigate(pos, delay)
    if self.down or self.state == "engage" then return end
    self.state = "alert"
    self.st = -(delay or 0)
    self.noise_pos = pos
end

function E:on_noise(pos, radius, source)
    if self.down or not self.entity.valid then return end
    if source and source.valid and source.id == self.entity.id then return end
    if source and Squad.state().enemies[source.id] then return end -- own team's shots
    local d = vector.magnitude(pos - self.entity.position)
    if d < radius + 4 then self:investigate(pos, 0.5 + math.random() * 0.4) end
end

function E:on_hit(info)
    if self.down or self.dormant then return false end
    if info.team == "enemy" then return false end
    if self.parley and not self.retreating then
        self.parley = false
        Game.emit("parley_broken", self.entity)
    end
    self.pool -= info.amount
    self.actor:look_at(info.source and info.source.valid and info.source.world_position + vector.create(0, 1.5, 0)
        or self.entity.position, 1.0)
    if self.state ~= "engage" then
        self.state = "alert"
        self.st = 0.6
        self.noise_pos = info.source and info.source.valid and info.source.position or self.entity.position
    end
    if self.pool <= 0 then
        self:go_down(info)
    else
        self.flinch = 0.25
    end
    return true
end

function E:go_down(info)
    self.down = true
    self.state = "down"
    self.actor:halt()
    self.actor.aim_want = 0
    self.actor:param("stunned", true)
    self.actor:param("crouch", false)
    self.entity:set("Perception", { line_of_sight = false })
    self.entity:set("Perception", { sight_range = 0.1 })
    self.entity:set("Perceptible", { enabled = false })
    Combat.stats.downs += 1
    Game.emit("enemy_down", self.entity, info and info.source)
    -- the other side reacts; the squad confirms
    local by_player = info and info.source and Game.player and info.source.id == Game.player.id
    if by_player or math.random() < 0.6 then Dialogue.bark("down", { cooldown = 5 }) end
    for _, o in self.group ~= "" and group_of(self.group) or {} do
        if o ~= self and not o.down and o.voice ~= "" then o:say("down"); break end
    end
end

-- Gives up without being stunned (mission beats: the Op01 patrol, Sorn). Same kneeling, hands-up
-- pose as a stun, but the contractor can still talk.
function E:surrender()
    if self.down then return end
    self.surrendered = true
    self:go_down(nil)
    Game.emit("enemy_surrender", self.entity)
end

function E:wake(pos, yaw)
    self.dormant = false
    local p = pos or self.wake_home
    self.actor:place(p, yaw)
    self.home = p
    self.entity:set("Perceptible", { enabled = true })
end

function E:retreat(points)
    self.parley = true
    self.retreating = true
    self.state = "patrol"
    self.points = {}
    self.actor.aim_want = 0
    self.actor:set_speed(3.4)
    self.retreat_pts = points
    self.retreat_i = 1
    self.actor:go(points[1])
end

function E:target()
    local p = self.entity:perception()
    if not p then return nil, nil end
    if p.target and p.target.valid and p.visible then return p.target, p end
    return nil, p
end

function E:update(dt)
    if Game.paused then return end
    local a = self.actor
    local e = self.entity
    self.st += dt
    if self.dormant then return end
    if self.down then
        a.focus = nil
        a:update(dt)
        return
    end
    if self.retreating then
        local g = self.retreat_pts[self.retreat_i]
        if g and (a:arrived() or flat_dist(e.position, g) < 1.0) then
            self.retreat_i += 1
            g = self.retreat_pts[self.retreat_i]
            if g then a:go(g) end
        end
        if not g then
            self.retreating = false
            Game.emit("enemy_retreated", self.entity)
        end
        a.focus = nil
        a:update(dt)
        return
    end
    if self.flinch and self.flinch > 0 then self.flinch -= dt end
    local tgt, per = nil, nil
    if not Game.cinematic and not self.parley then tgt, per = self:target() end
    if self.parley then
        a.aim_want = 0.5
        a.focus = Game.player and Game.player.position or a.focus
        a:update(dt)
        return
    end
    if tgt and self.state ~= "engage" then
        self.state = "engage"
        self.st = 0
        self.react = 0.6 + math.random() * 0.4
        a:halt()
        self:say("contact")
        self:alert_group(tgt.position)
        self.actor:set_speed(3.0)
    end
    if self.state == "patrol" then
        a.aim_want = 0
        if #self.points == 0 then
            a.focus = self.home + vector.create(math.sin(math.rad(self.home_yaw)), 0, math.cos(math.rad(self.home_yaw))) * 5
            if flat_dist(e.position, self.home) > 0.8 and not a.goal then a:go(self.home) end
        else
            local p = self.points[self.pi]
            if a.goal == nil then
                self.wait -= dt
                if self.wait <= 0 then
                    a:go(p)
                end
            elseif a:arrived() or flat_dist(e.position, p) < 0.6 then
                a:halt()
                self.pi = self.pi % #self.points + 1
                self.wait = 2 + math.random() * 2.5
                if math.random() < 0.25 then self:say("idle") end
            end
            a.focus = nil
        end
    elseif self.state == "alert" then
        if self.st >= 0 and self.noise_pos then
            a.aim_want = 0.7
            a.focus = self.noise_pos
            if self.st > 0.8 and not a.goal and flat_dist(e.position, self.noise_pos) > 3 then
                local p = nav.available() and nav.nearest(self.noise_pos, vector.create(3, 4, 3)) or self.noise_pos
                self.actor:set_speed(2.2)
                a:go(p)
            end
            if self.st > 9 then
                self:say("search")
                self.state = "patrol"
                a:halt()
                self.actor:set_speed(1.6)
            end
        end
    elseif self.state == "engage" then
        a.aim_want = 1
        if tgt and tgt.valid then
            self.last_seen = tgt.position
            self.lost_t = 0
            a.focus = tgt.position
            local tp = tgt.world_position + vector.create(0, 1.2, 0)
            local muzzle = a:muzzle_ray()
            local d = tp - muzzle
            a.aim_pitch = math.deg(math.atan2(d.y, math.sqrt(d.x * d.x + d.z * d.z)))
            if self.st >= self.react then self:fire(dt, tgt, tp) end
            -- keep a fighting distance
            local dist = flat_dist(e.position, tgt.position)
            if dist > 22 and not a.goal then a:go(tgt.position) elseif dist < 18 and a.goal then a:halt() end
        else
            self.lost_t = (self.lost_t or 0) + dt
            if self.lost_t > 1.5 and self.last_seen then
                self:say("search")
                self.state = "alert"
                self.st = 0.5
                self.noise_pos = self.last_seen
            end
        end
    end
    a:param("crouch", self.state == "engage" and not a.goal and (self.actor.seed % 2 == 0))
    a:update(dt)
end

function E:fire(dt, tgt, tp)
    if self.flinch and self.flinch > 0 then return end
    self.fire_t -= dt
    if self.fire_t > 0 then return end
    local dist = vector.magnitude(tp - self.entity.position)
    local moving = vector.magnitude(tgt.velocity or vector.create(0, 0, 0)) > 1.5
    local is_player = Game.player and tgt.id == Game.player.id
    -- generous spread so the player has time to react; first burst is a warning
    local spread = (3.2 + dist * 0.12 + (moving and 2.2 or 0)) / self.accuracy
    if (self.bursts or 0) == 0 then spread *= 1.8 end
    Squad.shoot(self, tp, { spread = spread, amount = is_player and 7 or 12, team = "enemy", volume = 0.5,
                            pitch = 0.82 + math.random() * 0.06 })
    self.burst += 1
    if self.burst >= 3 then
        self.burst = 0
        self.bursts = (self.bursts or 0) + 1
        self.fire_t = 1.2 + math.random() * 0.8
    else
        self.fire_t = 0.14
    end
end

return E
