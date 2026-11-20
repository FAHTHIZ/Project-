-- Footsteps for the player and the cast: what is underfoot, how wet it is, and how loud a step is.
--
--   Footsteps.surface_at(pos, ignore) -> surface      "dirt" "grass" "gravel" "mud" "concrete" "metal" "wood"
--   Footsteps.step(pos, opts)                        plays one footfall (opts below), returns the surface
--   Footsteps.land(pos, fall_speed, opts)            both feet and kit after a drop
--
-- Surfaces come from a short ray down: on terrain the dominant splat layer picks the set (forest
-- floor = dirt, rock and trail = gravel, meadow = grass); on anything else the names of the hit
-- entity and its parents are matched against keywords (Mule, grate, stairs = metal; cabin, porch,
-- deck = wood), else concrete. In rain (the scene's Weather wetness, outdoors only) soft ground turns
-- to mud and some steps land in puddles. Sound files: tools/audio/build_sfx.py.
local Game = require("scripts/lib/game")

local Footsteps = {}

local TERRAIN_LAYER = { "dirt", "gravel", "gravel", "grass" } -- forest, rock, path, meadow
local METAL = { "mule", "hull", "bay", "hatch", "grate", "grating", "catwalk", "stair", "ladder", "container",
    "truck", "vehicle", "tower", "metal", "steel", "hood", "case", "tailgate" }
local WOOD = { "cabin", "porch", "deck", "plank", "wood", "pallet", "shack", "hut", "bench", "bridge" }
-- base loudness per surface (wet and hard surfaces carry further; grass is soft)
local LOUD = { dirt = 1.0, grass = 0.8, gravel = 1.25, mud = 1.15, concrete = 1.0, metal = 1.5, wood = 1.2 }
local VOL = { dirt = 1.0, grass = 0.85, gravel = 0.95, mud = 0.9, concrete = 0.9, metal = 0.85, wood = 1.0 }
Footsteps.LOUDNESS = LOUD

local cache = {}       -- entity id -> surface (non-terrain hits)
local cache_scene = nil
local weather = nil    -- { wet, puddles } for the current scene
local function check_scene()
    local cur = scene.current()
    if cur ~= cache_scene then
        cache = {}
        cache_scene = cur
        weather = nil
    end
end

local function matches(name, words)
    for _, w in words do
        if string.find(name, w, 1, true) then return true end
    end
    return false
end

local function classify(e)
    local id = e.id
    local c = cache[id]
    if c then return c end
    local s = "concrete"
    local x = e
    for _ = 1, 5 do
        if not (x and x.valid) then break end
        local n = string.lower(x.name or "")
        if string.find(n, "terrain", 1, true) then s = "terrain"; break end
        if matches(n, METAL) then s = "metal"; break end
        if matches(n, WOOD) then s = "wood"; break end
        x = x.parent
    end
    cache[id] = s
    return s
end

-- Rain on the ground: { wet = 0..1, puddles = 0..1 } (0 indoors or in dry scenes).
function Footsteps.weather()
    check_scene()
    if weather then return weather end
    weather = { wet = 0, puddles = 0 }
    local ok, list = pcall(function() return scene.query("Weather") end)
    if ok and list then
        for _, e in list do
            local w = e:get("Weather")
            if w then
                weather.wet = math.max(weather.wet, w.wetness or 0)
                weather.puddles = math.max(weather.puddles, w.puddles or 0)
            end
        end
    end
    return weather
end

local function outdoors()
    local st = Game.storm
    if st then return st.outdoor ~= false end
    return true
end

local function terrain_surface(pos)
    local ok, smp = pcall(function() return terrain.sample(pos.x, pos.z) end)
    if not (ok and smp and smp.weights) then return nil end
    local best, bw = 1, -1
    for i = 1, 4 do
        local w = smp.weights[i] or 0
        if w > bw then best, bw = i, w end
    end
    return TERRAIN_LAYER[best]
end

function Footsteps.surface_at(pos, ignore)
    check_scene()
    local hit = nil
    if physics.available() then
        hit = physics.raycast(pos + vector.create(0, 0.4, 0), vector.create(0, -1, 0), 1.6, nil, ignore)
    end
    local s = nil
    if hit and hit.entity and hit.entity.valid then
        s = classify(hit.entity)
        if s == "terrain" then s = terrain_surface(hit.point or pos) or "dirt" end
    else
        s = terrain_surface(pos) or "dirt"
    end
    return s
end

-- opts: surface (skip detection), ignore (entity for the ray), speed (m/s), crouched, sprint,
--       volume (scale), listener (world position; steps beyond 22 m are skipped), gear (kit rattle),
--       two_d (play at the listener, for the player's own feet)
-- returns the surface used and its loudness factor
function Footsteps.step(pos, opts)
    opts = opts or {}
    local s = opts.surface
    if not s or s == "auto" then s = Footsteps.surface_at(pos, opts.ignore) end
    local w = Footsteps.weather()
    local wet = outdoors() and w.wet or 0
    -- soft ground turns to mud in the rain
    if (s == "dirt" or s == "grass") and wet > 0.35 and math.random() < 0.35 + wet * 0.55 then s = "mud" end
    if opts.listener and vector.magnitude(pos - opts.listener) > 22 then return s, LOUD[s] or 1 end
    local speed = opts.speed or 2
    local base = opts.crouched and 0.35 or math.clamp(0.45 + speed * 0.09, 0.45, 1.0)
    local vol = base * (VOL[s] or 1) * (opts.volume or 1)
    local pitch = 0.92 + math.random() * 0.16 + (opts.crouched and -0.04 or 0)
    local play_at = opts.two_d and nil or pos
    audio.play("audio/foley/step_" .. s .. "_" .. math.random(0, 3) .. ".wav",
               { position = play_at, volume = vol, pitch = pitch, bus = "sfx", max_instances = 8 })
    -- puddles on hard or trodden ground, outdoors in rain
    if wet > 0.3 and w.puddles > 0 and s ~= "wood" and s ~= "metal" and math.random() < w.puddles * 0.4 then
        audio.play("audio/foley/step_splash_" .. math.random(0, 3) .. ".wav",
                   { position = play_at, volume = vol * 0.7, pitch = 0.9 + math.random() * 0.2, bus = "sfx", max_instances = 4 })
    end
    if opts.gear and not opts.crouched and speed > 4.2 and math.random() < 0.7 then
        audio.play("audio/foley/gear_" .. math.random(0, 2) .. ".wav",
                   { position = play_at, volume = 0.3 * (opts.volume or 1), pitch = 0.95 + math.random() * 0.1, bus = "sfx", max_instances = 3 })
    end
    return s, LOUD[s] or 1
end

function Footsteps.land(pos, fall_speed, opts)
    opts = opts or {}
    local heavy = fall_speed > 6.5
    local play_at = opts.two_d and nil or pos
    audio.play(heavy and "audio/foley/land_hard.wav" or "audio/foley/land_soft.wav",
               { position = play_at, volume = math.clamp(0.35 + fall_speed * 0.07, 0.35, 1.0), pitch = 0.95 + math.random() * 0.1,
                 bus = "sfx", max_instances = 2 })
    return Footsteps.step(pos, { surface = opts.surface, ignore = opts.ignore, speed = 5, volume = 0.8,
                                 two_d = opts.two_d })
end

return Footsteps
