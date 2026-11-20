-- SPECIAL OPS HUD. Reads shared state from scripts/lib/game.luau (objective, focus prompt,
-- weapon state, health, subtitles, cinematic presentation) and the touch layout from
-- scripts/lib/controls.luau, and writes it into the UI entities built by tools/scenes/rig.py.
local Game = require("scripts/lib/game")
local Controls = require("scripts/lib/controls")
local Squad = require("scripts/lib/squad")
local Combat = require("scripts/lib/combat")

-- Layout constants shared with tools/scenes/rig.py (HUD v2).
local COMPASS_PPD = 4.0
local COMPASS_HALF = 270
local MAG_PIPS = 40
local SQUAD_ROWS = 5
local SQUAD_ORDER = { "Anchor", "Patch", "Echo", "Tally", "Brick" }

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
-- Toast queue: a repeat of the toast already queued is dropped, and an objective toast replaces any
-- objective toast still waiting (only the newest objective is announced).
Game.toast = function(text, seconds, kind)
    for i = #toasts, 1, -1 do
        local q = toasts[i]
        if q.text == text then return end
        if kind == "objective" and q.kind == "objective" then
            if i > 1 then table.remove(toasts, i) else q.t = math.min(q.t, 0.25) end -- shown one: cut short
        end
    end
    table.insert(toasts, { text = text, t = seconds or 3.5, kind = kind })
end
Game.toast_queue = toasts

Game.objective = Game.objective or { op = "", text = "", log = {} }
Game.set_objective = function(text, op)
    local o = Game.objective
    if op then o.op = op end
    if o.text ~= "" and o.text ~= text then table.insert(o.log, 1, "Done: " .. o.text) end
    if o.text ~= text then o.changed_at = time.now() end
    o.text = text
    Game.toast("New objective: " .. text, 3.5, "objective")
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
                  "Objective Text", "Objective Accent", "Toast", "Awareness", "Prompt", "Weapon Panel", "Weapon Name", "Ammo", "Weapon State",
                  "Status Panel", "Health Bar", "Tool Text", "Subtitle", "Subtitle Speaker", "Subtitle Text", "Skip Hint",
                  "Skip Button", "Fade", "Title Card", "Title Sub", "Title Kicker", "Title Rule", "Touch", "Stick Base", "Stick Knob", "Diagnostics", "Diagnostics Text",
                  "Objectives Log", "Letterbox Top", "Letterbox Bottom", "Damage", "Scope", "Scope Zoom", "Prompt Detail",
                  "Kit Text", "Waypoint", "Waypoint Tick", "Compass", "Compass Strip", "Compass Heading",
                  "Compass Notch", "Squad", "Feed", "Prompt Key", "Prompt Label", "Reserve", "Mag Pips",
                  "Reload Back", "Reload Bar", "Health Trail", "Stance Text", "Damage Dirs" } do
        self.e[n] = find(r, n)
        if not self.e[n] then log.warn("hud: missing element " .. n) end
    end
    self.touch_buttons = {}
    for _, b in Controls.buttons do
        self.touch_buttons[b.name] = find(r, "Touch " .. b.name)
        self.touch_icons = self.touch_icons or {}
        self.touch_icons[b.name] = find(r, "Touch " .. b.name .. " Icon")
    end
    self.pips, self.dirs, self.rows = {}, {}, {}
    for i = 0, MAG_PIPS - 1 do self.pips[i] = find(r, "Pip " .. i) end
    for k = 0, 7 do self.dirs[k] = { e = find(r, "Dmg Dir " .. k), t = 0 } end
    for i = 1, SQUAD_ROWS do
        self.rows[i] = { dot = find(r, "Squad " .. i .. " Dot"), name = "Squad " .. i .. " Name",
                         state = "Squad " .. i .. " State" }
        self.e[self.rows[i].name] = find(r, self.rows[i].name)
        self.e[self.rows[i].state] = find(r, self.rows[i].state)
    end
    self.cache = {}
    self.hit_t = 0
    self.hit_kind = "body"
    self.kill_t = 0
    self.hurt_t = 0
    self.trail = 1
    self.trail_hold = 0
    self.feed = {}
    self.calm_t = 0
    self.hud_alpha = 1
    self.last_sig = ""
    self.pulse = 0
    self.fps_acc, self.fps_n, self.fps = 0, 0, 0
    self.frame_ms_max = 0
    self.diag_t = 0
    self.show_log = false
    Game.on("hit_confirm", function(zone)
        self.hit_t = 0.18
        self.hit_kind = zone or "body"
        self.last_hit_zone, self.last_hit_time = zone, time.now()
    end)
    Game.on("player_hurt", function(a, from)
        self.hurt_t = math.min(1, self.hurt_t + a / 40)
        self.trail_hold = 0.55
        self.calm_t = 0
        if from and from.valid and Game.player_state and Game.player_state.cam then
            local b = Hud.bearing(from.world_position)
            local k = math.floor(((b % 360) + 22.5) / 45) % 8
            self.dirs[k].t = 1
        end
    end)
    Game.on("enemy_down", function(e, source)
        if not (source and Game.player and source.id == Game.player.id) then return end
        self.kill_t = 0.42
        local head = self.last_hit_zone == "head" and self.last_hit_time and time.now() - self.last_hit_time < 0.3
        self:push_feed(head and "CONTRACTOR STUNNED  ·  HEAD" or "CONTRACTOR STUNNED")
    end)
    Game.on("enemy_surrender", function() self:push_feed("CONTRACTOR SURRENDERED") end)
    self.e["Diagnostics"]:set_visible(false)
