-- Squad reactions: the team notices what the player does and what happens around them, and says so
-- like people would (lines react_* in tools/dialogue/lines.py). Advanced by scripts/ensemble.luau.
--
-- Event reactions (Game.on):
--   friendly_hit(key)     the operator Rook just shot complains (speaker = that operator)
--   operator_hit(key)     an operator hit by Greyline fire calls it out
--   thunder(km, volume)   a close strike outdoors gets a comment when nothing else is going on
--   player_hurt / kit_used / enemy_down / hit_confirm / reload_started / dry_fire / player_jumped /
--   player_shot_at / near_miss / enemy_surrender / enemy_flanking
-- Per-frame detectors:
--   aiming down sights at a teammate, staring at one up close, walking into one, firing at
--   nothing, torch on or sprinting near contractors who have not noticed the squad, standing idle,
--   low cells while it's quiet, low health, the long wet walk.
-- Every reaction has a cooldown and needs its speaker present and within earshot, so lines never
-- come out of nowhere and never repeat in a loop. Story lines (priority >= 2) always win.
local Game = require("scripts/lib/game")
local Dialogue = require("scripts/lib/dialogue")
local Squad = require("scripts/lib/squad")
local Inventory = require("scripts/lib/inventory")

local R = {}

local st = nil
local function fresh()
    return {
        clock = 0, delayed = {}, aim = {}, stare = {}, bump_cd = {},
        shots = {}, last_hit = -100, last_target = -100, last_fire_at_player = -100, last_head = -100,
        downs = {}, jumps = {}, idle_t = 0, low_ammo_t = 0, wet_t = 0, last_pos = nil,
        fired = 0,
    }
end

function R.state()
    local cur = scene.current()
    if not st or st.scene ~= cur then
        st = fresh()
        st.scene = cur
    end
    return st
end

local function after(seconds, fn)
    local s = R.state()
    table.insert(s.delayed, { t = s.clock + seconds, fn = fn })
end

-- key -> operator controller, for operators that are in the scene and able to talk
local function op_of(key)
    local found = nil
    Squad.each(function(_, m) if m.key == key or (m.r and m.r.key == key) then found = m end end)
    return found
end

local function player_pos()
    return Game.player and Game.player.valid and Game.player.world_position or nil
end

local function bark(kind, opts)
    opts = opts or {}
    opts.prefix = "react_"
    if opts.near == nil and opts.speaker == nil then opts.near = player_pos(); opts.radius = opts.radius or 30 end
    if opts.speaker then
        -- a named speaker must be in the scene and within earshot of the player
        local m = op_of(opts.speaker)
        local p = player_pos()
        if not m or not p or vector.magnitude(m.entity.world_position - p) > (opts.radius or 30) then return false end
    end
    local ok = Dialogue.bark(kind, opts)
    if ok then Game.emit("squad_reaction", kind, opts.speaker) end
    return ok
end
R.bark = bark

local function engaged_near(p, radius)
    for _, e in Squad.active_enemies() do
        if e.state == "engage" and e.entity.valid and vector.magnitude(e.entity.world_position - p) < radius then
            return true
        end
    end
    return false
end

-- contractors up, not fighting and not yet aware of anyone
local function unaware_near(p, radius)
    for _, e in Squad.active_enemies() do
        if e.state == "patrol" and not e.parley and e.entity.valid and
            vector.magnitude(e.entity.world_position - p) < radius then
            return true
        end
    end
    return false
end
R.engaged_near = engaged_near

-- Awareness 0..1 for the HUD: 1 while anyone is shooting, ~0.5 while someone is searching.
function R.awareness()
    local a = 0
    for _, e in Squad.active_enemies() do
        if not e.parley then
            if e.state == "engage" then return 1 end
            if e.state == "alert" then a = math.max(a, 0.5) end
        end
    end
    return a
end

