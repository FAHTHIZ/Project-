-- SPECIAL OPS HUD. Reads shared state from scripts/lib/game.luau (objective, focus prompt,
-- weapon state, health, subtitles, cinematic presentation) and the touch layout from
-- scripts/lib/controls.luau, and writes it into the UI entities built by tools/scenes/rig.py.
local Game = require("scripts/lib/game")
local Controls = require("scripts/lib/controls")

local Hud = {}

local function find(root, name)
    -- Breadth-first search below root for a named entity.
    local queue = { root }
    while #queue > 0 do
        local e = table.remove(queue, 1)
        if e.name == name then return e end
        for _, c in e:children() do table.insert(queue, c) end
    end
    return nil
end

-- Shared presentation services --------------------------------------------------------------

local toasts = {}
Game.toast = function(text, seconds)
    table.insert(toasts, { text = text, t = seconds or 3.5 })
end

Game.objective = Game.objective or { op = "", text = "", log = {} }
Game.set_objective = function(text, op)
    local o = Game.objective
    if op then o.op = op end
    if o.text ~= "" and o.text ~= text then table.insert(o.log, 1, "Done: " .. o.text) end
    o.text = text
    Game.toast("New objective: " .. text, 3.5)
    Game.emit("objective", text)
end

Game.subtitle = nil -- { speaker, text, until_time }
Game.show_subtitle = function(speaker, text, seconds)
    Game.subtitle = { speaker = speaker, text = text, until_time = time.now() + (seconds or 3) }
end
Game.clear_subtitle = function() Game.subtitle = nil end

-- Cinematic presentation: letterbox 0..1, fade 0..1, title card.
Game.present = Game.present or { letterbox = 0, fade = 0, title = nil, subtitle_title = nil, skip_hint = false }

function Hud:start()
    Game.load_settings()
    local r = self.entity
    self.e = {}
    for _, n in { "Reticle", "R Up", "R Down", "R Left", "R Right", "R Dot", "Hit Marker", "Objective", "Objective Op",
                  "Objective Text", "Toast", "Awareness", "Prompt", "Weapon Panel", "Weapon Name", "Ammo", "Weapon State",
                  "Status Panel", "Health Bar", "Tool Text", "Subtitle", "Subtitle Speaker", "Subtitle Text", "Skip Hint",
                  "Skip Button", "Fade", "Title Card", "Title Sub", "Touch", "Stick Base", "Stick Knob", "Diagnostics", "Diagnostics Text",
                  "Objectives Log", "Letterbox Top", "Letterbox Bottom", "Damage", "Scope", "Scope Zoom", "Prompt Detail",
                  "Kit Text", "Waypoint", "Waypoint Tick" } do
        self.e[n] = find(r, n)
        if not self.e[n] then log.warn("hud: missing element " .. n) end
    end
    self.touch_buttons = {}
    for _, b in Controls.buttons do
        self.touch_buttons[b.name] = find(r, "Touch " .. b.name)
    end
    self.cache = {}
    self.hit_t = 0
    self.hurt_t = 0
    self.fps_acc, self.fps_n, self.fps = 0, 0, 0
    self.frame_ms_max = 0
    self.diag_t = 0
    self.show_log = false
    Game.on("hit_confirm", function() self.hit_t = 0.16 end)
    Game.on("player_hurt", function(a) self.hurt_t = math.min(1, self.hurt_t + a / 40) end)
    self.e["Diagnostics"]:set_visible(false)
end

-- Cached setters to avoid re-writing unchanged UI every frame.
function Hud:text(name, s)
    local key = name .. ":t"
    if self.cache[key] ~= s then
        self.cache[key] = s
        local e = self.e[name]
        if e then e:set_text(s) end
    end
end
function Hud:vis(name, v)
    local key = name .. ":v"
    if self.cache[key] ~= v then
        self.cache[key] = v
        local e = self.e[name]
        if e then e:set_visible(v) end
    end
