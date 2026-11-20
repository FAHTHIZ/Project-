-- SPECIAL OPS unified controls.
-- Keyboard/mouse, gamepad (through victus.project actions) and multitouch (virtual stick, look
-- region and on-screen buttons) all feed the same logical actions:
--   move (vector), look (degrees this frame), fire, aim, reload, switch, interact, tool, jump,
--   sprint, crouch, pause, objectives, diagnostics, quick_save, quick_load.
-- Controls.poll() runs once per frame (lazily, on first use), so every script sees one state.
local Game = require("scripts/lib/game")

local Controls = {}

-- Touch layout in canvas units (the HUD canvas is 720 tall; its width follows the aspect).
-- y is measured from the top. `ax` 1 measures x from the right edge. Shared with hud.luau.
Controls.buttons = {
    -- Right-thumb cluster around FIRE (thumb rests at fire; aim and jump on the right edge for
    -- the index finger / claw grip), kept clear of the weapon panel in the bottom-right corner.
    { name = "fire",     ax = 1, x = 205, y = 440, r = 80, label = "FIRE" },
    { name = "aim",      ax = 1, x = 78,  y = 330, r = 46, label = "AIM" },
    { name = "jump",     ax = 1, x = 70,  y = 520, r = 40, label = "JUMP" },
    { name = "reload",   ax = 1, x = 355, y = 545, r = 42, label = "RELOAD" },
    { name = "crouch",   ax = 1, x = 345, y = 655, r = 40, label = "CROUCH" },
    { name = "switch",   ax = 1, x = 215, y = 290, r = 38, label = "SWITCH" },
    { name = "tool",     ax = 1, x = 330, y = 330, r = 38, label = "TOOL" },
    { name = "interact", ax = 1, x = 480, y = 440, r = 50, label = "USE" },
    { name = "utility",  ax = 1, x = 470, y = 590, r = 38, label = "KIT", needs = "utility" },
    { name = "pause",    ax = 1, x = 56,  y = 56,  r = 30, label = "II" },
    { name = "objectives", ax = 0, x = 56, y = 56, r = 30, label = "OBJ" },
    { name = "light",    ax = 0, x = 56,  y = 132, r = 28, label = "LIGHT" },
}
Controls.stick_zone = 0.42      -- left share of the screen that spawns the floating stick
Controls.stick_radius = 90      -- canvas units for full deflection

local ACTIONS = { "fire", "aim", "reload", "switch", "interact", "tool", "utility", "light", "jump", "sprint", "crouch", "pause",
                  "objectives", "diagnostics", "quick_save", "quick_load", "skip",
                  "weapon1", "weapon2" }

local state = { frame = -1, move = vector.create(0, 0, 0), look = vector.create(0, 0, 0), down = {}, prev = {},
                touch_used = false, gamepad_used = false, mouse_used = false }
Controls.state = state

-- Finger tracking: id -> { role = "stick"|"look"|"button", start, last, button }
local fingers = {}
Controls.fingers = fingers
Controls.stick = nil -- { origin = vector(canvas), knob = vector(canvas) } while the stick finger is down

-- Autotest / cinematic injection: fields set here are merged into the frame state.
Controls.virtual = { move = nil, look = nil, down = {} }

local function canvas_size()
    local w, h = ui.screen_size()
    if not w or h <= 0 then return 1280, 720 end
    return 720 * w / h, 720
end
Controls.canvas_size = canvas_size

-- Comfort settings: the touch layout scales about its own corner (so a bigger layout never makes
-- two buttons overlap) and mirrors left to right for left-handed play.
local function tscale() return Game.clamp(Game.settings.touch_scale or 1, 0.8, 1.25) end
Controls.touch_scale = tscale
function Controls.mirrored() return Game.settings.left_handed == true end
function Controls.radius(b) return b.r * tscale() end
function Controls.stick_r() return Controls.stick_radius * tscale() end

function Controls.button_center(b, cw)
    local s = tscale()
    local x, y = b.x * s, b.y
    if y > 200 then
        y = 720 - (720 - y) * s -- thumb cluster: scale about the bottom corner
    else
        y = y * s               -- pause / objectives / light: scale about the top corner
    end
    local ax = b.ax
    if Controls.mirrored() then ax = 1 - ax end
    return ax == 1 and (cw - x) or x, y
end

-- Left-handed touch puts the thumb cluster under the squad roster and the objectives / light
-- column over the takedown feed, so the HUD moves those two blocks to the free side.
function Controls.hud_swap() return Controls.mirrored() and Controls.show_touch() end

-- Idle stick position (where the base rests until a thumb lands in the stick zone).
function Controls.stick_home(cw)
    local x = 220 * tscale()
    return Controls.mirrored() and (cw - x) or x, 720 - 250 * tscale()
end

-- Buttons tied to an inventory slot (KIT) only exist while that slot holds something.
function Controls.button_enabled(b)
    if not b.needs then return true end
    local inv = Game.inventory
    return inv ~= nil and inv.slots[b.needs] ~= nil
end

