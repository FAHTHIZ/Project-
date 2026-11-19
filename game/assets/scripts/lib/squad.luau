-- Halyard Team services: member registry, orders, formation slots, NPC fire and the shared
-- tracer pool. Operators (scripts/operator.luau) and Greyline contractors (scripts/enemy.luau)
-- register here; mission directors give orders through Squad.order / Squad.move.
local Game = require("scripts/lib/game")
local Combat = require("scripts/lib/combat")

local Squad = {}

-- Gameplay identity of each operator. Slots are (right, back) metres relative to the player's
-- facing; the lead walks closest, the scout ranges wider, comms trails.
Squad.ROSTER = {
    Anchor = { key = "anchor", name = "Anchor", role = "lead", slot = vector.create(-1.7, 0, 1.9), accuracy = 0.8,
               cadence = 1.0, speed = 3.6, emotion = "focus" },
    Patch = { key = "patch", name = "Patch", role = "medic", slot = vector.create(1.6, 0, 2.6), accuracy = 0.65,
              cadence = 1.25, speed = 3.5, emotion = "neutral" },
    Echo = { key = "echo", name = "Echo", role = "scout", slot = vector.create(-3.0, 0, 3.6), accuracy = 0.9,
             cadence = 0.9, speed = 3.9, emotion = "deadpan" },
    Tally = { key = "tally", name = "Tally", role = "comms", slot = vector.create(2.6, 0, 4.4), accuracy = 0.6,
              cadence = 1.2, speed = 3.4, emotion = "smile" },
}

local st = nil
function Squad.state()
    local cur = scene.current()
    if not st or st.scene ~= cur then
        st = { scene = cur, members = {}, order_list = {}, enemies = {}, tracers = {}, tracer_i = 1, mode = "follow",
               clock = 0 }
        for i = 0, 7 do
            local t = scene.find("NPC Tracer " .. i)
            if t then
                if t:has("MeshRenderer") then t:set_visible(false) end
                for _, c in t:children() do if c:has("MeshRenderer") then c:set_visible(false) end end
                table.insert(st.tracers, { e = t, life = 0 })
            end
        end
        Squad.members = st.members
        Squad.enemies = st.enemies
    end
    return st
end

function Squad.register(key, op)
    local s = Squad.state()
    s.members[key] = op
    table.insert(s.order_list, key)
end
function Squad.member(key) return Squad.state().members[key] end
function Squad.each(fn)
    local s = Squad.state()
    for _, k in s.order_list do
        local m = s.members[k]
        if m and m.entity.valid then fn(k, m) end
    end
end
function Squad.count()
    local n = 0
    Squad.each(function() n += 1 end)
    return n
end

function Squad.register_enemy(e, ctl) Squad.state().enemies[e.id] = { entity = e, ctl = ctl } end
function Squad.unregister_enemy(e) Squad.state().enemies[e.id] = nil end
function Squad.active_enemies()
    local out = {}
    for _, r in Squad.state().enemies do
        if r.entity.valid and r.ctl and not r.ctl.down then table.insert(out, r.ctl) end
    end
    return out
end

-- Orders -------------------------------------------------------------------------------------
-- mode: "follow" (formation on the player), "hold" (stay put), "move" (go to per-member points
-- and hold there). points: { Anchor = vector, ... } for "move".
function Squad.order(mode, points, opts)
    local s = Squad.state()
    s.mode = mode
    Squad.each(function(k, m)
        m:set_order(mode, points and points[k], opts)
    end)
    Game.emit("squad_order", mode)
end

function Squad.slot_point(who)
    local p = Game.player
    local r = Squad.ROSTER[who]
    if not p or not r then return nil end
    local ps = Game.player_state
    local yaw = ps and math.rad(ps.yaw) or 0
    -- player forward is -Z rotated by yaw; right is +X rotated by yaw
    local fwd = vector.create(-math.sin(yaw), 0, -math.cos(yaw))
    local right = vector.create(math.cos(yaw), 0, -math.sin(yaw))
    return p.position + right * r.slot.x - fwd * r.slot.z
end

