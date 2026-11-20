-- Halyard Team services: member registry, orders, formation slots, NPC fire and the shared
-- tracer pool. Operators (scripts/operator.luau) and Greyline contractors (scripts/enemy.luau)
-- register here; mission directors give orders through Squad.order / Squad.move.
local Game = require("scripts/lib/game")
local Dialogue = require("scripts/lib/dialogue")
local Combat = require("scripts/lib/combat")

local Squad = {}

-- Gameplay identity of each operator. Slots are (right, back) metres relative to the player's
-- facing; the lead walks closest, the scout ranges wider, comms trails.
Squad.ROSTER = {
    Anchor = { key = "anchor", name = "Anchor", role = "lead", slot = vector.create(-1.7, 0, 1.9), accuracy = 0.8,
               cadence = 1.0, speed = 3.6, emotion = "focus" },
    Patch = { key = "patch", name = "Patch", role = "medic", slot = vector.create(1.6, 0, 2.6), accuracy = 0.65,
              cadence = 1.25, speed = 3.5, emotion = "neutral", weapon = "pdw", sound = "audio/weapons/kv5_fire.wav" },
    Echo = { key = "echo", name = "Echo", role = "scout", slot = vector.create(-3.0, 0, 3.6), accuracy = 0.9,
             cadence = 0.9, speed = 3.9, emotion = "deadpan", weapon = "dmr", sound = "audio/weapons/mr6_fire.wav" },
    Tally = { key = "tally", name = "Tally", role = "comms", slot = vector.create(2.6, 0, 4.4), accuracy = 0.6,
              cadence = 1.2, speed = 3.4, emotion = "smile" },
    -- Brick (story bible rev 2): breacher, walks at the back of the stack, slow but steady
    Brick = { key = "brick", name = "Brick", role = "breacher", slot = vector.create(-0.6, 0, 5.4), accuracy = 0.7,
              cadence = 1.4, speed = 3.3, emotion = "deadpan", weapon = "breacher", sound = "audio/weapons/br9_fire.wav" },
}

local st = nil
function Squad.state()
    local cur = scene.current()
    if not st or st.scene ~= cur then
        st = { scene = cur, members = {}, order_list = {}, enemies = {}, tracers = {}, tracer_i = 1, mode = "follow",
               clock = 0, crumbs = {} }
        -- open-world scenes (tools/world/world_scene.py) carry an "Open World" marker and no navmesh
        Game.open_world = scene.find("Open World") ~= nil
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
        if r.entity.valid and r.ctl and not r.ctl.down and not r.ctl.dormant then table.insert(out, r.ctl) end
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
        -- a pinned operator has a standing job (Brick guarding Venn) and ignores squad orders
        if not m.pinned then m:set_order(mode, points and points[k], opts) end
    end)
    Game.emit("squad_order", mode)
end

