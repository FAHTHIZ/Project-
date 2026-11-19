-- Credits roll: scrolls the credits text upward; any button, tap or the end returns to the menu.
local Game = require("scripts/lib/game")

local C = {}
C.speed = 42 -- canvas units per second
C.length = 2300

local function find(root, name)
    for _, c in root:children() do
        if c.name == name then return c end
    end
    return nil
end

function C:start()
    Game.load_settings()
    self.roll = find(self.entity, "Credits Roll")
    self.y = 0
    self.t = 0
end

function C:back()
    if self.left then return end
    self.left = true
    local p = Game.progress()
    if p.completed and p.completed.op07 then
        p.finished = true
        Game.save_progress()
    end
    scene.load("scenes/menu.vscene")
end

function C:on_click(button, action)
    if self.t > 1.5 then self:back() end
end

function C:update(dt)
    self.t += dt
    self.y += self.speed * dt
    local r = self.roll:get("UiRect")
    r.position = { 0, -math.floor(self.y) } -- UiRect is y-down; the roll rises
    self.roll:set("UiRect", r)
    if self.t > 1.5 and (input.action_pressed("pause") or input.action_pressed("skip") or input.action_pressed("interact")) then
        self:back()
    end
    if self.y > self.length then self:back() end
end

return C
