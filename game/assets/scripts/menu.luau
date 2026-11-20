-- SPECIAL OPS front end. First launch plays a short boot sequence (studio card, engine card,
-- content note) over black, fades into the storm-night key art (three of LANTERN under the
-- sodium lamp), shows the title with "tap to start", then slides the menu list in. Returning
-- from a mission goes straight to the list. Any tap / click / Enter skips the boot.
-- Menu: continue, new campaign, operation select (unlocked chapters), settings, credits.
local Game = require("scripts/lib/game")
local Campaign = require("scripts/lib/campaign")

local Menu = {}

-- Boot timeline (seconds): each card fades in, holds, fades out.
local CARDS = {
    { name = "Boot Studio", t0 = 0.6, t1 = 2.9 },
    { name = "Boot Engine", t0 = 3.2, t1 = 5.7 },
    { name = "Boot Warn",   t0 = 6.0, t1 = 8.4 },
}
local REVEAL = 8.6       -- black lifts over 1.6 s
local TITLE_IN = 9.6     -- heading fades in
local PRESS_IN = 10.8    -- "tap to start" appears
local BOOT_END = 11.0
local ROWS = { "Menu Continue", "Menu New campaign", "Menu Operations", "Menu Settings", "Menu Credits" }

local function smooth(a, b, t)
    local x = math.clamp((t - a) / (b - a), 0, 1)
    return x * x * (3 - 2 * x)
end

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
    text = string.upper(text) -- condensed caps style (tools/scenes/build_menu.py)
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
    self.cache = {}
    self.el = {}
    for _, n in { "Boot", "Boot Studio", "Boot Engine", "Boot Warn", "Menu Head", "Menu Press", "Menu Press Text",
                  "Menu Shade", "Menu Shade Bottom", "Menu Version" } do
        self.el[n] = find(self.entity, n)
    end
    self.rows = {}
    for i, n in ROWS do self.rows[i] = find(self.entity, n) end
    if Game.front_end_booted then
        self.phase = "main"
        self:set_op("Boot", 0)
        self.el["Boot"]:set_visible(false)
        self.el["Menu Press"]:set_visible(false)
        self:show("main")
        self.list_t = 0.25
    else
        self.phase = "boot"
        self.el["Boot"]:set_visible(true)
        self:show("none")
        self:set_op("Menu Head", 0)
        self.el["Menu Press"]:set_visible(false)
        for _, c in CARDS do self:set_op(c.name, 0) end
    end
    Game.menu = self
end

function Menu:set_op(name, a, e)
    e = e or self.el[name]
    if not e then return end
    local q = math.floor(a * 100 + 0.5)
    if self.cache[name] == q then return end
    self.cache[name] = q
    local r = e:get("UiRect")
    r.opacity = q / 100
    e:set("UiRect", r)
end

function Menu:skip_boot()
    if self.phase == "boot" and self.t < REVEAL then self.t = REVEAL end
end

function Menu:enter_main()
    Game.front_end_booted = true
    self.phase = "main"
    self.el["Boot"]:set_visible(false)
    self.el["Menu Press"]:set_visible(false)
    self:set_op("Menu Head", 1)
    self:show("main")
    self.list_t = 0
end

function Menu:show(which)
    self.main:set_visible(which == "main")
    if which == "main" then self.list_t = 0 end
    self.ops:set_visible(which == "ops")
    self.confirm:set_visible(which == "confirm")
end

function Menu:on_click(button, action)
    if action == "skip_boot" then self:skip_boot() return end
    if action == "start" then self:enter_main() return end
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
        -- slow dolly in and out (no wrap-around pop), gentle sway
        self.cam.position = self.cam0 + vector.create(math.sin(t * 0.05) * 2.2, math.sin(t * 0.08) * 0.25, -2.2 + 2.2 * math.cos(t * 0.03))
        self.cam.rotation = vector.create(-4 + math.sin(t * 0.07) * 1.5, 12 + math.sin(t * 0.04) * 8, 0)
    end
    if self.phase == "boot" then
        local t = self.t
        for _, c in CARDS do
            self:set_op(c.name, smooth(c.t0, c.t0 + 0.7, t) * (1 - smooth(c.t1 - 0.5, c.t1, t)))
        end
        self:set_op("Boot", 1 - smooth(REVEAL, REVEAL + 1.6, t))
        self:set_op("Menu Head", smooth(TITLE_IN, TITLE_IN + 1.2, t))
        if t >= BOOT_END then
            self.phase = "title"
            self.el["Boot"]:set_visible(false)
            self.el["Menu Press"]:set_visible(true)
        end
        if t < REVEAL and (input.action_pressed("skip") or input.touch_count() > 0) then self:skip_boot() end
    elseif self.phase == "title" then
        -- slow breathing prompt
        self:set_op("Menu Press Text", 0.45 + 0.45 * (0.5 + 0.5 * math.sin((self.t - PRESS_IN) * 2.4)))
        if input.action_pressed("skip") then self:enter_main() end
    elseif self.list_t then
        -- list rows slide in from the left, staggered 60 ms
        self.list_t += dt
        for i, e in self.rows do
            local k = smooth(0.06 * (i - 1), 0.06 * (i - 1) + 0.35, self.list_t)
            local key = "row" .. i
            local q = k >= 1 and 1000 or math.floor(k * 50 + 0.5)
            if self.cache[key] ~= q then
                self.cache[key] = q
                local r = e:get("UiRect")
                r.opacity = k
                r.position = { -36 * (1 - k), r.position[2] }
                e:set("UiRect", r)
            end
        end
        if self.list_t > 1 then self.list_t = nil end
    end
    if input.action_pressed("pause") and not Game.paused and self.phase == "main" then
        self:show("main")
    end
end

return Menu
