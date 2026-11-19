-- A sentry turret driven by assets/ai/sentry.vbt. The behaviour tree calls these methods as
-- tasks (returning "running", "success" or "failure"): scan sweeps the turret while nothing is in
-- sight; once its Perception writes a `target` to the blackboard, track turns to face it.
local Sentry = {}
Sentry.sweep = 50 -- degrees either side of the starting heading
Sentry.scan_speed = 35 -- degrees per second while scanning
Sentry.turn_speed = 220 -- degrees per second while tracking

function Sentry:start()
    self.home = self.entity.rotation.y
    self.yaw = self.home
    self.dir = 1
    self.head = self.entity:find_child("Head")
end

function Sentry:face(yaw)
    self.yaw = yaw
    self.entity.rotation = vector.create(0, yaw, 0)
end

function Sentry:scan(dt, first)
    if first and self.head then self.head:set_emissive(vector.create(0.2, 0.6, 1.0), 1.5) end
    if self.yaw > self.home + self.sweep then self.dir = -1 elseif self.yaw < self.home - self.sweep then self.dir = 1 end
    self:face(self.yaw + self.dir * self.scan_speed * dt)
    return "running"
end

function Sentry:track(dt, first)
    local target = self.entity:bb_get("target")
    if not target or not target.valid then return "failure" end
    if first and self.head then self.head:set_emissive(vector.create(1.0, 0.15, 0.1), 3) end
    -- Perception looks along +Z, so the heading toward the target is atan2(dx, dz).
    local d = target.position - self.entity.position
    local want = math.deg(math.atan2(d.x, d.z))
    local diff = ((want - self.yaw + 540) % 360) - 180
    local step = self.turn_speed * dt
    self:face(self.yaw + math.clamp(diff, -step, step))
    return "running"
end

return Sentry
