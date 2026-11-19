-- Pop-up training target for the dev range and the prologue drill. A stun pulse drains its
-- charge; when empty it folds back, powers down and resets after `reset_time` seconds.
-- Entity: root with a box Collider (the plate) and the stun_target model as children.
local Game = require("scripts/lib/game")
local Combat = require("scripts/lib/combat")

local T = {}
T.charge = 60          -- abstract stun capacity
T.reset_time = 3.0     -- 0 = stays down
T.group = ""           -- drill group name reported in the "target_down" event

function T:start()
    self.left = self.charge
    self.down = false
    self.fold = 0
    self.t = 0
    self.base_rot = self.entity.rotation
    Combat.register(self.entity, function(info) return self:hit(info) end)
end

function T:hit(info)
    if self.down then return false end
    self.left -= info.amount
    self.flash = 0.08
    if self.left <= 0 then
        self.down = true
        self.t = 0
        Combat.stats.downs += 1
        audio.play("audio/weapons/target_down.wav", { volume = 0.7, position = self.entity.world_position, bus = "sfx" })
        Game.emit("target_down", self.entity, self.group, info.zone)
    end
    return true
end

function T:reset()
    self.down = false
    self.left = self.charge
    audio.play("audio/weapons/target_up.wav", { volume = 0.5, position = self.entity.world_position, bus = "sfx" })
end

function T:update(dt)
    self.t += dt
    if self.down and self.reset_time > 0 and self.t > self.reset_time then self:reset() end
    self.fold = Game.damp(self.fold, self.down and 1 or 0, self.down and 10 or 6, dt)
    local b = self.base_rot
    self.entity.rotation = vector.create(b.x - 82 * self.fold, b.y, b.z)
end

return T