end

-- Estimated wrapped line count of a subtitle in the 740-unit text box (Inter Medium averages about
-- 0.4 em per glyph in sentence case, measured on a 1312x576 capture); words never split, so a long word pushes to the next line as the renderer does.
function Hud.subtitle_lines(text, size)
    local per = math.max(10, math.floor(740 / (size * 0.43)))
    local lines, cur = 1, 0
    for word in string.gmatch(text, "%S+") do
        local n = utf8.len(word) or #word
        if cur == 0 then cur = n
        elseif cur + 1 + n <= per then cur += 1 + n
        else lines += 1; cur = n end
    end
    return math.min(lines, 4)
end

-- Bearing of a world point relative to the view, degrees clockwise (0 ahead, 90 right).
function Hud.bearing(p)
    local ps = Game.player_state
    local origin, dir = ps:aim_ray()
    local d = p - origin
    local f = math.deg(math.atan2(-dir.x, -dir.z))
    local g = math.deg(math.atan2(-d.x, -d.z))
    return (f - g + 540) % 360 - 180
end

function Hud:push_feed(text)
    table.insert(self.feed, 1, { text = text, t = 4.0 })
    while #self.feed > 3 do table.remove(self.feed) end
end

function Hud:image_alpha(name, rgb, a, e)
    local key = name .. ":ia"
    local sig = string.format("%.2f %.2f %.2f %.2f", rgb[1], rgb[2], rgb[3], a)
    if self.cache[key] == sig then return end
    self.cache[key] = sig
    e = e or self.e[name]
    if not e then return end
    local im = e:get("UiImage")
    if not im then return end
    im.tint = { rgb[1], rgb[2], rgb[3], a }
    e:set("UiImage", im)
end

function Hud:panel_color(e, key, c)
    local sig = string.format("%.2f %.2f %.2f %.2f", c[1], c[2], c[3], c[4])
    if self.cache[key] == sig then return end
    self.cache[key] = sig
    local p = e:get("UiPanel")
    p.color = c
    e:set("UiPanel", p)
end

