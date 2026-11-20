-- SPECIAL OPS pause and settings modal. Opens on the "pause" action (Escape, gamepad Start,
-- touch II), blocks gameplay input while open (Game.paused) and edits Game.settings.
local Game = require("scripts/lib/game")
local Controls = require("scripts/lib/controls")

local M = {}

-- Setting ranges: numeric {min, max, step}; booleans toggle; lists cycle.
local RANGES = {
    look_sensitivity = { 0.2, 3.0, 0.1 },
    aim_sensitivity = { 0.2, 1.0, 0.05 },
    fov = { 60, 95, 1 },
    camera_shake = { 0, 1, 0.25 },
    lens_effects = { 0, 1, 0.25 },
    reticle_size = { 0.5, 2.0, 0.1 },
    reticle_opacity = { 0.2, 1.0, 0.1 },
    subtitle_size = { 18, 40, 2 },
    subtitle_background = { 0, 0.9, 0.15 },
    hud_opacity = { 0.3, 1.0, 0.1 },
    touch_scale = { 0.8, 1.25, 0.05 },
    master_volume = { 0, 1, 0.1 },
    music_volume = { 0, 1, 0.1 },
    voice_volume = { 0, 1, 0.1 },
    sfx_volume = { 0, 1, 0.1 },
    ambient_volume = { 0, 1, 0.1 },
}
local LISTS = { touch_controls = { "auto", "on", "off" } }

local function find(root, name)
    local queue = { root }
    while #queue > 0 do
        local e = table.remove(queue, 1)
        if e.name == name then return e end
        for _, c in e:children() do table.insert(queue, c) end
    end
    return nil
end

function M:start()
    self.main = find(self.entity, "Pause Main")
    self.settings_panel = find(self.entity, "Settings Panel")
    self.op_label = find(self.entity, "Pause Op")
    self.values = {}
    for k, _ in Game.settings do
        local e = find(self.entity, "Set " .. k .. " Value")
        if e then self.values[k] = e end
    end
    self.open = false
    self:set_open(false)
    Game.on("open_pause", function() self:set_open(true) end)
    Game.on("open_settings", function()
        self:set_open(true)
        self.settings_only = true
        self.main:set_visible(false)
        self.settings_panel:set_visible(true)
        self:refresh()
    end)
    Game.pause_menu = self
end

function M:set_open(open)
    self.open = open
    Game.paused = open
    self.opened_frame = time.frame()
    local c = self.entity:get("UiCanvas")
    c.visible = open
    self.entity:set("UiCanvas", c)
    self.main:set_visible(true)
    self.settings_panel:set_visible(false)
    if open then
        self.pad_reason = Game.pause_reason == "pad"
        Game.pause_reason = nil
        self.op_label:set_text(self.pad_reason and "CONTROLLER DISCONNECTED"
            or (Game.objective and Game.objective.op or ""))
        self:refresh()
        Game.emit("paused", true)
    else
        Game.save_settings()
        Game.emit("paused", false)
    end
end

local function fmt(k, v)
    if type(v) == "boolean" then return v and "On" or "Off" end
    if type(v) == "string" then return string.upper(string.sub(v, 1, 1)) .. string.sub(v, 2) end
    if k == "fov" or k == "subtitle_size" then return string.format("%d", v) end
    if string.find(k, "volume") or k == "camera_shake" or k == "lens_effects" or k == "reticle_opacity"
        or k == "subtitle_background" or k == "hud_opacity" or k == "touch_scale" then
        return string.format("%d%%", math.floor(v * 100 + 0.5))
    end
    return string.format("%.2f", v)
end

function M:refresh()
    for k, e in self.values do e:set_text(fmt(k, Game.settings[k])) end
end

function M:change(key, dir)
    local s = Game.settings
    local v = s[key]
    if type(v) == "boolean" then
        s[key] = not v
    elseif LISTS[key] then
        local l = LISTS[key]
        local i = 1
        for j, x in l do if x == v then i = j end end
        i = ((i - 1 + (dir == "+" and 1 or -1)) % #l) + 1
        s[key] = l[i]
    elseif RANGES[key] then
        local r = RANGES[key]
        local nv = v + (dir == "+" and r[3] or -r[3])
        s[key] = math.floor(Game.clamp(nv, r[1], r[2]) / r[3] + 0.5) * r[3]
    end
    Game.apply_audio()
    if key == "lens_effects" then Game.apply_lens() end
    self:refresh()
end

function M:on_click(button, action)
    if action == "resume" then
        self:set_open(false)
    elseif action == "settings" then
        self.main:set_visible(false)
        self.settings_panel:set_visible(true)
        self:refresh()
    elseif action == "settings_back" then
        if self.settings_only then
            self.settings_only = false
            self:set_open(false)
            return
        end
        self.settings_panel:set_visible(false)
        self.main:set_visible(true)
        Game.save_settings()
    elseif action == "objectives" then
        self:set_open(false)
        Game.emit("show_objectives")
    elseif action == "restart_checkpoint" then
        self:set_open(false)
        Game.emit("restart_checkpoint")
    elseif action == "quit_menu" then
        self:set_open(false)
        Game.save_progress()
        scene.load("scenes/menu.vscene")
    elseif string.sub(action, 1, 4) == "set:" then
        local key, dir = string.match(action, "set:([%w_]+):([%+%-])")
        if key then self:change(key, dir) end
    end
end

function M:update(dt)
    -- After a controller disconnect, say so when it comes back (the game stays paused until the
    -- player resumes, so nobody is dropped back into a firefight mid-reconnect).
    if self.open and self.pad_reason and Controls.pad_connected() then
        self.pad_reason = false
        self.op_label:set_text("CONTROLLER RECONNECTED")
    end
    if self.open and time.frame() > (self.opened_frame or 0) then
        -- Close with the same pause action (or gamepad East / Escape).
        if input.action_pressed("pause") then
            if self.settings_only then
                self.settings_only = false
                self:set_open(false)
            elseif self.settings_panel:visible() then
                self.settings_panel:set_visible(false)
                self.main:set_visible(true)
            else
                self:set_open(false)
            end
        end
    end
end

return M
