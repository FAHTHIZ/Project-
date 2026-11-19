-- A companion that follows `target` over the navmesh. The entity has a NavAgent and a
-- CharacterController: set_destination() plans a path around the steps, crates and pillars and
-- the character mover walks it. Its child "Robot" model's animation controller blends Idle, Walk
-- and Run by the "speed" parameter.
local Buddy = {}
Buddy.target = "Player"
Buddy.follow_distance = 2.0 -- stays about this far from the target
Buddy.repath_distance = 0.75 -- re-plans when the target moved this far

function Buddy:start()
    self.subject = scene.find(self.target)
    self.robot = self.entity:find_child("Robot")
end

function Buddy:update(dt)
    if self.subject and self.subject.valid then
        local goal = self.subject.position
        local here = self.entity.position
        local offset = vector.create(goal.x - here.x, 0, goal.z - here.z)
        local distance = vector.magnitude(offset)
        if distance > self.follow_distance then
            -- Walk to a point short of the target so the two never bump into each other.
            local spot = goal - vector.normalize(offset) * (self.follow_distance * 0.75)
            if not self.goal or vector.magnitude(spot - self.goal) > self.repath_distance then
                if self.entity:set_destination(spot) then self.goal = spot end
            end
        elseif self.goal and distance < self.follow_distance * 0.6 then
            self.entity:stop()
            self.goal = nil
        end
    end
    if not self.robot then return end
    local v = self.entity.velocity
    -- The companion is about half size: its legs cover half the ground per step.
    self.robot:set_anim_param("speed", vector.magnitude(vector.create(v.x, 0, v.z)) * 1.8)
end

return Buddy