-- What the reticle is over: "enemy" (an awake contractor), "friend" (an operator) or nil.
function Hud:aim_target()
    if not Game.aim_ray or not Game.player then return nil end
    local o, d = Game.aim_ray()
    if not o then return nil end
    local hit = physics.raycast(o, d, 120, nil, Game.player)
    if not hit or not hit.entity then return nil end
    local h = Combat.handler_of(hit.entity)
    if not h or not h.entity.valid then return nil end
    local rec = Squad.state().enemies[h.entity.id]
    if rec then
        local c = rec.ctl
        if c and not c.down and not c.dormant and not c.parley then return "enemy" end
        return nil
    end
    local friend = false
    Squad.each(function(_, m) if m.entity.id == h.entity.id then friend = true end end)
    return friend and "friend" or nil
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
-- Chapter card: "Operation 01: Green Silence" -> kicker OPERATION 01 / title GREEN SILENCE; the rule
-- grows over 0.5 s, the title rises 14 units and fades in, the place line follows 0.35 s later.
function Hud:title_card(pres)
    local title = pres.title
    if title ~= self.title_shown then
        self.title_shown = title
        self.title_t0 = time.now()
        if title then
            local kick, main = string.match(title, "^(.-):%s*(.+)$")
            if not kick then kick, main = "", title end
            self:text("Title Kicker", string.upper(kick))
            self:text("Title Card", string.upper(main))
        end
    end
    local on = title ~= nil
    self:vis("Title Card", on)
    self:vis("Title Kicker", on)
    self:vis("Title Rule", on)
    self:vis("Title Sub", on and pres.subtitle_title ~= nil)
    if pres.subtitle_title then self:text("Title Sub", string.upper((string.gsub(pres.subtitle_title, ",%s*", "  \u{00B7}  ")))) end
    if not on then return end
    local t = (time.now()) - self.title_t0
    local function ease(x) x = math.clamp(x, 0, 1); return 1 - (1 - x) * (1 - x) * (1 - x) end
    local a = ease(t / 0.6)
    self:rect(self.e["Title Rule"], "trule", function(r) r.size = { math.floor(160 * ease((t - 0.15) / 0.5) + 0.5), 3 } end)
    self:rect(self.e["Title Card"], "tcard", function(r) r.opacity = a; r.position[2] = math.floor(-20 + 14 * (1 - a) + 0.5) end)
    self:rect(self.e["Title Kicker"], "tkick", function(r) r.opacity = ease((t - 0.1) / 0.5) end)
    self:rect(self.e["Title Sub"], "tsub", function(r) r.opacity = ease((t - 0.45) / 0.5) end)
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
    -- The controller in use dropped: pause at once (and say why) rather than let Rook walk on.
    if Controls.take_pad_lost() and not Game.paused and Game.pause_menu then
        Game.pause_reason = "pad"
        Game.emit("open_pause")
    end
    if Controls.pressed("diagnostics") then s.diagnostics = not s.diagnostics end
    if Controls.pressed("objectives") and playing then self.show_log = not self.show_log end

    -- A chapter card or a fade owns the centre of the screen: the reticle, compass, waypoint and
    -- roster step aside until it has gone, so nothing draws through the title.
    local card = pres.title ~= nil or pres.subtitle_title ~= nil or pres.fade > 0.3
    local framed = playing and not card

    -- Reticle.
    local ws = Game.weapon_hud
    local zoom = Game.player_state and Game.player_state.zoom or 0
    local show_ret = framed and ws ~= nil and zoom < 0.75
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
        -- tint: red over an awake contractor, blue over a teammate (hold fire)
        self.aim_t = (self.aim_t or 0) - dt
        if self.aim_t <= 0 then
            self.aim_t = 0.08
            self.aim_kind = self:aim_target()
        end
        local c = self.aim_kind == "enemy" and { 1, 0.36, 0.3, 0.95 } or
            (self.aim_kind == "friend" and { 0.45, 0.75, 1, 0.95 } or { 1, 1, 1, 0.9 })
        for _, n in { "R Up", "R Down", "R Left", "R Right", "R Dot" } do self:panel_color(self.e[n], n .. ":c", c) end
    end
    -- Hit marker: white body hit, red head hit, larger amber mark on a takedown.
    self.hit_t = math.max(0, self.hit_t - dt)
    self.kill_t = math.max(0, self.kill_t - dt)
    local show_hit = (self.hit_t > 0 or self.kill_t > 0) and playing
    self:vis("Hit Marker", show_hit)
    if show_hit then
        local kill = self.kill_t > 0
        local col = kill and { 1, 0.72, 0.3 } or (self.hit_kind == "head" and { 1, 0.3, 0.25 } or { 1, 1, 1 })
        local a = kill and math.min(1, self.kill_t / 0.15) or math.min(1, self.hit_t / 0.08)
        self:image_alpha("Hit Marker", col, 0.95 * a)
        local sz = kill and math.floor(44 + (0.42 - self.kill_t) * 30) or 34
        self:rect(self.e["Hit Marker"], "hm:r", function(r) r.size = { sz, sz } end)
    end

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

    -- Objective panel: slides in and the accent bar flares for 1.6 s when the objective changes, so a
    -- new objective reads in the corner it lives in, not only in the centre toast.
    if o.changed_at and self.e["Objective"] and self.e["Objective Accent"] then
        local k = math.clamp((time.now() - o.changed_at) / 1.6, 0, 1)
        local ease = 1 - (1 - math.min(1, k * 2.5)) ^ 3
        local flare = (1 - k) ^ 2
        self:rect(self.e["Objective"], "obj:r", function(r) r.position = { 110 - 36 * (1 - ease), 22 } end)
        self:rect(self.e["Objective Accent"], "obja:r", function(r) r.size = { 3 + math.floor(5 * flare + 0.5), 50 } end)
        if k >= 1 then o.changed_at = nil end
    end

    -- Toasts. They wait (paused, hidden) while a chapter title card is up or the screen is fading, so
    -- the centre of the screen shows one thing at a time.
    local toast = toasts[1]
    local busy = cin or pres.title ~= nil or pres.subtitle_title ~= nil or pres.fade > 0.3
    if toast and not busy then
        toast.t -= dt
        if toast.t <= 0 then table.remove(toasts, 1) end
    end
    toast = toasts[1]
    self:vis("Toast", toast ~= nil and not busy)
    if toast then self:text("Toast", toast.text) end

    -- Awareness (scripts/lib/reactions.luau sets Game.awareness / Game.awareness_level).
    local aw = Game.awareness
    self:vis("Awareness", aw ~= nil and aw ~= "" and not cin)
    if aw then
        self:text("Awareness", aw)
        local lvl = Game.awareness_level or 0
        self.pulse += dt
        local a = lvl >= 1 and (0.75 + 0.25 * math.sin(self.pulse * 6)) or 0.85
        local e = self.e["Awareness"]
        local key = "aw:c"
        local sig = string.format("%.1f %.2f", lvl, a)
        if e and self.cache[key] ~= sig then
            self.cache[key] = sig
            local t = e:get("UiText")
            t.color = lvl >= 1 and { 1, 0.38, 0.3, a } or { 1, 0.8, 0.45, a }
            e:set("UiText", t)
        end
    end

    -- Heading compass.
    local cps = Game.player_state
    local show_comp = framed and cps ~= nil and not self.show_log
    self:vis("Compass", show_comp)
    self:vis("Compass Notch", show_comp)
    self:vis("Compass Heading", show_comp)
    if show_comp then
        local heading = (-(cps.yaw or 0)) % 360
        local x = -math.floor(heading * COMPASS_PPD + 0.5)
        self:rect(self.e["Compass Strip"], "cs:r", function(r) r.position = { x, 0 } end)
        self:text("Compass Heading", string.format("%03d", math.floor(heading + 0.5) % 360))
    end

    -- Waypoint (Game.waypoint = { pos = vector, label = string }).
    local wpt = Game.waypoint
    local show_wp = wpt ~= nil and framed and not self.show_log and s.waypoints ~= false
    self:vis("Waypoint", show_wp)
    self:vis("Waypoint Tick", show_wp)
    local wps = Game.player_state
    if show_wp and wps and Game.player then
        local d = wpt.pos - Game.player.position
        local dist = math.sqrt(d.x * d.x + d.z * d.z)
        local bearing = math.deg(math.atan2(-d.x, -d.z))
        local rel = (bearing - wps.yaw + 540) % 360 - 180   -- + = to the left
        local x = Game.clamp(-rel * COMPASS_PPD, -COMPASS_HALF, COMPASS_HALF)
        local label = string.format("%d m", math.floor(dist + 0.5))
        if wpt.label and wpt.label ~= "" then label = wpt.label .. "  " .. label end
        if rel > 70 then label = "< " .. label elseif rel < -70 then label = label .. " >" end
        self:text("Waypoint", label)
        local xi = math.floor(x + 0.5)
        local lx = Game.clamp(xi, -COMPASS_HALF + 110, COMPASS_HALF - 110)
        self:rect(self.e["Waypoint"], "wp:r", function(r) r.position = { lx, 62 } end)
        self:rect(self.e["Waypoint Tick"], "wpt:r", function(r) r.position = { xi, 31 } end)
    end

    -- Interaction prompt.
    local f = Game.focus
    self:vis("Prompt", f ~= nil and framed)
    if f then
        local key = Controls.state.touch_used and "USE" or (Controls.state.gamepad_used and "X" or "E")
        self:text("Prompt Key", key)
        self:text("Prompt Label", f.prompt or "Interact")
    end
    self:vis("Prompt Detail", f ~= nil and framed and f.detail ~= nil)
    if f and f.detail then self:text("Prompt Detail", f.detail) end

    -- Weapon panel.
    self:vis("Weapon Panel", ws ~= nil and not cin)
    if ws then
        self:text("Weapon Name", ws.name or "")
        local ammo, mag = ws.ammo or 0, ws.mag or 0
        self:text("Ammo", tostring(ammo))
        self:text("Reserve", "/ " .. tostring(ws.reserve or 0))
        -- count goes amber at a quarter, red when empty
        local low = mag > 0 and ammo <= math.floor(mag * 0.25)
        local ac = ammo == 0 and { 1, 0.36, 0.3, 1 } or (low and { 1, 0.78, 0.4, 1 } or { 1, 1, 1, 1 })
        local ae = self.e["Ammo"]
        local asig = string.format("%.2f %.2f", ac[2], ac[3])
        if ae and self.cache["ammo:c"] ~= asig then
            self.cache["ammo:c"] = asig
            local t = ae:get("UiText"); t.color = ac; ae:set("UiText", t)
        end
        self:text("Weapon State", ws.state or "")
        -- magazine pips (one per round up to MAG_PIPS)
        local psig = ammo .. "/" .. mag
        if self.cache["pips"] ~= psig then
            self.cache["pips"] = psig
            local show = mag > 0 and mag <= MAG_PIPS
            for i = 0, MAG_PIPS - 1 do
                local e = self.pips[i]
                if e then
                    local on = show and i < mag
                    e:set_visible(on)
                    if on then
                        local p = e:get("UiPanel")
                        -- rounds left fill from the left of the row (right-anchored pips count down)
                        local full = (mag - 1 - i) < ammo
                        p.color = full and { 1, 1, 1, 0.88 } or { 1, 1, 1, 0.16 }
                        e:set("UiPanel", p)
                    end
                end
            end
        end
        local rl = ws.reload
        self:vis("Reload Back", rl ~= nil)
        self:vis("Reload Bar", rl ~= nil)
        if rl then
            local w = math.floor(200 * Game.clamp(rl, 0, 1) + 0.5)
            self:rect(self.e["Reload Bar"], "rl:r", function(r) r.size = { w, 3 } end)
        end
    end

    -- Status: health and tool.
    local ps = Game.player_state
    self:vis("Status Panel", ps ~= nil and not cin)
    if ps then
        local frac = Game.clamp(ps.health / ps.max_health, 0, 1)
        self:rect(self.e["Health Bar"], "hp:r", function(r) r.size = { math.floor(272 * frac + 0.5), 8 } end)
        -- the trailing bar holds for a moment after a hit, then drains down to the real value
        self.trail_hold = math.max(0, self.trail_hold - dt)
        if frac > self.trail then self.trail = frac
        elseif self.trail_hold <= 0 then self.trail = math.max(frac, self.trail - dt * 0.45) end
        self:rect(self.e["Health Trail"], "ht:r", function(r) r.size = { math.floor(272 * self.trail + 0.5), 8 } end)
        local hc = frac < 0.35 and { 1, 0.42, 0.32, 0.95 } or (frac < 0.6 and { 1, 0.8, 0.45, 0.95 } or { 0.55, 0.9, 0.75, 0.95 })
        self:panel_color(self.e["Health Bar"], "hp:c", hc)
        local stance = ps.crouched and "CROUCHED" or (ps.sprinting and "SPRINTING" or "STANDING")
        if ps.torch_on then stance = stance .. "   ·   TORCH ON" end
        self:text("Stance Text", stance)
        self:text("Tool Text", Game.tool_hud or "")
        self:text("Kit Text", Game.kit_hud or "")
    end
    -- Edge vignette: hit flash plus a slow heartbeat pulse at low health.
    self.hurt_t = math.max(0, self.hurt_t - dt * 0.8)
    local lowv = 0
    if ps and ps.health > 0 and ps.health < 35 then
        self.beat = (self.beat or 0) + dt * (1.6 - ps.health / 50)
        lowv = 0.32 + 0.16 * math.max(0, math.sin(self.beat * math.pi * 2)) ^ 4
    end
    local dmg = math.max(self.hurt_t * 0.75, lowv)
    self:vis("Damage", dmg > 0.01 and not cin)
    if dmg > 0.01 then self:image_alpha("Damage", { 0.62, 0.04, 0.02 }, math.min(0.9, dmg)) end
    for k = 0, 7 do
        local d = self.dirs[k]
        if d.e then
            d.t = math.max(0, d.t - dt * 0.9)
            local on = d.t > 0.01 and not cin
            local vk = "dd" .. k
            if self.cache[vk] ~= on then self.cache[vk] = on; d.e:set_visible(on) end
            if on then self:image_alpha("Dmg Dir " .. k, { 1, 0.22, 0.12 }, 0.9 * d.t, d.e) end
        end
    end

    -- Squad roster: who is where and what they are doing.
    local rows = {}
    for _, who in SQUAD_ORDER do
        local m = Squad.member(who)
        if m and m.entity and m.entity.valid then table.insert(rows, m) end
    end
    local show_sq = #rows > 0 and framed and not self.show_log
    -- Left-handed touch: the roster moves under the objectives / light column on the right and the
    -- feed steps left of that column (both follow the touch size setting).
    local swap, ts = Controls.hud_swap(), Controls.touch_scale()
    if self.e["Squad"] then
        self:rect(self.e["Squad"], "sqpos", function(r)
            if swap then
                r.anchor_min, r.anchor_max, r.pivot = { 1, 0 }, { 1, 0 }, { 0, 0 }
                r.position = { -240, math.floor((132 + 28) * ts + 12 + 0.5) }
            else
                r.anchor_min, r.anchor_max, r.pivot = { 0, 0 }, { 0, 0 }, { 0, 0 }
                r.position = { 110, 102 }
            end
        end)
    end
    if self.e["Feed"] then
        self:rect(self.e["Feed"], "feedpos", function(r)
            r.position = { swap and -math.floor((56 + 30) * ts + 18 + 0.5) or -28, 110 }
        end)
    end
    self:vis("Squad", show_sq)
    if show_sq then
        local pp = Game.player and Game.player.world_position
        for i = 1, SQUAD_ROWS do
            local row, m = self.rows[i], rows[i]
            local on = m ~= nil
            local rk = "sqv" .. i
            if self.cache[rk] ~= on then
                self.cache[rk] = on
                if row.dot then row.dot:set_visible(on) end
                if self.e[row.name] then self.e[row.name]:set_visible(on) end
                if self.e[row.state] then self.e[row.state]:set_visible(on) end
            end
            if m then
                local st, col
                if (m.stagger_t or 0) > 0 then st, col = "HIT", { 1, 0.42, 0.32, 1 }
                elseif m.engaged then st, col = "ENGAGED", { 1, 0.8, 0.45, 1 }
                elseif m.mode == "vehicle" then st, col = "MOUNTED", { 0.6, 0.85, 1, 0.9 }
                elseif m.mode == "hold" then st, col = "HOLDING", { 0.6, 0.85, 1, 0.9 }
                elseif m.mode == "move" then st, col = "MOVING", { 0.6, 0.85, 1, 0.9 }
                else st, col = "ON YOU", { 0.55, 0.9, 0.75, 0.95 } end
                if pp then
                    local dist = vector.magnitude(m.entity.world_position - pp)
                    if dist > 25 then st = st .. string.format("  %d m", math.floor(dist + 0.5)) end
                end
                self:text(row.name, string.upper(m.r and m.r.name or m.who or ""))
                self:text(row.state, st)
                if row.dot then self:panel_color(row.dot, "sqd" .. i, col) end
            end
        end
    end

    -- Takedown feed.
    for i = #self.feed, 1, -1 do
        self.feed[i].t -= dt
        if self.feed[i].t <= 0 then table.remove(self.feed, i) end
    end
    self:vis("Feed", #self.feed > 0 and playing)
    if #self.feed > 0 then
        local t = {}
        for _, f in self.feed do table.insert(t, f.text) end
        self:text("Feed", table.concat(t, "\n"))
    end

    -- Calm HUD: with nobody searching, no damage and no shooting for a while, the vitals, weapon
    -- and squad blocks settle back so the world carries the picture. Anything happening brings
    -- them straight back.
    local sig = string.format("%s %s %d", tostring(ws and ws.ammo), tostring(ws and ws.state),
        ps and math.floor(ps.health) or 0)
    local busy = (Game.awareness_level or 0) > 0 or zoom > 0.2 or sig ~= self.last_sig or (ps and ps.health < 60)
    self.last_sig = sig
    if busy then self.calm_t = 0 else self.calm_t += dt end
    local want = self.calm_t > 8 and 0.4 or 1
    self.hud_alpha = want > self.hud_alpha and math.min(want, self.hud_alpha + dt * 4) or
        math.max(want, self.hud_alpha - dt * 0.5)
    -- HUD opacity setting scales the ambient blocks; prompts, subtitles, cards and the reticle
    -- (it has its own opacity setting) stay at full strength.
    local hop = Game.clamp(s.hud_opacity or 1, 0.3, 1)
    local ha = math.floor(self.hud_alpha * hop * 50 + 0.5) / 50
    for _, n in { "Weapon Panel", "Status Panel", "Squad" } do
        local e = self.e[n]
        if e then self:rect(e, n .. ":o", function(r) r.opacity = ha end) end
    end
    local hq = math.floor(hop * 50 + 0.5) / 50
    for _, n in { "Compass", "Objective" } do
        local e = self.e[n]
        if e then self:rect(e, n .. ":ho", function(r) r.opacity = hq end) end
    end

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
        -- The plate grows with the line count, so a two-line radio line stays on its backing
        -- instead of spilling under it onto the gun.
        local lines = Hud.subtitle_lines(sub.text or "", s.subtitle_size)
        local lh = math.floor(s.subtitle_size * 1.28 + 0.5)
        local th = lines * lh
        self:rect(self.e["Subtitle Text"], "subt:r", function(r) r.size = { 740, th } end)
        self:rect(self.e["Subtitle"], "sub:r", function(r) r.size = { 760, th + 40 } end)
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
    self:title_card(pres)
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
                local d = math.floor(2 * Controls.radius(b) + 0.5)
                self:rect(e, "tb:" .. b.name, function(r)
                    r.anchor_min = { 0, 0 }; r.anchor_max = { 0, 0 }
                    r.position = { math.floor(bx), math.floor(by) }
                    r.size = { d, d }
                    local hidden = (b.name == "interact" and Game.focus == nil)
                    r.opacity = hidden and 0.25 or 1
                end)
                local ic = self.touch_icons[b.name]
                if ic then
                    local f = b.name == "fire" and 0.6 or 0.62
                    local di = math.floor(d * f + 0.5)
                    self:rect(ic, "tbi:" .. b.name, function(r) r.size = { di, di } end)
                end
                local held = Controls.state.down[b.name] == true
                local key = "tbp:" .. b.name
                if self.cache[key] ~= held then
                    self.cache[key] = held
                    -- pressed: the disc brightens and the icon picks up the HUD amber
                    local im = e:get("UiImage")
                    if im then
                        im.tint = held and { 1, 0.86, 0.62, 1 } or { 1, 1, 1, 0.92 }
                        e:set("UiImage", im)
                    end
                    local ic = self.touch_icons[b.name]
                    if ic then
                        local ii = ic:get("UiImage")
                        ii.tint = held and { 1, 0.78, 0.42, 1 } or { 1, 1, 1, 0.95 }
                        ic:set("UiImage", ii)
                    end
                end
            end
        end
        local st = Controls.stick
        local hx, hy = Controls.stick_home(cw)
        local base = st and st.origin or vector.create(hx, hy, 0)
        local knob = st and st.knob or base
        local ts = Controls.touch_scale()
        local bs, ks = math.floor(200 * ts + 0.5), math.floor(84 * ts + 0.5)
        self:rect(self.e["Stick Base"], "sb", function(r)
            r.position = { math.floor(base.x), math.floor(base.y) }
            r.size = { bs, bs }
            r.opacity = st and 1 or 0.55
        end)
        self:rect(self.e["Stick Knob"], "sk", function(r)
            r.position = { math.floor(knob.x), math.floor(knob.y) }
            r.size = { ks, ks }
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