-- NPC fire ------------------------------------------------------------------------------------
local function show_tracer(s, from, to)
    if #s.tracers == 0 then return end
    local t = s.tracers[s.tracer_i]
    s.tracer_i = s.tracer_i % #s.tracers + 1
    local len = vector.magnitude(to - from)
    if len < 0.5 then return end
    t.e.position = from
    t.e:look_at(to)
    t.e.scale = vector.create(1, 1, math.min(len, 6))
    t.from = from
    t.dir = (to - from) / len
    t.len = len
    t.t = 0
    t.life = math.min(0.09, 0.03 + len / 900)
    if t.e:has("MeshRenderer") then t.e:set_visible(true) end
    for _, c in t.e:children() do if c:has("MeshRenderer") then c:set_visible(true) end end
end

-- shooter: actor controller ({entity, actor}); aim: world point; opts: spread (deg), amount,
-- team ("squad"|"enemy"). Returns the hit table (or nil) and whether a combatant was struck.
function Squad.shoot(shooter, aim, opts)
    local s = Squad.state()
    local from = shooter.actor:muzzle_ray()
    local dir = aim - from
    local dist = vector.magnitude(dir)
    if dist < 0.1 then return nil, false end
    dir = dir / dist
    local spread = math.rad(opts.spread or 2)
    local up = vector.create(0, 1, 0)
    local right = vector.normalize(vector.cross(dir, up))
    local up2 = vector.cross(right, dir)
    local a = math.random() * math.pi * 2
    local rr = math.sqrt(math.random()) * math.tan(spread)
    local sdir = vector.normalize(dir + right * (math.cos(a) * rr) + up2 * (math.sin(a) * rr))
    local range = 60
    local hit = physics.raycast(from, sdir, range, nil, shooter.entity)
    local endp = from + sdir * range
    local struck = false
    if hit then
        endp = hit.point
        local e = hit.entity
        if opts.team == "enemy" and Game.player and e and e.id == Game.player.id then
            Game.hurt_player(opts.amount or 7, shooter.entity)
            struck = true
            Game.emit("player_shot_at", shooter.entity)
        elseif e then
            local h = Combat.handler_of(e)
            if h and h.entity.valid and h.entity.id ~= shooter.entity.id then
                local lp = hit.point.y - h.entity.world_position.y
                local zone = lp > 1.52 and "head" or "body"
                local amt = (opts.amount or 12) * (zone == "head" and 1.6 or 1)
                struck = h.fn({ amount = amt, point = hit.point, normal = hit.normal, dir = sdir,
                                source = shooter.entity, zone = zone, weapon = "npc", team = opts.team }) == true
            end
        end
    end
    show_tracer(s, from, endp)
    local cam = Game.camera
    if cam and vector.magnitude(from - cam.world_position) < 70 then
        audio.play(opts.sound or "audio/weapons/pc7_fire.wav",
                   { position = from, volume = opts.volume or 0.55, pitch = opts.pitch or (0.93 + math.random() * 0.1),
                     bus = "sfx", max_instances = 6 })
    end
    Combat.noise(from, 24, shooter.entity)
    -- near misses on the player make the threat readable
    if opts.team == "enemy" and Game.player and not struck and cam then
        local cp = cam.world_position
        local to_cam = cp - from
        local along = vector.dot(to_cam, sdir)
        if along > 0 and along < (hit and vector.magnitude(endp - from) or range) then
            local miss = vector.magnitude(to_cam - sdir * along)
            if miss < 1.6 then Game.emit("near_miss", from) end
        end
    end
    return hit, struck
end

function Squad.update(dt)
    local s = Squad.state()
    if Game.paused then return end
    s.clock += dt
    for _, t in s.tracers do
        if t.life > 0 then
            t.t += dt
            if t.t >= t.life then
                t.life = 0
                if t.e:has("MeshRenderer") then t.e:set_visible(false) end
                for _, c in t.e:children() do if c:has("MeshRenderer") then c:set_visible(false) end end
            else
                local k = t.t / t.life
                t.e.position = t.from + t.dir * (t.len * k * 0.7)
            end
        end
    end
end

return Squad