-- Relative bearing (degrees, -180..180, positive = to the player's right) of a world point.
local function bearing(p)
    local ps = Game.player_state
    if not ps or not ps.cam then return 0 end
    local origin, dir = ps:aim_ray()
    local d = p - origin
    local f = math.atan2(-dir.x, -dir.z)
    local g = math.atan2(-d.x, -d.z)
    local r = math.deg(f - g)
    while r > 180 do r -= 360 end
    while r < -180 do r += 360 end
    return r
end
R.bearing = bearing

-- shooter: the entity that hit the player (player_shot_at) or the muzzle position of a near miss
local function on_shot_from(shooter)
    if shooter == nil then return end
    local pos
    if type(shooter) == "vector" then pos = shooter
    elseif shooter.valid then pos = shooter.world_position
    else return end
    local s = R.state()
    s.last_fire_at_player = s.clock
    local b = bearing(pos)
    -- one directional callout at a time, and only for fire from outside the player's view
    if s.clock < (s.flank_cd or 0) or math.abs(b) < 55 then return end
    s.flank_cd = s.clock + 12
    if math.abs(b) > 125 then bark("behind", { cooldown = 14 })
    elseif b > 55 then bark("right", { cooldown = 14 })
    elseif b < -55 then bark("left", { cooldown = 14 }) end
end

function R.start()
    local s = R.state()
    Game.on("friendly_hit", function(key)
        local m = op_of(key)
        if m and m.actor and m.actor.face then m.actor.face:set_emotion("concern", 2.5) end
        bark("ff", { speaker = key, cooldown = 6, radius = 60 })
    end)
    Game.on("operator_hit", function(key)
        if math.random() < 0.55 then bark("hit", { speaker = key, cooldown = 9, radius = 60 }) end
    end)
    Game.on("thunder", function(km, volume)
        if (volume or 1) < 0.9 or km > 1.3 then return end
        local p = player_pos()
        if not p or engaged_near(p, 80) or Dialogue.busy() or math.random() > 0.55 then return end
        after(0.7 + math.random() * 0.6, function() bark("thunder", { cooldown = 120, radius = 20 }) end)
    end)
    Game.on("player_hurt", function(amount)
        local ps = Game.player_state
        if ps and ps.health > 0 and ps.health < 35 then
            bark("lowhp", { cooldown = 50 })
        elseif math.random() < 0.35 then
            bark("phurt", { cooldown = 25 })
        end
    end)
    Game.on("kit_used", function()
        after(1.0, function() bark("kit", { speaker = "patch", cooldown = 40, radius = 25 }) end)
    end)
    Game.on("hit_confirm", function(zone)
        s.last_hit = s.clock
        if zone == "head" then s.last_head = s.clock end
    end)
    Game.on("target_down", function() s.last_target = s.clock end)
    Game.on("enemy_down", function(e, source)
        if not (source and Game.player and source.id == Game.player.id) then return end
        table.insert(s.downs, s.clock)
        local n = 0
        for _, t in s.downs do if s.clock - t < 8 then n += 1 end end
        if s.clock - s.last_head < 0.3 then
            after(0.9, function() bark("head", { cooldown = 40 }) end)
        elseif n >= 2 then
            -- two or more down in quick succession: someone says something about it
            after(1.4, function() bark("pkill", { cooldown = 18 }) end)
        end
    end)
    Game.on("enemy_surrender", function()
        after(1.8, function() bark("surr", { cooldown = 25 }) end)
    end)
    Game.on("reload_started", function()
        local p = player_pos()
        if p and (s.clock - s.last_fire_at_player < 4 or engaged_near(p, 35)) then
            bark("cover", { cooldown = 14 })
        end
    end)
    Game.on("dry_fire", function(id)
        local sec = Inventory.in_slot("secondary")
        if sec and sec ~= id then bark("dry", { cooldown = 30 }) end
    end)
    Game.on("player_jumped", function()
        table.insert(s.jumps, s.clock)
        local n = 0
        for _, t in s.jumps do if s.clock - t < 6 then n += 1 end end
        if n >= 4 then
            s.jumps = {}
            local p = player_pos()
            if p and not engaged_near(p, 60) then bark("jump", { cooldown = 90 }) end
        end
    end)
    Game.on("player_fired", function()
        table.insert(s.shots, s.clock)
        s.fired += 1
    end)
    Game.on("enemy_flanking", function(e)
        local p = player_pos()
        if not p or not (e and e.valid) or vector.magnitude(e.world_position - p) > 50 then return end
        -- somebody on the team saw him go: a warning, not a radar
        after(1.0 + math.random() * 0.8, function()
            if e.valid then bark("eflank", { cooldown = 25 }) end
        end)
    end)
    Game.on("player_shot_at", on_shot_from)
    Game.on("near_miss", on_shot_from)
end

-- Per-frame checks ---------------------------------------------------------------------------

-- Distance from point q to the ray (origin, dir), and how far along the ray it is.
local function ray_dist(origin, dir, q)
    local v = q - origin
    local along = vector.dot(v, dir)
    if along <= 0 then return math.huge, along end
    return vector.magnitude(v - dir * along), along
end

local function ws_armed()
    local ws = Game.weapon_hud
    return ws ~= nil and ws.name ~= nil and ws.name ~= ""
end

function R.update(dt)
    local s = R.state()
    s.clock += dt
    for i = #s.delayed, 1, -1 do
        local d = s.delayed[i]
        if s.clock >= d.t then
            table.remove(s.delayed, i)
            if Game.playing() then d.fn() end
        end
    end
    local aw = R.awareness()
    Game.awareness_level = aw
    Game.awareness = aw >= 1 and "COMPROMISED" or (aw > 0 and "SEARCHING" or nil)
    local ps = Game.player_state
    local pl = Game.player
    if not Game.playing() or not ps or not ps.cam or not pl or not pl.valid then return end
    local p = pl.world_position
    local origin, dir = ps:aim_ray()
    local fight = engaged_near(p, 70)
    local zoom = ps.zoom or 0

    -- Teammates: muzzle on them, staring at them, walking into them.
    Squad.each(function(_, m)
        local key = m.key or (m.r and m.r.key)
        if not key then return end
        local mp = m.entity.world_position
        local chest = mp + vector.create(0, 1.25, 0)
        local off, along = ray_dist(origin, dir, chest)
        -- aimed: down sights (or hip for longer) with the muzzle line through their torso
        if along < 30 and off < 0.45 and ws_armed() then
            s.aim[key] = (s.aim[key] or 0) + dt * (zoom > 0.4 and 1 or 0.6)
            if s.aim[key] > 1.2 then
                s.aim[key] = -6
                if m.actor then m.actor:look_at(origin, 1.8) end
                bark("aimed", { speaker = key, cooldown = 20 })
            end
        elseif (s.aim[key] or 0) > 0 then
            s.aim[key] = math.max(0, s.aim[key] - dt * 2)
        end
        -- stare: close, not aiming, looking at their face for a while, nothing going on
        local head = mp + vector.create(0, 1.62, 0)
        local hoff, halong = ray_dist(origin, dir, head)
        if not fight and zoom < 0.3 and halong < 4 and hoff < 0.35 then
            s.stare[key] = (s.stare[key] or 0) + dt
            if s.stare[key] > 2.6 then
                s.stare[key] = -20
                if m.actor then m.actor:look_at(origin, 2.5) end
                bark("stare", { speaker = key, cooldown = 45 })
            end
        elseif (s.stare[key] or 0) > 0 then
            s.stare[key] = math.max(0, s.stare[key] - dt * 3)
        end
        -- bump: walking into them
        local flat = vector.create(mp.x - p.x, 0, mp.z - p.z)
        if vector.magnitude(flat) < 0.8 and math.abs(mp.y - p.y) < 1.2 and (ps.ground_speed or 0) > 1.6 and not fight then
            if s.clock > (s.bump_cd[key] or 0) then
                s.bump_cd[key] = s.clock + 25
                if m.actor then m.actor:look_at(origin, 1.2) end
                bark("bump", { speaker = key, cooldown = 25 })
            end
        end
    end)

    -- Firing at nothing: a long string of shots with no enemy or target anywhere.
    for i = #s.shots, 1, -1 do if s.clock - s.shots[i] > 4 then table.remove(s.shots, i) end end
    if #s.shots >= 9 and not fight and #Squad.active_enemies() == 0 and s.clock - s.last_hit > 10 and
        s.clock - s.last_target > 20 then
        s.shots = {}
        bark("waste", { cooldown = 70 })
    end

    -- Giving away the approach.
    if not fight then
        if ps.torch_on and unaware_near(p, 38) then bark("light", { cooldown = 50 }) end
        if ps.sprinting and unaware_near(p, 24) then bark("sprint", { cooldown = 45 }) end
    end

    -- Standing still for a long time with nothing happening.
    local moved = s.last_pos and vector.magnitude(p - s.last_pos) > 0.05
    s.last_pos = p
    if moved or fight or Dialogue.busy() or Game.cinematic then s.idle_t = 0 else s.idle_t += dt end
    if s.idle_t > 75 then
        s.idle_t = 0
        bark("idle", { cooldown = 150, radius = 25 })
    end

    -- Low cells while it's quiet.
    local ws = Game.weapon_hud
    if ws and ws.state == "LOW" and not fight and s.clock - s.last_fire_at_player > 8 then
        s.low_ammo_t += dt
        if s.low_ammo_t > 7 then
            s.low_ammo_t = -60
            bark("reloadp", { cooldown = 90 })
        end
    elseif s.low_ammo_t > 0 then
        s.low_ammo_t = 0
    end

    -- The long wet walk: an occasional remark about the weather, outdoors in the storm only.
    if Game.storm and Game.storm.outdoor and moved and not fight and not Dialogue.busy() then
        s.wet_t += dt
        if s.wet_t > 240 then
            s.wet_t = 0
            if math.random() < 0.6 then bark("rain", { cooldown = 300, radius = 18 }) end
        end
    end
end

return R
