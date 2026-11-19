-- Per-scene ensemble runner (one "Ensemble" entity per scene): advances the dialogue scheduler
-- and the squad services (orders, shared NPC tracers) once per frame.
local Dialogue = require("scripts/lib/dialogue")
local Squad = require("scripts/lib/squad")

local R = {}

function R:start()
    Dialogue.state()
    Squad.state()
end

function R:update(dt)
    Dialogue.update(dt)
    Squad.update(dt)
end

return R
