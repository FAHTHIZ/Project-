-- Plays a positional impact sound when the crate hits something hard enough.
local Crate = {}
Crate.sound = "audio/impact.wav"
Crate.min_speed = 1.5 -- m/s before impact
Crate.cooldown = 0.12

function Crate:start()
    self.speed = 0
    self.last = -1
end

function Crate:update(dt)
    -- Runs before the physics step, so this is the speed going into any contact this frame.
    self.speed = vector.magnitude(self.entity.velocity)
end

function Crate:on_collision_enter(other, info)
    local now = time.now()
    if self.speed >= self.min_speed and now - self.last >= self.cooldown then
        self.last = now
        audio.play(self.sound, { position = info.point, volume = math.min(1, self.speed / 6),
                                 pitch = 0.9 + math.random() * 0.2 })
    end
end

return Crate
