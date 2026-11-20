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
-- Fighting (lib/tactics.luau): after the first burst, or when hit or caught in the open, a
-- contractor dashes to real cover (a trunk, rock, log, vehicle or fold in the ground that blocks a
-- line from the threat's eyes to a crouched chest) and fights from it: crouched between bursts,
-- standing to fire. In a group, one contractor at a time swings wide to flank. When the target
-- breaks line of sight they put a few bursts into the last known position before searching, and a
-- search sweeps several points around it instead of standing on one spot.
--
-- Mission hooks: e.parley = true holds fire (and the squad holds theirs) while someone talks; a
-- hit breaks it. e:surrender() kneels without a stun. e:retreat(points) walks off under parley.
local Game = require("scripts/lib/game")
local Combat = require("scripts/lib/combat")
local Actor = require("scripts/lib/actor")
local Squad = require("scripts/lib/squad")
local Dialogue = require("scripts/lib/dialogue")
local Tactics = require("scripts/lib/tactics")

local E = {}
E.patrol = ""
E.voice = ""
E.alert = false
E.group = ""
E.stun = 60
E.surface = "auto"     -- footstep set: auto (ray down) or dirt/grass/gravel/mud/concrete/metal/wood
E.accuracy = 1.0
E.dormant = false

local groups = {}
local group_flank = {}   -- group name -> time before which nobody else in it starts a flank
local groups_scene = nil
local function group_of(name)
    local cur = scene.current()
    if cur ~= groups_scene then groups = {}; group_flank = {}; groups_scene = cur end
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
        self.dlg = {
            entity = self.entity, voice = a.voice, face = nil,
            look_at = function(p) a:look_at(p, 0.6) end,
            can_speak = function() return (not self.down) or self.surrendered end,
        }
        Dialogue.register(self.voice, self.dlg)
    end
    self.mag_left = 18 + math.random(0, 12)   -- rounds before this contractor has to change cells
    self.think_t = math.random() * 0.5
    self.hit_t = -100
end

-- Voices are shared by several contractors (greyline1/greyline2), so the speaker claims the voice
-- key before barking: the line then plays from this contractor's head, not a colleague's. Barks
-- beyond earshot are skipped instead of falling back to the radio bus.
function E:say(kind, chance, ttl)
    if self.voice == "" or self.down or not self.dlg then return false end
    if chance and math.random() > chance then return false end
    local cam = Game.camera
    if cam and vector.magnitude(self.entity.world_position - cam.world_position) > 40 then return false end
    Dialogue.register(self.voice, self.dlg)
    return Dialogue.bark(kind, { prefix = "grey_", speaker = self.voice, cooldown = 7, ttl = ttl })
end

-- A group mate already sweeping the spot this contractor is heading for.
function E:spot_lead()
    if self.group == "" or not self.noise_pos then return nil end
    for _, o in group_of(self.group) do
        if o ~= self and not o.down and o.state == "alert" and o.sweep and o.noise_pos
            and flat_dist(o.noise_pos, self.noise_pos) < 6 then return o end
    end
    return nil
end

-- A group mate currently walking to a search point nearby (the one this contractor covers).
function E:sweep_mate()
    if self.group == "" then return nil end
    for _, o in group_of(self.group) do
        if o ~= self and not o.down and o.state == "alert" and o.sweep_moving and o.sweep
            and flat_dist(o.entity.position, self.entity.position) < 18 then return o end
    end
    return nil
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
    self.sweep_moving, self.held, self.hold_t = nil, nil, 0
    -- more of the same noise (footsteps, a burst) refines the spot instead of restarting the search
    if self.state == "alert" and self.noise_pos and flat_dist(pos, self.noise_pos) < 5 then
        self.noise_pos = pos
        return
    end
    if self.state == "patrol" and not self.dormant then self:say("alert", 0.7) end
    self.state = "alert"
    self.st = -(delay or 0)
    self.noise_pos = pos
    self.sweep = nil
    self.tac_goal, self.in_cover = nil, nil
    self.actor:halt()   -- stop and listen; the walk to the new spot starts after the delay
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
    self.hit_t = time.now()
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
        self:say("hit", 0.55)
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
        self.tac_goal, self.in_cover, self.flanked = nil, nil, false
        self.cover_t = time.now() + 0.8 + math.random() * 1.2   -- earliest cover decision
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
            -- a mate is already checking this spot: hold short of it and cover him instead of
            -- walking into the same bushes (one searches, one covers)
            local lead = not self.sweep and self:spot_lead()
            if lead then
                if flat_dist(e.position, self.noise_pos) < 11 then
                    if a.goal then a:halt() end
                    a.focus = lead.sweep[math.max(1, lead.sweep_i)] or lead.entity.position
                    if not self.held then
                        self.held = true
                        self:say("covering", 0.5, 1.4)
                        Game.emit("enemy_sweep_cover", e, lead.entity)
                    end
                end
            elseif self.held and not self.sweep then
                -- the mate finished (or went down): done here too
                self.held = nil
                self.st = 100
            end
            if lead and flat_dist(e.position, self.noise_pos) < 11 then
                -- covering: nothing else to do this frame
            elseif self.st > 0.8 and not a.goal and not self.sweep and flat_dist(e.position, self.noise_pos) > 3 then
                local p = nav.available() and nav.nearest(self.noise_pos, vector.create(3, 4, 3)) or self.noise_pos
                self.actor:set_speed(2.2)
                a:go(p)
            elseif self.st > 0.8 and not self.sweep and (a:arrived() or flat_dist(e.position, self.noise_pos) <= 3) then
                -- reached the spot: sweep a few points around it, pausing to look at each
                self.sweep = Tactics.search_points(self.noise_pos, 3, 7)
                self.sweep_i, self.sweep_wait = 0, 1.2 + math.random()
                a:halt()
                Game.emit("enemy_sweep", e, #self.sweep)
            end
            if self.sweep then
                local g = self.sweep_moving and self.sweep[self.sweep_i] or nil
                self.leg_t = (self.leg_t or 0) + dt
                if g and (a:arrived() or flat_dist(e.position, g) < 1.0 or self.leg_t > 6) then
                    g = nil
                    self.sweep_wait = 1.0 + math.random() * 1.5
                    self.sweep_moving = nil
                    a:halt()
                end
                if not g then
                    self.sweep_wait -= dt
                    -- look around while paused
                    a.focus = e.position + vector.create(math.sin(self.st * 0.9 + self.actor.seed), 0, math.cos(self.st * 0.9 + self.actor.seed)) * 6
                    -- searching in pairs: while a mate walks to his next point, hold and watch over him
                    -- (one moves, one covers), for up to 6 s
                    local mate = self:sweep_mate()
                    if mate and self.sweep_wait <= 0 and (self.hold_t or 0) < 6 then
                        self.hold_t = (self.hold_t or 0) + dt
                        a.focus = mate.sweep[mate.sweep_i] or mate.entity.position
                        if not self.held then
                            self.held = true
                            Game.emit("enemy_sweep_cover", e, mate.entity)
                        end
                    elseif self.sweep_wait <= 0 and self.sweep_i < #self.sweep then
                        self.hold_t, self.leg_t = 0, 0
                        self.sweep_moving = true
                        self.sweep_i += 1
                        self.actor:set_speed(1.8)
                        a:go(self.sweep[self.sweep_i])
                        if self.sweep_i == 2 then self:say("search", 0.35) end
                    end
                else
                    a.focus = g
                end
            end
            local give_up = self.sweep and (self.sweep_i >= #self.sweep and self.sweep_wait <= 0 or self.st > 30)
                or (not self.sweep and not lead and self.st > (a.goal and 20 or 9))
            if give_up then
                self.sweep, self.sweep_moving = nil, nil
                self:say("calm", 0.6)
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
            self:think(dt, tgt)
            if self.st >= self.react and not self.tac_goal then self:fire(dt, tgt, tp) end
            -- keep a fighting distance (only when not already moving with a purpose)
            if not self.tac_goal and not self.in_cover then
                local dist = flat_dist(e.position, tgt.position)
                if dist > 22 and not a.goal then a:go(tgt.position) elseif dist < 18 and a.goal then a:halt() end
            end
        else
            self.lost_t = (self.lost_t or 0) + dt
            if self.tac_goal then self:think(dt, nil) end
            -- they just ducked out of sight: keep their heads down for a moment
            if self.last_seen and self.lost_t > 0.35 and self.lost_t < 2.4 and not self.tac_goal and (self.bursts or 0) > 0 then
                local jitter = vector.create((math.random() - 0.5) * 2.5, 0.6 + math.random() * 0.8, (math.random() - 0.5) * 2.5)
                a.focus = self.last_seen
                self:fire(dt, nil, self.last_seen + jitter)
            end
            if self.lost_t > 3.0 and self.last_seen then
                self.tac_goal, self.in_cover = nil, nil
                if not self:say("lost", 0.5) then self:say("search") end
                self.state = "alert"
                self.st = 0.5
                self.noise_pos = self.last_seen
            end
        end
    end
    local crouch
    if self.state == "engage" and self.in_cover then
        -- duck between bursts and while changing cells, stand to shoot
        crouch = self.fire_t > 0.45
    else
        crouch = self.state == "engage" and not a.goal and (self.actor.seed % 2 == 0)
    end
    self.crouching = crouch
    a:param("crouch", crouch)
    a:update(dt)
end

-- Group members currently flanking (one at a time per group).
local function flanker_in(group, me)
    for _, o in group do
        if o ~= me and not o.down and o.tac_kind == "flank" and o.tac_goal then return true end
    end
    return false
end

local function engaged_in(group)
    local n = 0
    for _, o in group do if not o.down and o.state == "engage" then n += 1 end end
    return n
end

-- Tactical decisions while engaged, a few times a second: take cover, relocate when the cover
-- stops covering, flank, and arrive. tgt may be nil while moving after losing sight.
function E:think(dt, tgt)
    local a, e = self.actor, self.entity
    local now = time.now()
    -- moving: arrive, or give up a run that takes too long
    if self.tac_goal then
        if a:arrived() or flat_dist(e.position, self.tac_goal) < 0.9 or now > self.tac_until then
            local kind = self.tac_kind
            a:halt()
            self.in_cover = self.tac_goal
            self.tac_goal, self.tac_kind = nil, nil
            self.actor:set_speed(3.0)
            self.check_t = now + 1.5
            local cov = self.covered_by
            if cov then cov.overwatch_for, cov.overwatch_until = nil, 0 end
            self.covered_by = nil
            Game.emit("enemy_in_cover", e, kind)
            Game.emit("enemy_bound", e, kind, { dur = now - (self.tac_t0 or now), by = cov and cov.entity or nil })
            if kind ~= "sidestep" then self:say("set", 0.45, 1.5) end
            -- a flank is several short rushes, not one long run in the open
            if kind == "flank" and self.flank_goal then
                self.flank_n = (self.flank_n or 0) + 1
                if flat_dist(e.position, self.flank_goal) < 3 or self.flank_n >= 4 then
                    self.flank_goal = nil
                else
                    self.flank_next = now + 1.0 + math.random() * 1.0
                end
            end
        end
        return
    end
    -- next rush of a flank, after a breath (and a burst) in cover
    if self.flank_goal and now >= (self.flank_next or 0) and tgt then
        if self:mate_moving() and now - self.hit_t > 1.5 then self.flank_next = now + 0.8; return end
        self:bound_to(self.flank_goal, tgt.position, "flank")
        return
    end
    self.think_t -= dt
    if self.think_t > 0 or not tgt or now < (self.cover_t or 0) then return end
    self.think_t = 0.45 + math.random() * 0.3
    local threat = tgt.position
    local eye = threat + vector.create(0, 1.55, 0)
    local group = self.group ~= "" and group_of(self.group) or nil
    -- flank: one contractor of an engaged group of two or more swings wide, once per fight
    if group and not self.flanked and engaged_in(group) >= 2 and now >= (group_flank[self.group] or 0)
        and not flanker_in(group, self) and (self.actor.seed % 3 ~= 0 or (self.bursts or 0) >= 3) then
        self.flanked = true
        group_flank[self.group] = now + 25
        local rel = e.position - threat
        local side = (rel.x * 0.37 + rel.z * 0.93 > 0) and 1 or -1
        local fp = Tactics.flank_point(e.position, threat, side)
        if fp then
            local c = Tactics.find_cover(fp, threat, { radius = 6, samples = 12, min_threat = 7, ignore = e })
            self.flank_goal, self.flank_n = c or fp, 0
            self:bound_to(self.flank_goal, threat, "flank")
            self:say("flank", 0.9, 3.5)
            Game.emit("enemy_flanking", e, threat)
            return
        end
    end
    -- in cover: is it still cover? (the threat may have moved round it)
    if self.in_cover then
        if now < (self.check_t or 0) then return end
        self.check_t = now + 1.4 + math.random() * 0.8
        local hit_recent = now - self.hit_t < 1.0
        if Tactics.exposed(eye, self.in_cover, e) or (hit_recent and math.random() < 0.35) then
            self.in_cover = nil
        else
            return
        end
    end
    -- in the open: take cover after a burst or two, at once if hit
    local hit_recent = now - self.hit_t < 1.5
    if not hit_recent and (self.bursts or 0) < 1 and (self.blocked_n or 0) < 3 then return end
    if not Tactics.exposed(eye, e.position, e) and Tactics.can_peek(eye, e.position, e) and (self.blocked_n or 0) == 0 then
        -- already behind something where we stand, and can shoot over it
        self.in_cover = e.position
        self.check_t = now + 1.5
        return
    end
    -- one moves while the other covers: wait for a mate's rush to finish unless rounds are landing
    if not hit_recent and self:mate_moving() then
        self.cover_t = now + 0.7
        return
    end
    local avoid = {}
    for _, o in group or {} do
        if o ~= self and (o.in_cover or o.tac_goal) then table.insert(avoid, o.tac_goal or o.in_cover) end
    end
    if (self.blocked_n or 0) > 0 then table.insert(avoid, e.position) end
    local c = Tactics.find_cover(e.position, threat, { radius = 9, ignore = e, avoid = avoid })
    self.blocked_n = 0
    if c then
        self:move_tactical(c, "cover", 4.5)
        self:say("cover", hit_recent and 0.7 or 0.4, 3.0)
    elseif self.sidestep then
        -- no cover around, but the shot is blocked: step out sideways
        local p = self.sidestep
        self.sidestep = nil
        self:move_tactical(p, "sidestep", 3)
    else
        self.cover_t = now + 2.5   -- nothing around; try again later (or after moving)
    end
end

-- A group mate in the middle of a rush.
function E:mate_moving()
    if self.group == "" then return false end
    for _, o in group_of(self.group) do
        if o ~= self and not o.down and o.tac_goal then return true end
    end
    return false
end

-- One rush of a flank: at most ~14 m (3-5 s at a run), ending behind cover where there is some.
function E:bound_to(goal, threat, kind)
    local pos = self.entity.position
    local d = goal - pos
    local len = math.sqrt(d.x * d.x + d.z * d.z)
    local p = goal
    if len > 14 then
        local mid = Tactics.ground(pos + vector.create(d.x, 0, d.z) * (12 / len), self.entity) or goal
        p = Tactics.find_cover(mid, threat, { radius = 4, samples = 8, ignore = self.entity }) or mid
    end
    self:move_tactical(p, kind, 5)
end

-- Rushes are covered (FM 3-21.8 bounding overwatch, "I'm up, he sees me, I'm down"): a set mate who
-- can shoot steps up his fire on the threat while this one moves, and the two call it.
function E:move_tactical(p, kind, limit)
    self.tac_goal, self.tac_kind = p, kind
    self.tac_t0 = time.now()
    self.tac_until = time.now() + (limit or 5)
    self.covered_by = nil
    if self.group ~= "" and kind ~= "sidestep" then
        local best, bd = nil, 30
        for _, o in group_of(self.group) do
            if o ~= self and not o.down and o.state == "engage" and not o.tac_goal and not o.overwatch_for then
                local dd = flat_dist(o.entity.position, self.entity.position)
                if dd < bd then best, bd = o, dd end
            end
        end
        if best then
            best.overwatch_for, best.overwatch_until = self, time.now() + (limit or 5) + 0.5
            best.cover_t = math.max(best.cover_t or 0, time.now() + (limit or 5))
            best.fire_t = math.min(best.fire_t, 0.3)
            self.covered_by = best
            Game.emit("enemy_overwatch", best.entity, self.entity)
            self:say("moving", 0.8, 1.4)
            best.say_cover_t = time.now() + 0.9
        end
    end
    self.in_cover = nil
    self.burst = 0
    self.actor:set_speed(kind == "flank" and 3.4 or 3.8)
    self.actor:go(p)
end

function E:fire(dt, tgt, tp)
    if self.flinch and self.flinch > 0 then return end
    self.fire_t -= dt
    if self.fire_t > 0 then return end
    if self.mag_left <= 0 then
        -- changing cells: a real pause in the fire the squad (and the player) can use
        self.mag_left = 24 + math.random(0, 8)
        self.fire_t = 2.4 + math.random() * 0.8
        self.burst = 0
        self:say("reload", 0.7)
        Game.emit("enemy_reloading", self.entity)
        return
    end
    -- do not empty a magazine into the rock in front of you: after a few blocked attempts, move
    local muzzle = self.actor:muzzle_ray()
    local reach = vector.magnitude(tp - muzzle)
    if not Tactics.clear_shot(muzzle, tp, self.entity, math.min(6, reach * 0.5)) then
        self.fire_t = 0.35
        self.blocked_n = (self.blocked_n or 0) + 1
        if self.blocked_n >= 3 then
            local d = tp - self.entity.position
            local side = vector.normalize(vector.create(-d.z, 0, d.x)) * ((self.actor.seed % 2 == 0) and 2.5 or -2.5)
            self.sidestep = Tactics.ground(self.entity.position + side, self.entity)
            self.in_cover = nil
            self.cover_t, self.think_t = 0, 0
        end
        return
    end
    self.blocked_n = 0
    self.mag_left -= 1
    local dist = vector.magnitude(tp - self.entity.position)
    local moving = tgt ~= nil and vector.magnitude(tgt.velocity or vector.create(0, 0, 0)) > 1.5
    local is_player = tgt ~= nil and Game.player ~= nil and tgt.id == Game.player.id
    -- generous spread so the player has time to react; first burst is a warning
    local spread = (3.2 + dist * 0.12 + (moving and 2.2 or 0)) / self.accuracy
    if (self.bursts or 0) == 0 then spread *= 1.8 end
    if tgt == nil then spread *= 1.5 end   -- suppressing a last known position
    Squad.shoot(self, tp, { spread = spread, amount = is_player and 7 or 12, team = "enemy", volume = 0.5,
                            pitch = 0.82 + math.random() * 0.06 })
    self.burst += 1
    if self.burst >= 3 then
        self.burst = 0
        self.bursts = (self.bursts or 0) + 1
        local covering = self.overwatch_for and time.now() < (self.overwatch_until or 0)
        if self.say_cover_t and time.now() >= self.say_cover_t then
            self.say_cover_t = nil
            if covering then self:say("covering", 0.8, 1.4) end
        elseif self.bursts == 2 or self.bursts % 5 == 0 or (tgt == nil and self.bursts % 2 == 0) then self:say("suppress", 0.45) end
        -- covering a mate's rush: short pauses, keep the threat's head down
        self.fire_t = covering and (0.45 + math.random() * 0.3) or (1.2 + math.random() * 0.8)
    else
        self.fire_t = 0.14
    end
end

return E
