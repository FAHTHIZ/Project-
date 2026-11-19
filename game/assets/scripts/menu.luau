-- SPECIAL OPS main menu: continue, new campaign, operation select (unlocked chapters),
-- settings (shared settings modal) and credits. The backdrop camera drifts slowly.
local Game = require("scripts/lib/game")
local Campaign = require("scripts/lib/campaign")

local Menu = {}

local function find(root, name)
    local queue = { root }
    while #queue > 0 do
        local e = table.remove(queue, 1)
        if e.name == name then return e end
        for _, c in e:children() do table.insert(queue, c) end
    end
    return nil
end

-- Buttons carry their text on a "<name> Label" child (inset from the panel edge).
local function set_label(e, text)
    local l = find(e, e.name .. " Label")
    if l then l:set_text(text) else e:set_text(text) end
end

function Menu:start()
    Game.load_settings()
    Game.paused = false
    Game.cinematic = false
    Game.campaign = nil
    self.main = find(self.entity, "Menu Main")
    self.ops = find(self.entity, "Menu Ops")
    self.confirm = find(self.entity, "Menu Confirm")
    self.status = find(self.entity, "Menu Status")
    self.cam = scene.find("Menu Camera")
    self.cam0 = self.cam and self.cam.position
    self.t = 0
    local p = Game.progress()
    local cont = find(self.entity, "Menu Continue")
    local c = Campaign.get(p.op or "prologue")
    if cont then
        if save.available() and save.exists("campaign") and c then
            set_label(cont, "Continue: " .. c.title)
        else
            set_label(cont, "Begin campaign")
        end
    end
    for i, ch in Campaign.chapters do
        local b = find(self.entity, "Op " .. ch.id)
        if b then
            local open = p.unlocked[ch.id] == true or ch.id == "prologue"
            set_label(b, open and ch.title or (ch.title .. "  (locked)"))
            local ub = b:get("UiButton")
            ub.interactable = open
            b:set("UiButton", ub)
        end
    end
    self:show("main")
    Game.menu = self
end

function Menu:show(which)
    self.main:set_visible(which == "main")
    self.ops:set_visible(which == "ops")
    self.confirm:set_visible(which == "confirm")
end

function Menu:on_click(button, action)
    local p = Game.progress()
    if action == "continue" then
        Campaign.start(p.op or "prologue", false)
    elseif action == "new" then
        if p.completed or (p.op and p.op ~= "prologue") then self:show("confirm") else self:new_campaign() end
    elseif action == "confirm_new" then
        self:new_campaign()
    elseif action == "cancel" then
        self:show("main")
    elseif action == "ops" then
        self:show("ops")
    elseif action == "settings" then
        Game.emit("open_settings")
    elseif action == "credits" then
        scene.load("scenes/credits.vscene")
    elseif string.sub(action, 1, 3) == "op:" then
        local id = string.sub(action, 4)
        if p.unlocked[id] or id == "prologue" then Campaign.start(id, true) end
    end
end

function Menu:new_campaign()
    Game.campaign = { op = "prologue", unlocked = { prologue = true }, flags = {} }
    Game.save_progress()
    Campaign.start("prologue", true)
end

function Menu:update(dt)
    self.t += dt
    if self.cam and self.cam0 then
        local t = self.t
        self.cam.position = self.cam0 + vector.create(math.sin(t * 0.05) * 3, math.sin(t * 0.08) * 0.3, -t * 0.05 % 6)
        self.cam.rotation = vector.create(-4 + math.sin(t * 0.07) * 1.5, 12 + math.sin(t * 0.04) * 8, 0)
    end
    if input.action_pressed("pause") and not Game.paused then
        self:show("main")
    end
end

return Menu