-- Open-world following (scenes without a navmesh): the player's recent path is kept as
-- breadcrumbs 1.2 m apart and each operator walks to the crumb its trail distance behind, so
-- the squad files along the trail the player actually walked instead of cutting through trees.
local CRUMB = 1.2
local function crumbs_update(s)
    local p = Game.player
    if not p or not p.valid then return end
    local pos = p.position
    local c = s.crumbs
    if #c == 0 or vector.magnitude(pos - c[#c]) > 25 then
        s.crumbs = { pos }
        return
    end
    if vector.magnitude(pos - c[#c]) >= CRUMB then
        table.insert(c, pos)
        if #c > 40 then table.remove(c, 1) end
    end
end

-- Point `back` metres behind the player along the breadcrumb path (nil when the path is shorter).
function Squad.trail_point(back)
    local s = Squad.state()
    local c = s.crumbs
    local p = Game.player
    if not p or #c == 0 then return nil end
    local prev = p.position
    local left = back
    for i = #c, 1, -1 do
        local seg = vector.magnitude(prev - c[i])
        if seg >= left and seg > 0.001 then
            return prev + (c[i] - prev) * (left / seg)
        end
        left -= seg
        prev = c[i]
    end
    return nil
end

function Squad.slot_point(who)
    local p = Game.player
    local r = Squad.ROSTER[who]
    if not p or not r then return nil end
    if Game.open_world then
        -- single file in trail order, a small lateral stagger so heads do not line up
        local back = 1.6 + r.slot.z * 1.15
        local tp = Squad.trail_point(back)
        if tp then
            local ahead = Squad.trail_point(math.max(0.2, back - 1.5)) or p.position
            local d = ahead - tp
            local len = math.sqrt(d.x * d.x + d.z * d.z)
            if len > 0.01 then
                local side = vector.create(-d.z / len, 0, d.x / len)
                tp = tp + side * (r.slot.x * 0.18)
            end
            return tp
        end
    end
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
    -- where the pulse lands: sparks (and dust off the ground) from the shared pooled emitters, with
    -- the impact sound only close by; nothing is spawned per shot
    if hit and cam and Game.weapons and Game.weapons.impact then
        local dcam = vector.magnitude(hit.point - cam.world_position)
        if dcam < 35 then
            -- quiet = true: Weapons:impact draws math.random for the sound pitch, and the NPC fights'
            -- shared random stream must not shift because a camera happened to be close
            Game.weapons:impact(hit, struck, true)
            if dcam < 14 then
                audio.play(struck and "audio/weapons/impact_hard.wav" or "audio/weapons/impact_soft.wav",
                           { position = hit.point, volume = 0.6, pitch = 0.9 + ((s.npc_impacts or 0) % 5) * 0.05,
                             bus = "sfx", max_instances = 4 })
            end
            s.npc_impacts = (s.npc_impacts or 0) + 1
        end
    end
    if cam and vector.magnitude(from - cam.world_position) < 70 then
        audio.play(opts.sound or "audio/weapons/pc7_fire.wav",
                   { position = from, volume = opts.volume or 0.55, pitch = opts.pitch or (0.93 + math.random() * 0.1),
                     bus = "sfx", max_instances = 6 })
    end
    Combat.noise(from, 24, shooter.entity)
    -- near misses on people close to the camera: a startle on the face (blink, brows) and stress
    if cam then
        local seg = endp - from
        local seg_len = vector.magnitude(seg)
        local function snap(ctl)
            local a = ctl and ctl.actor
            if not a or ctl == shooter or not ctl.entity or not ctl.entity.valid or ctl.down then return end
            local chest = ctl.entity.position + vector.create(0, 1.45, 0)
            if vector.magnitude(chest - cam.world_position) > 22 then return end
            local along = math.clamp(vector.dot(chest - from, sdir), 0, seg_len)
            if along < 1 then return end
            local miss = vector.magnitude(chest - (from + sdir * along))
            if miss < 1.3 then a:startle(miss < 0.6 and 1 or 0.6) end
        end
        for _, r in s.enemies do snap(r.ctl) end
        Squad.each(function(_, m) snap(m) end)
    end
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

-- After contact: once every contractor nearby is down or gone and nobody has been engaged for a
-- few seconds, the lead calls a sound-off and two of the team answer (hurt ones say so). Real
-- squads reorganise like this after a fight (status, casualties, ammunition) before moving on.
local CON_KEYS = { "echo", "tally", "patch", "brick" }
local function consolidate(s, dt)
    if not s.con_hooked then
        s.con_hooked = true
        Game.on("squad_contact", function() s.con_contact = true; s.con_quiet = 0 end)
        Game.on("operator_hit", function(key) s.con_hit = s.con_hit or {}; s.con_hit[key] = true end)
    end
    if not s.con_contact then return end
    local engaged = false
    Squad.each(function(_, m) if m.engaged then engaged = true end end)
    if engaged or #Squad.active_enemies() > 0 or Game.cinematic then s.con_quiet = 0; return end
    s.con_quiet = (s.con_quiet or 0) + dt
    if s.con_quiet < 3.0 or Dialogue.busy() then return end
    s.con_contact = false
    local lead = Dialogue.actor("anchor")
    if not lead or not lead.entity or not lead.entity.valid then s.con_hit = nil; return end
    s.con_n = (s.con_n or 0) + 1
    local ids = { "con_call_" .. ((s.con_n - 1) % 3 + 1) }
    local answered = 0
    local start = s.con_n % #CON_KEYS
    for i = 0, #CON_KEYS - 1 do
        local key = CON_KEYS[(start + i) % #CON_KEYS + 1]
        local a = Dialogue.actor(key)
        local hurt = s.con_hit and s.con_hit[key]
        if a and a.entity and a.entity.valid and (answered < 2 or hurt) then
            local id = hurt and ("con_hurt_" .. key .. "_1") or ("con_up_" .. key .. "_" .. ((s.con_n + i) % 2 + 1))
            table.insert(ids, { id, to = "anchor" })
            answered += 1
        end
    end
    table.insert(ids, "con_done_" .. ((s.con_n - 1) % 2 + 1))
    s.con_hit = nil
    Dialogue.conversation(ids, { priority = 1, gap = 0.45 })
    Game.emit("squad_sound_off", { n = answered })
end

function Squad.update(dt)
    local s = Squad.state()
    if Game.paused then return end
    s.clock += dt
    consolidate(s, dt)
    if Game.open_world then crumbs_update(s) end
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
