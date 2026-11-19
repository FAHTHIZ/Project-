-- Smoothly follows the entity named `target`, keeping the starting offset.
local Follow = {}
Follow.target = "Player"
Follow.smoothing = 4 -- higher follows more tightly

function Follow:start()
    self.subject = scene.find(self.target)
    if self.subject then
        self.offset = self.entity.position - self.subject.position
    end
end

function Follow:update(dt)
    if not self.subject or not self.subject.valid then return end
    local goal = self.subject.position + self.offset
    local k = 1 - math.exp(-self.smoothing * dt)
    self.entity.position = self.entity.position + (goal - self.entity.position) * k
    self.entity:look_at(self.subject.position)
end

return Follow
