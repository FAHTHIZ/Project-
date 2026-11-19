-- Idle squad chatter on quiet walks (story bible rev 2, "squad between beats").
-- Mission scripts call Chatter.update(dt, stage_name, outdoors) every frame. A short exchange
-- plays when the stage is listed as a quiet walk, nobody is talking, no awake contractor is
-- within 50 m, the player is actually moving and at least `gap` seconds of quiet have passed.
-- Every exchange plays at most once per campaign run (Game.chatter_used), and only when all of
-- its speakers are present in the scene, so a missing operator never "talks" from nowhere.
local Game = require("scripts/lib/game")
local Dialogue = require("scripts/lib/dialogue")
local Squad = require("scripts/lib/squad")

local Chatter = {}

-- id list, speakers (Dialogue keys), outdoor-only (rain / lightning lines)
Chatter.GROUPS = {
    { ids = { "chat_06a", "chat_06b" }, who = { "echo", "anchor" }, outdoor = true },
    { ids = { "chat_01a", "chat_01b", "chat_01c" }, who = { "tally", "patch", "echo" } },
    { ids = { "chat_03a", "chat_03b", "chat_03c" }, who = { "echo", "patch", "tally" }, outdoor = true },
    { ids = { "chat_04a", "chat_04b" }, who = { "patch", "anchor" } },
    { ids = { "chat_07a", "chat_07b" }, who = { "tally", "brick" }, outdoor = true },
    { ids = { "chat_02a", "chat_02b", "chat_02c" }, who = { "anchor", "tally" } },
    { ids = { "chat_05a", "chat_05b", "chat_05c" }, who = { "tally", "brick", "patch" } },
}

-- Stages that are walks between beats (missions/kestrel.luau, missions/facility.luau).
Chatter.QUIET = {
    trail = true, relay_path = true, fence = true, op03_start = true,
    reception = true, breakers = true, stairs = true,
}

Chatter.gap = 45.0       -- seconds of quiet before the first and between exchanges
Chatter.quiet_t = 0
Chatter.last_pos = nil

local function present(key)
    local a = Dialogue.actor(key)
    return a ~= nil and a.entity ~= nil and a.entity.valid and (not a.can_speak or a.can_speak())
end

local function danger_near(p)
    for _, ctl in Squad.active_enemies() do
        local e = ctl.entity
        if e and e.valid and vector.magnitude(e.world_position - p) < 50 then return true end
    end
    return false
end

function Chatter.reset()
    Chatter.quiet_t = 0
    Chatter.last_pos = nil
end

-- Returns the group index started, or nil.
function Chatter.update(dt, stage, outdoors, talking)
    Game.chatter_used = Game.chatter_used or {}
    local pl = Game.player
    if not pl or not pl.valid then return nil end
    local p = pl.world_position
    local moving = Chatter.last_pos ~= nil and dt > 0 and vector.magnitude(p - Chatter.last_pos) / dt > 0.6
    Chatter.last_pos = p
    if not Chatter.QUIET[stage] or talking or Dialogue.busy() or danger_near(p) then
        Chatter.quiet_t = 0
        return nil
    end
    if not moving then return nil end
    Chatter.quiet_t += dt
    if Chatter.quiet_t < Chatter.gap then return nil end
    for i, g in Chatter.GROUPS do
        if not Game.chatter_used[i] and (outdoors or not g.outdoor) then
            local ok = true
            for _, k in g.who do if not present(k) then ok = false; break end end
            if ok then
                Game.chatter_used[i] = true
                Chatter.quiet_t = 0
                Dialogue.conversation(g.ids, { priority = 1, gap = 0.6 })
                Game.emit("squad_chatter", i)
                return i
            end
        end
    end
    return nil
end

return Chatter
