-- SPECIAL OPS shared game state (one table shared by every script through require()).
-- Owns pause, cinematic input ownership, settings and small cross-script services.
local Game = {}

Game.paused = false          -- pause modal open
Game.cinematic = false       -- a cutscene owns the camera and input
Game.dialog_lock = false     -- reserved for modal dialogue choices
Game.autotest = false        -- set by the autotest driver
Game.player = nil            -- Player entity (set by fp_player)
Game.camera = nil            -- gameplay camera entity
Game.op = ""                 -- current operation id, e.g. "op01"

-- Settings with defaults; persisted with save.write("settings", ...).
Game.settings = {
    look_sensitivity = 1.0,
    aim_sensitivity = 0.6,
    invert_y = false,
    fov = 70,
    camera_shake = 1.0,     -- 0 disables shake and head bob
    head_bob = true,
    reticle_size = 1.0,
    reticle_opacity = 0.9,
    subtitles = true,
    subtitle_size = 26,
    subtitle_background = 0.55,
    touch_controls = "auto", -- auto / on / off
    master_volume = 1.0,
    music_volume = 0.7,
    sfx_volume = 0.9,
    voice_volume = 1.0,
    ambient_volume = 0.8,
    quality = "auto",
    diagnostics = false,
}

local loaded = false
function Game.load_settings()
    if loaded then return Game.settings end
    loaded = true
    if save.available() and save.exists("settings") then
        local s = save.read("settings")
        if type(s) == "table" then
            for k, v in s do
                if Game.settings[k] ~= nil and type(Game.settings[k]) == type(v) then Game.settings[k] = v end
            end
        end
    end
    Game.apply_audio()
    return Game.settings
end

function Game.save_settings()
    if save.available() then save.write("settings", Game.settings) end
    Game.apply_audio()
end

function Game.apply_audio()
    local s = Game.settings
    audio.set_volume("master", s.master_volume)
    audio.set_volume("music", s.music_volume)
    audio.set_volume("sfx", s.sfx_volume)
    audio.set_volume("voice", s.voice_volume)
    audio.set_volume("ambient", s.ambient_volume)
end

-- True while ordinary gameplay (movement, combat) should run.
function Game.playing()
    return not Game.paused and not Game.cinematic and not Game.dialog_lock
end

-- Campaign progress persisted in save "campaign".
Game.campaign = nil
function Game.progress()
    if Game.campaign then return Game.campaign end
    local c = nil
    if save.available() and save.exists("campaign") then c = save.read("campaign") end
    if type(c) ~= "table" then c = { op = "prologue", unlocked = { prologue = true }, flags = {} } end
    c.flags = c.flags or {}
    c.unlocked = c.unlocked or { prologue = true }
    Game.campaign = c
    return c
end

function Game.save_progress()
    if save.available() and Game.campaign then save.write("campaign", Game.campaign) end
end

function Game.flag(name) return Game.progress().flags[name] == true end
function Game.set_flag(name, v)
    Game.progress().flags[name] = (v ~= false)
end

-- Event bus between scripts (plain Lua callbacks; cleared when the scene changes).
local listeners = {}
local bus_scene = nil
local function check_scene()
    local cur = scene.current()
    if cur ~= bus_scene then listeners = {}; bus_scene = cur end
end
function Game.on(name, fn)
    check_scene()
    listeners[name] = listeners[name] or {}
    table.insert(listeners[name], fn)
end
function Game.emit(name, a, b, c)
    check_scene()
    local l = listeners[name]
    if not l then return end
    for _, fn in l do fn(a, b, c) end
end

-- Interactables: Game.register_interactable(entity, prompt, callback); the player's focus ray (or a
-- narrow cone fallback) picks the nearest enabled one. `detail` (optional) is a second HUD line.
Game.interactables = Game.interactables or {}
function Game.register_interactable(entity, prompt, fn)
    Game.interactables[entity.id] = { entity = entity, prompt = prompt, fn = fn, enabled = true }
end
function Game.set_interactable(entity, enabled, prompt)
    local r = Game.interactables[entity.id]
    if r then
        r.enabled = enabled
        if prompt then r.prompt = prompt end
    end
end

function Game.clamp(x, a, b) if x < a then return a elseif x > b then return b else return x end end
function Game.lerp(a, b, t) return a + (b - a) * t end
function Game.damp(a, b, k, dt) return a + (b - a) * (1 - math.exp(-k * dt)) end

return Game
