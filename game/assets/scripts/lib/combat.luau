-- SPECIAL OPS combat services shared by weapons, targets, enemies and companions.
-- Weapons fire invented non-lethal "stun pulses": a hit reduces an abstract `stun` pool and an
-- incapacitated target simply slumps and powers down (no gore, no injury depiction).
--
--   Combat.register(entity, handler)   handler(info) -> true when the hit counted
--       info = { amount, point, normal, dir, source, zone }
--   Combat.unregister(entity)
--   Combat.apply(hit_entity, info)     walks up the parents of hit_entity to the first handler
--   Combat.ray(origin, dir, range, ignore) -> hit, handler_entity
--   Combat.noise(position, radius, source)  gunfire/footstep loudness for AI hearing
local Game = require("scripts/lib/game")

local Combat = {}

local handlers = {} -- entity id -> { entity, fn }
local handlers_scene = nil
local function check_scene()
    local cur = scene.current()
    if cur ~= handlers_scene then
        handlers = {}
        handlers_scene = cur
    end
end

function Combat.register(entity, fn)
    check_scene()
    handlers[entity.id] = { entity = entity, fn = fn }
end

function Combat.unregister(entity)
    check_scene()
    handlers[entity.id] = nil
end

function Combat.handler_of(e)
    check_scene()
    while e and e.valid do
        local h = handlers[e.id]
        if h then return h end
        e = e.parent
    end
    return nil
end

function Combat.apply(hit_entity, info)
    local h = Combat.handler_of(hit_entity)
    if not h then return false, nil end
    info.zone = info.zone or "body"
    local ok = h.fn(info)
    return ok == true, h.entity
end

function Combat.ray(origin, dir, range, ignore)
    local hit = physics.raycast(origin, dir, range, nil, ignore)
    if not hit then return nil, nil end
    local h = Combat.handler_of(hit.entity)
    return hit, h and h.entity
end

-- Sound events for perception: listeners register with Combat.on_noise(fn(pos, radius, source)).
local noise_listeners = {}
local noise_scene = nil
function Combat.on_noise(fn)
    local cur = scene.current()
    if cur ~= noise_scene then noise_listeners = {}; noise_scene = cur end
    table.insert(noise_listeners, fn)
end
function Combat.noise(pos, radius, source)
    local cur = scene.current()
    if cur ~= noise_scene then noise_listeners = {}; noise_scene = cur end
    for _, fn in noise_listeners do fn(pos, radius, source) end
end

-- Running statistics (used by the HUD diagnostics and autotests).
Combat.stats = { shots = 0, hits = 0, downs = 0 }
Game.combat = Combat

return Combat
