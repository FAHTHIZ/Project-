-- Per-scene ensemble runner (one "Ensemble" entity per scene): advances the dialogue scheduler
-- the squad services (orders, shared NPC tracers) and squad reactions (lib/reactions.luau) once per frame.
local Dialogue = require("scripts/lib/dialogue")
local Squad = require("scripts/lib/squad")
local Reactions = require("scripts/lib/reactions")

local R = {}

function R:start()
    Dialogue.state()
    Squad.state()
    Reactions.start()
end

function R:update(dt)
    Dialogue.update(dt)
    Squad.update(dt)
    Reactions.update(dt)
end

return R
