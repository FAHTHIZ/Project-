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

function N:start()
    self.key = string.lower(self.who)
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
    a:update(dt)
end

return N
