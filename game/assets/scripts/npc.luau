-- Civilian NPC (Ranger Hollis and others): idles, keeps an eye on people nearby, speaks through
-- the dialogue scheduler with lip sync, and can be talked to (Game.register_interactable).
--
-- Script properties:
--   who      dialogue speaker key (e.g. "hollis")
--   prompt   interaction prompt ("" = not interactable)
--   event    Game event emitted when the player interacts (e.g. "talk_hollis")
--   emotion  resting expression
local Game = require("scripts/lib/game")
local Actor = require("scripts/lib/actor")
local Dialogue = require("scripts/lib/dialogue")

local N = {}
N.who = "hollis"
N.prompt = ""
N.event = ""
N.emotion = "neutral"
N.surface = "dirt"

Game.npcs = Game.npcs or {}

function N:start()
    self.key = string.lower(self.who)
    Game.npcs[self.entity.name] = self
    self.actor = Actor.new(self.entity, #self.key * 131)
    self.actor.surface = self.surface
    if self.actor.face then self.actor.face:set_emotion(self.emotion, 9999) end
    local a = self.actor
    Dialogue.register(self.key, {
        entity = self.entity, voice = a.voice, face = a.face,
        look_at = function(p) a:look_at(p, 0.6) end,
        talk = function(on) a:talk(on) end,
    })
    if self.prompt ~= "" and Game.register_interactable then
        Game.register_interactable(self.entity, self.prompt, function()
            if self.event ~= "" then Game.emit(self.event, self.entity) end
        end)
    end
    self.glance_t = 1
end

-- Movement modes used by mission directors (Hollis guides the squad from his cabin to the ridge).
--   N:follow(dist)       keep within `dist` metres of the player, never leading into a fight
--   N:hold(point)        stand still (optionally walk to `point` first) - used when shooting starts
--   N:walk(points, done) walk a list of points in order, then call done()
--   N:hide()             step out of the scene entirely (after he withdraws at the ridge)
function N:follow(dist)
    self.mode = "follow"
    self.follow_dist = dist or 6
    self.path = nil
end

function N:hold(point)
    self.mode = "hold"
    self.path = nil
    if point then self.actor:go(point) else self.actor:halt() end
end

function N:walk(points, done)
    self.mode = "walk"
    self.path = points
    self.path_i = 1
    self.path_done = done
    if points[1] then self.actor:go(points[1]) end
end

function N:hide()
    self.mode = "hidden"
    self.actor:halt()
    self.entity.position = vector.create(0, -200, 0)
end

local function flat(a, b)
    local d = a - b
    return math.sqrt(d.x * d.x + d.z * d.z)
end

function N:update_move(dt)
    local a = self.actor
    local here = self.entity.position
    if self.mode == "follow" and Game.player then
        self.repath_t = (self.repath_t or 0) - dt
        local target = Game.player.position
        local d = flat(here, target)
        -- fell far behind (blocked by trees or rocks): catch up out of sight, behind the player
        if d > 45 and Game.player_state then
            local r = math.rad(Game.player_state.yaw or 0)
            local back = vector.create(math.sin(r), 0, math.cos(r)) * 12
            a:place(target + back + vector.create(0, 1.5, 0))
            d = 12
        end
        if d > self.follow_dist + 2 and self.repath_t <= 0 then
            self.repath_t = 0.6
            -- stop short of the player, on the near side
            local dir = (here - target)
            local m = math.max(0.01, math.sqrt(dir.x * dir.x + dir.z * dir.z))
            a:set_speed(d > 18 and 3.6 or 2.2)
            a:go(target + vector.create(dir.x / m, 0, dir.z / m) * self.follow_dist)
        elseif d < self.follow_dist - 1 and not a:arrived() then
            a:halt()
        end
        if d < 10 then a.focus = target end
    elseif self.mode == "walk" and self.path then
        local goal = self.path[self.path_i]
        if goal and flat(here, goal) < 1.2 then
            self.path_i += 1
            goal = self.path[self.path_i]
            if goal then a:go(goal) end
        end
        if not goal then
            self.path = nil
            self.mode = "hold"
            a:halt()
            local cb = self.path_done
            self.path_done = nil
            if cb then cb() end
        end
    end
end

function N:set_prompt(enabled, prompt)
    if Game.set_interactable then Game.set_interactable(self.entity, enabled, prompt) end
end

function N:update(dt)
    if Game.paused then return end
    local a = self.actor
    -- glance at the player when close
    self.glance_t -= dt
    if self.glance_t <= 0 and Game.camera then
        self.glance_t = 1.5 + math.random() * 2
        local d = vector.magnitude(Game.camera.world_position - self.entity.position)
        if d < 7 then a:look_at(Game.camera.world_position, 1.4) end
        if d < 4 then a.focus = Game.player and Game.player.position or nil end
    end
    if self.mode == "hidden" then return end
    if self.mode then self:update_move(dt) end
    a:update(dt)
end

return N