end
function Hud:rect(e, key, fn)
    local r = e:get("UiRect")
    fn(r)
    local sig = json.encode(r)
    if self.cache[key] ~= sig then
        self.cache[key] = sig
        e:set("UiRect", r)
    end
end
function Hud:panel_alpha(name, a, border_a)
    local key = name .. ":a"
    local sig = string.format("%.2f %.2f", a, border_a or -1)
    if self.cache[key] == sig then return end
    self.cache[key] = sig
    local e = self.e[name]
    local p = e:get("UiPanel")
    p.color[4] = a
    if border_a then p.border_color[4] = border_a end
    e:set("UiPanel", p)
end

function Hud:update(dt)
    local s = Game.settings
    local cin = Game.cinematic
    local pres = Game.present
    local playing = Game.playing()
    Controls.poll()
    if Controls.pressed("pause") and not Game.paused then Game.emit("open_pause") end
    if Controls.pressed("diagnostics") then s.diagnostics = not s.diagnostics end
    if Controls.pressed("objectives") and playing then self.show_log = not self.show_log end

    -- Reticle.
    local ws = Game.weapon_hud
    local zoom = Game.player_state and Game.player_state.zoom or 0
    local show_ret = playing and ws ~= nil and zoom < 0.75
    self:vis("Reticle", show_ret)
    if show_ret then
        local spread = (ws.spread or 1) * 8 * s.reticle_size
        local a = s.reticle_opacity
        local gap = 6 + spread
        for n, p in { ["R Up"] = vector.create(0, gap, 0), ["R Down"] = vector.create(0, -gap, 0),
                      ["R Left"] = vector.create(-gap, 0, 0), ["R Right"] = vector.create(gap, 0, 0) } do
            self:rect(self.e[n], n .. ":r", function(r)
                r.position = { p.x, -p.y } -- UiRect is y-down
                r.opacity = a
                local long = 9 * s.reticle_size
                if n == "R Up" or n == "R Down" then r.size = { 2, long } else r.size = { long, 2 } end
            end)
        end
        self:rect(self.e["R Dot"], "dot:r", function(r) r.opacity = a end)
    end
    self.hit_t = math.max(0, self.hit_t - dt)
    self:vis("Hit Marker", self.hit_t > 0 and playing)

    -- Scope overlay (LR-4).
    local sc = Game.scope
    self:vis("Scope", sc ~= nil and playing)
    if sc then self:text("Scope Zoom", string.format("ZOOM %d / %d", sc.level, sc.levels)) end

    -- Objective and log.
    local o = Game.objective
    self:vis("Objective", (not cin) and o.text ~= "")
    self:text("Objective Op", o.op or "")
    self:text("Objective Text", o.text or "")
    self:vis("Objectives Log", self.show_log and playing)
    if self.show_log then
        local lines = { (o.op or "") .. "\n", "Current: " .. (o.text or "") }
        for i = 1, math.min(7, #o.log) do table.insert(lines, o.log[i]) end
        self:text("Objectives Log", table.concat(lines, "\n"))
    end

    -- Toasts.
    local toast = toasts[1]
    if toast and not cin then
        toast.t -= dt
        if toast.t <= 0 then table.remove(toasts, 1) end
    end
    self:vis("Toast", toast ~= nil and not cin)
    if toast then self:text("Toast", toast.text) end

    -- Awareness.
    local aw = Game.awareness
    self:vis("Awareness", aw ~= nil and aw ~= "" and not cin)
    if aw then self:text("Awareness", aw) end

    -- Waypoint (Game.waypoint = { pos = vector, label = string }).
    local wpt = Game.waypoint
    local show_wp = wpt ~= nil and playing and not self.show_log and s.waypoints ~= false
    self:vis("Waypoint", show_wp)
    self:vis("Waypoint Tick", show_wp)
    local wps = Game.player_state
    if show_wp and wps and Game.player then
        local d = wpt.pos - Game.player.position
        local dist = math.sqrt(d.x * d.x + d.z * d.z)
        local bearing = math.deg(math.atan2(-d.x, -d.z))
        local rel = (bearing - wps.yaw + 540) % 360 - 180   -- + = to the left
        local x = Game.clamp(-rel / 50 * 300, -470, 470)
        local label = (wpt.label or "") .. string.format("  %d m", math.floor(dist + 0.5))
        if rel > 70 then label = "< " .. label elseif rel < -70 then label = label .. " >" end
        self:text("Waypoint", label)
        local xi = math.floor(x + 0.5)
        self:rect(self.e["Waypoint"], "wp:r", function(r) r.position = { xi, 60 } end)
        self:rect(self.e["Waypoint Tick"], "wpt:r", function(r) r.position = { xi, 46 } end)
    end

    -- Interaction prompt.
    local f = Game.focus
    self:vis("Prompt", f ~= nil and playing)
    if f then
        local key = Controls.state.touch_used and "USE" or (Controls.state.gamepad_used and "[X]" or "[E]")
        self:text("Prompt", key .. "  " .. (f.prompt or "Interact"))
    end
    self:vis("Prompt Detail", f ~= nil and playing and f.detail ~= nil)
    if f and f.detail then self:text("Prompt Detail", f.detail) end

    -- Weapon panel.
    self:vis("Weapon Panel", ws ~= nil and not cin)
    if ws then
        self:text("Weapon Name", ws.name or "")
        self:text("Ammo", string.format("%d / %d", ws.ammo or 0, ws.reserve or 0))
        self:text("Weapon State", ws.state or "")
    end

    -- Status: health and tool.
    local ps = Game.player_state
    self:vis("Status Panel", ps ~= nil and not cin)
    if ps then
        local frac = Game.clamp(ps.health / ps.max_health, 0, 1)
        self:rect(self.e["Health Bar"], "hp:r", function(r) r.size = { math.floor(272 * frac + 0.5), 10 } end)
        self:text("Tool Text", Game.tool_hud or "")
        self:text("Kit Text", Game.kit_hud or "")
    end
    self.hurt_t = math.max(0, self.hurt_t - dt * 0.8)
    local low = ps and ps.health < 35 and 0.25 or 0
    local dmg = math.max(self.hurt_t * 0.55, low)
    self:vis("Damage", dmg > 0.01 and not cin)
    if dmg > 0.01 then self:panel_alpha("Damage", dmg * 0.25, dmg) end

    -- Subtitles.
    local sub = Game.subtitle
    if sub and time.now() > sub.until_time then Game.subtitle = nil; sub = nil end
    local show_sub = sub ~= nil and s.subtitles
    self:vis("Subtitle", show_sub)
    if show_sub then
        self:text("Subtitle Speaker", sub.speaker or "")
        self:text("Subtitle Text", sub.text or "")
        local key = "subsize"
        local sig = string.format("%d %.2f", s.subtitle_size, s.subtitle_background)
        if self.cache[key] ~= sig then
            self.cache[key] = sig
            local t = self.e["Subtitle Text"]:get("UiText")
            t.font_size = s.subtitle_size
            self.e["Subtitle Text"]:set("UiText", t)
            local p = self.e["Subtitle"]:get("UiPanel")
            p.color[4] = s.subtitle_background
            self.e["Subtitle"]:set("UiPanel", p)
        end
    end

    -- Cinematic presentation.
    local lb = pres.letterbox
    self:vis("Letterbox Top", lb > 0.01)
    self:vis("Letterbox Bottom", lb > 0.01)
    if lb > 0.01 then
        local h = math.floor(86 * lb + 0.5)
        self:rect(self.e["Letterbox Top"], "lbt", function(r) r.size = { 0, h } end)
        self:rect(self.e["Letterbox Bottom"], "lbb", function(r) r.size = { 0, h } end)
    end
    self:vis("Fade", pres.fade > 0.005)
    if pres.fade > 0.005 then self:panel_alpha("Fade", pres.fade) end
    self:vis("Title Card", pres.title ~= nil)
    self:vis("Title Sub", pres.subtitle_title ~= nil)
    if pres.title then self:text("Title Card", pres.title) end
    if pres.subtitle_title then self:text("Title Sub", pres.subtitle_title) end
    self:vis("Skip Hint", pres.skip_hint == true)
    self:vis("Skip Button", pres.skip_hint == true and Controls.show_touch())
    if pres.skip_hint then
        local k = Controls.state.touch_used and "Tap SKIP" or (Controls.state.gamepad_used and "Hold [B] to skip" or "Hold [Space] to skip")
        self:text("Skip Hint", k)
    end

    -- Touch controls.
    local show_touch = Controls.show_touch() and playing
    self:vis("Touch", show_touch)
    if show_touch then
        local cw = select(1, Controls.canvas_size())
        for _, b in Controls.buttons do
            local e = self.touch_buttons[b.name]
            local en = Controls.button_enabled(b)
            if e and self.cache["tbv:" .. b.name] ~= en then
                self.cache["tbv:" .. b.name] = en
                e:set_visible(en)
            end
            if e and en then
                local bx, by = Controls.button_center(b, cw)
                self:rect(e, "tb:" .. b.name, function(r)
                    r.anchor_min = { 0, 0 }; r.anchor_max = { 0, 0 }
                    r.position = { math.floor(bx), math.floor(by) }
                    local hidden = (b.name == "interact" and Game.focus == nil)
                    r.opacity = hidden and 0.25 or 1
                end)
                local held = Controls.state.down[b.name] == true
                local key = "tbp:" .. b.name
                if self.cache[key] ~= held then
                    self.cache[key] = held
                    local p = e:get("UiPanel")
                    p.color = held and { 0.55, 0.8, 0.95, 0.45 } or { 0.05, 0.07, 0.08, 0.35 }
                    e:set("UiPanel", p)
                end
            end
        end
        local st = Controls.stick
        local base = st and st.origin or vector.create(220, 470, 0)
        local knob = st and st.knob or base
        self:rect(self.e["Stick Base"], "sb", function(r)
            r.position = { math.floor(base.x), math.floor(base.y) }
            r.opacity = st and 1 or 0.55
        end)
        self:rect(self.e["Stick Knob"], "sk", function(r)
            r.position = { math.floor(knob.x), math.floor(knob.y) }
            r.opacity = st and 1 or 0.55
        end)
    end

    -- Diagnostics: real measurements only.
    self.fps_acc += dt
    self.fps_n += 1
    self.frame_ms_max = math.max(self.frame_ms_max, dt * 1000)
    if self.fps_acc >= 0.5 then
        self.fps = self.fps_n / self.fps_acc
        self.fps_acc, self.fps_n = 0, 0
        self.diag_ms_max = self.frame_ms_max
        self.frame_ms_max = 0
    end
    self:vis("Diagnostics", s.diagnostics)
    if s.diagnostics then
        self.diag_t -= dt
        if self.diag_t <= 0 then
            self.diag_t = 0.5
            local w, h = ui.screen_size()
            local pos = Game.player and Game.player.position or vector.create(0, 0, 0)
            local ps = Game.player_state
            local lines = {
                string.format("FPS %.1f   frame max %.1f ms", self.fps, self.diag_ms_max or 0),
                string.format("Window %dx%d   quality %s", w, h, s.quality),
                "GPU time: unavailable (no GPU timestamp queries)",
                string.format("Entities %d", scene.count()),
                string.format("Player %.1f %.1f %.1f  yaw %.0f pitch %.0f", pos.x, pos.y, pos.z,
                    ps and ps.yaw or 0, ps and ps.pitch or 0),
                string.format("Scene %s", tostring(scene.current())),
                string.format("Touches %d  pad %s", input.touch_count(), tostring(input.gamepad_connected())),
                string.format("Op %s  frame %d", Game.campaign and Game.campaign.op or "-", time.frame()),
            }
            if Game.diag_extra then
                for _, l in Game.diag_extra() do table.insert(lines, l) end
            end
            self:text("Diagnostics Text", table.concat(lines, "\n"))
        end
    end
end

return Hud
