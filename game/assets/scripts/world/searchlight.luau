-- Watchtower searchlight (tools/world/night.py): a spot that sweeps `arc` degrees either side
-- of its authored heading, pausing at the ends like a guard working it by hand. The tower
-- crews are gone (Op02 onward the towers are automated), so the sweep never tracks anyone.
local S = {}
S.arc = 35
S.period = 14
S.phase = 0
S.pitch = -9
S.yaw = 180     -- authored heading (degrees; passed in, not read back from the quaternion)

function S:start()
    self.yaw0 = self.yaw
    self.t = self.phase * self.period
end

function S:update(dt)
    self.t += dt
    local u = math.sin(self.t / self.period * 2 * math.pi)
    -- ease toward the ends (|u|^0.6 keeps the middle quick, the ends lingering)
    local s = (u >= 0 and 1 or -1) * math.abs(u) ^ 0.6
    self.entity.rotation = vector.create(self.pitch, self.yaw0 + s * self.arc, 0)
end

return S