local function hit_button(cx, cy, cw)
    for _, b in Controls.buttons do
        if not Controls.button_enabled(b) then continue end
        local bx, by = Controls.button_center(b, cw)
        local dx, dy = cx - bx, cy - by
        if dx * dx + dy * dy <= (Controls.radius(b) * 1.15) ^ 2 then return b end
    end
    return nil
end
Controls.hit_button = hit_button

local function poll_touch(down)
    local n = input.touch_count()
    local cw, ch = canvas_size()
    local seen = {}
    local move = nil
    local look = vector.create(0, 0, 0)
    for i = 1, n do
        local t, id = input.touch(i)
        if t then
            state.touch_used = true
            local cx, cy = t.x * cw, t.y * ch
            local p = vector.create(cx, cy, 0)
            seen[id] = true
            local f = fingers[id]
            if not f then
                local b = hit_button(cx, cy, cw)
                if b then
                    f = { role = "button", button = b.name, start = p, last = p }
                elseif not Controls.stick and ((not Controls.mirrored() and t.x < Controls.stick_zone)
                        or (Controls.mirrored() and t.x > 1 - Controls.stick_zone)) then
                    f = { role = "stick", start = p, last = p }
                    Controls.stick = { origin = p, knob = p }
                else
                    f = { role = "look", start = p, last = p }
                end
                fingers[id] = f
            end
            if f.role == "stick" then
                local d = p - f.start
                local len = vector.magnitude(d)
                local r = Controls.stick_r()
                if len > r then
                    -- Drag the origin along so reversing direction is immediate.
                    f.start = f.start + d * ((len - r) / len)
                    d = p - f.start
                    len = r
                end
                Controls.stick.origin = f.start
                Controls.stick.knob = p
                move = vector.create(d.x / r, -d.y / r, 0)
                if len >= r * 0.98 and -d.y > r * 0.75 then down.sprint = true end
            elseif f.role == "look" or (f.role == "button" and f.button == "fire") then
                local d = p - f.last
                look = look + vector.create(d.x, d.y, 0)
            end
            if f.role == "button" then down[f.button] = true end
            f.last = p
        end
    end
    for id, f in fingers do
        if not seen[id] then
            if f.role == "stick" then Controls.stick = nil end
            fingers[id] = nil
        end
    end
    return move, look
end

function Controls.poll()
    local fr = time.frame()
    if state.frame == fr then return state end
    -- A gap in polling (new scene, window just shown, paused controller) starts a short mouse
    -- settle window: the first relative deltas after focus or pointer warps are not user input.
    if state.frame == nil or fr - state.frame > 1 then state.mouse_settle = 8 end
    state.frame = fr
    local prev = state.down
    state.prev = prev
    local down = {}
    -- Keyboard / mouse / gamepad through named project actions.
    for _, a in ACTIONS do
        if input.action(a) then down[a] = true end
    end
    local move = input.vector("move_x", "move_y")
    if vector.magnitude(move) > 0.05 then
        if input.gamepad_connected() then state.gamepad_used = true end
    end
    local s = Game.settings
    local dt = time.delta()
    local look = vector.create(0, 0, 0)
    -- Mouse: degrees per pixel.
    local md = input.mouse_delta()
    if (state.mouse_settle or 0) > 0 then
        state.mouse_settle -= 1
        md = vector.create(0, 0, 0)
    elseif math.abs(md.x) > 400 or math.abs(md.y) > 400 then
        md = vector.create(0, 0, 0) -- a pointer warp, not a hand movement
    end
    if md.x ~= 0 or md.y ~= 0 then state.mouse_used = true end
    look = look + vector.create(md.x, md.y, 0) * (0.11 * s.look_sensitivity)
    -- Gamepad right stick: response curve, degrees per second.
    local gx, gy = input.value("look_x"), -input.value("look_y")
    local gm = math.sqrt(gx * gx + gy * gy)
    if gm > 0 then
        local curve = gm ^ 1.8 / gm
        look = look + vector.create(gx * curve * 165, gy * curve * 120, 0) * (s.look_sensitivity * dt)
        state.gamepad_used = true
    end
    -- Touch: degrees per canvas unit.
    local tmove, tlook = poll_touch(down)
    if tmove then move = tmove end
    look = look + tlook * (0.16 * s.look_sensitivity)
    -- Injected input (autotests and cinematic handoff tests).
    local v = Controls.virtual
    if v.move then move = v.move end
    if v.look then look = look + v.look end
    for k, on in v.down do if on then down[k] = true end end
    if s.invert_y then look = vector.create(look.x, -look.y, 0) end
    if vector.magnitude(move) > 1 then move = vector.normalize(move) end
    state.move = move
    state.look = look
    state.down = down
    return state
end

function Controls.down(a) return Controls.poll().down[a] == true end
function Controls.pressed(a)
    local s = Controls.poll()
    return s.down[a] == true and s.prev[a] ~= true
end
function Controls.released(a)
    local s = Controls.poll()
    return s.down[a] ~= true and s.prev[a] == true
end
function Controls.move() return Controls.poll().move end
function Controls.look() return Controls.poll().look end

-- Whether to draw the touch overlay.
function Controls.show_touch()
    local mode = Game.settings.touch_controls
    if mode == "on" then return true end
    if mode == "off" then return false end
    return state.touch_used
end

return Controls
