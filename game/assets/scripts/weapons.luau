-- SPECIAL OPS first-person weapons and field device.
-- Attached to the Viewmodel entity (child of Main Camera, built by tools/scenes/rig.py):
--   Viewmodel (this script)
--     VM Pivot                         sway / bob / recoil / sprint / reload pose
--       Carbine | Sidearm              weapon roots (local frame: muzzle along -Z)
--         <W> Body, <W> Cell, <W> Slide (sidearm), <W> Hand R, <W> Hand L, <W> Muzzle (Light)
--           <W> Flash                  emissive muzzle bloom
--       Device                         field scanner in the left hand (tool action)
--   World entities: "Tracer 0..3" (pulse bolts), "Impact Sparks", "Impact Dust" (particles).
--
-- The weapons are fictional stun-pulse emitters with invented, abstract values. All motion is
-- procedural (springs and easing curves), so it costs a few transforms per frame.
-- Writes Game.weapon_hud { name, ammo, reserve, state, spread }, Game.tool_hud, and the
-- player's zoom / zoom_fov (read by fp_player.luau for FOV, speed and look sensitivity).
local Game = require("scripts/lib/game")
local Controls = require("scripts/lib/controls")
local Combat = require("scripts/lib/combat")

local V = vector.create

local DEFS = {
    carbine = {
        id = "carbine", label = "PC-7 LANTERN", root = "Carbine",
        mag = 30, reserve = 150, max_reserve = 240, interval = 0.095, auto = true,
        stun = 22, head_mult = 1.8, range = 140,
        spread_hip = 1.6, spread_ads = 0.18, spread_move = 1.6, bloom = 0.35, bloom_max = 2.4,
        kick_pitch = 0.62, kick_yaw = 0.28, ads_kick = 0.55, kick_back = 0.028, kick_rot = 3.2,
        reload = 1.75, reload_empty = 2.25, equip = 0.38, lower = 0.2,
        hip = V(0.15, -0.165, -0.40), ads = V(0, -0.1135, -0.30), hip_rot = V(1.5, 3.5, 0), zoom_fov = 0.72,
        muzzle = V(0, 0.045, -0.52), cell = V(0, 0, 0),
        fire = "audio/weapons/pc7_fire.wav", cell_out = "audio/weapons/pc7_cell_out.wav",
        cell_in = "audio/weapons/pc7_cell_in.wav", charge = "audio/weapons/pc7_charge.wav", noise = 38,
    },
    sidearm = {
        id = "sidearm", label = "SP-2 WREN", root = "Sidearm",
        mag = 12, reserve = 48, max_reserve = 96, interval = 0.16, auto = false,
        stun = 30, head_mult = 1.8, range = 80,
        spread_hip = 1.9, spread_ads = 0.3, spread_move = 1.4, bloom = 0.7, bloom_max = 2.6,
        kick_pitch = 1.05, kick_yaw = 0.35, ads_kick = 0.6, kick_back = 0.02, kick_rot = 6.0,
        reload = 1.3, reload_empty = 1.6, equip = 0.3, lower = 0.16,
        hip = V(0.13, -0.14, -0.36), ads = V(0, -0.0615, -0.30), hip_rot = V(2, 5, 0), zoom_fov = 0.85,
        muzzle = V(0, 0.012, -0.16), cell = V(0, 0, 0),
        fire = "audio/weapons/sp2_fire.wav", cell_out = "audio/weapons/sp2_cell_out.wav",
        cell_in = "audio/weapons/sp2_cell_in.wav", charge = "audio/weapons/sp2_charge.wav", noise = 26,
    },
}
local ORDER = { "carbine", "sidearm" }

local W = {}
W.scan_cooldown = 6.0
W.scan_range = 40

local function find(root, name)
    local queue = { root }
    while #queue > 0 do
        local e = table.remove(queue, 1)
        if e.name == name then return e end
        for _, c in e:children() do table.insert(queue, c) end
    end
    return nil
end

-- set_visible applies to one renderer: walk the subtree and remember the last state per root.
local vis_cache = {}
local function setvis(e, v)
    if not e or vis_cache[e.id] == v then return end
    vis_cache[e.id] = v
    local queue = { e }
    while #queue > 0 do
        local x = table.remove(queue)
        vis_cache[x.id] = v
        if x:has("MeshRenderer") then x:set_visible(v) end
        for _, c in x:children() do table.insert(queue, c) end
    end
end
local function isvis(e) return vis_cache[e.id] == true end

local function smooth(x) x = Game.clamp(x, 0, 1); return x * x * (3 - 2 * x) end
-- 0 -> 1 -> 0 bump over [a, b].
local function bump(t, a, b)
    if t <= a or t >= b then return 0 end
    return math.sin(math.pi * (t - a) / (b - a))
end
local function play(clip, vol, pitch, pos)
    audio.play(clip, { volume = vol or 1, pitch = pitch or 1, bus = "sfx", max_instances = 4, position = pos })
end

function W:start()
    vis_cache = {}
    Game.load_settings()
    self.was_cin = false
    Game.weapons = self
    self.pivot = find(self.entity, "VM Pivot")
    self.w = {}
    for id, d in DEFS do
        local root = self.pivot and find(self.pivot, d.root)
        if root then
            local r = { def = d, root = root, ammo = d.mag, reserve = d.reserve,
                        cell = find(root, d.root .. " Cell"), slide = find(root, d.root .. " Slide"),
                        hand_l = find(root, d.root .. " Hand L"), muzzle = find(root, d.root .. " Muzzle"),
                        flash = find(root, d.root .. " Flash") }
            r.cell_home = r.cell and r.cell.position or V(0, 0, 0)
            r.hand_home = r.hand_l and r.hand_l.position or V(0, 0, 0)
            r.hand_rot = r.hand_l and r.hand_l.rotation or V(0, 0, 0)
            r.slide_home = r.slide and r.slide.position or V(0, 0, 0)
            setvis(root, false)
            self.w[id] = r
        end
    end
    self.device = self.pivot and find(self.pivot, "Device")
    if self.device then
        self.device_home = self.device.position
        setvis(self.device, false)
    end
    self.tracers = {}
    for i = 0, 7 do
        local t = scene.find("Tracer " .. i)
        if t then setvis(t, false); table.insert(self.tracers, { e = t, t = 0, life = 0 }) end
    end
    self.tracer_i = 1
    self.sparks = scene.find("Impact Sparks")
    self.dust = scene.find("Impact Dust")
    -- Loadout: which weapons the player carries this operation (directors may change it).
    local lo = Game.loadout or { carbine = true, sidearm = true }
    Game.loadout = lo
    self.current = nil
    self.pending = nil
    for _, id in ORDER do if lo[id] and self.w[id] then self.pending = id; break end end
    self.state = "idle"     -- idle | equip | lower | reload | holstered
    self.st = 0             -- time in state
    self.cooldown = 0
    self.bloom = 0
    self.zoom = 0
    self.aim_toggle = false
    self.sway = V(0, 0, 0)
    self.sway_v = V(0, 0, 0)
    self.kick = 0           -- recoil spring (position back)
    self.kick_v = 0
    self.kick_rot = 0
    self.recoil_debt = 0    -- camera pitch to recover
    self.flash_t = 0
    self.sprint = 0
    self.retract = 0
    self.lower_amt = 1      -- 1 = fully lowered (start of equip)
    self.trigger_held = false
    self.scan_t = 99
    self.scan_anim = 0
    self.last_scan = 0
    self.shots = 0
    self.hits = 0
    if self.pending then self:begin_equip(self.pending) end
end

-- Public API ---------------------------------------------------------------------------------

function W:visible(id) local r = self.w[id]; return r ~= nil and isvis(r.root) end

function W:weapon() return self.current and self.w[self.current] end

function W:give(id, ammo)
    local r = self.w[id]
    if not r then return false end
    if not Game.loadout[id] then
        Game.loadout[id] = true
        if not self.current then self:begin_equip(id) end
    end
    if ammo then r.reserve = math.min(r.def.max_reserve, r.reserve + ammo) end
    return true
end

function W:refill()
    for _, r in self.w do r.reserve = r.def.max_reserve; r.ammo = r.def.mag end
end

function W:save_state()
    local s = { current = self.current, loadout = Game.loadout, ammo = {} }
    for id, r in self.w do s.ammo[id] = { r.ammo, r.reserve } end
    return s
end

function W:load_state(s)
    if type(s) ~= "table" then return end
    if s.loadout then Game.loadout = s.loadout end
    for id, a in (s.ammo or {}) do
        local r = self.w[id]
        if r then r.ammo, r.reserve = a[1], a[2] end
    end
    if s.current and self.w[s.current] and s.current ~= self.current then
        if self.current then setvis(self.w[self.current].root, false) end
        self.current = nil
        self:begin_equip(s.current)
    end
end

Game.give_ammo = function(id, n) if Game.weapons then return Game.weapons:give(id, n) end return false end

-- State machine --------------------------------------------------------------------------------

function W:begin_equip(id)
    local r = self.w[id]
    if not r then return end
    if self.current and self.w[self.current] then setvis(self.w[self.current].root, false) end
    self.current = id
    self.pending = nil
    setvis(r.root, true)
    self:reset_parts(r)
    self.state = "equip"
    self.st = 0
    self.lower_amt = 1
    play("audio/weapons/equip.wav", 0.7)
end

function W:begin_switch(id)
    if id == self.current or not self.w[id] or not Game.loadout[id] then return end
    if self.state == "lower" then self.pending = id; return end
    self.pending = id
    self.state = "lower"
    self.st = 0
end

function W:begin_reload()
    local r = self:weapon()
    if not r or self.state ~= "idle" then return false end
    if r.ammo >= r.def.mag or r.reserve <= 0 then return false end
    self.state = "reload"
    self.st = 0
    self.reload_len = r.ammo == 0 and r.def.reload_empty or r.def.reload
    self.reload_empty = r.ammo == 0
    self.reload_sfx = 0
    return true
end

function W:reset_parts(r)
    if r.cell then r.cell.position = r.cell_home; setvis(r.cell, true) end
    if r.hand_l then r.hand_l.position = r.hand_home; r.hand_l.rotation = r.hand_rot end
    if r.slide then r.slide.position = r.slide_home end
    if r.flash then setvis(r.flash, false) end
    if r.muzzle then self:set_flash_light(r, 0) end
end

function W:set_flash_light(r, intensity)
    local m = r.muzzle
    if not m then return end
    local l = m:get("Light")
    if l then
        if (intensity > 0) ~= (r.light_on == true) or math.abs((r.light_i or 0) - intensity) > 0.5 then
            l.intensity = intensity
            m:set("Light", l)
            r.light_on = intensity > 0
            r.light_i = intensity
        end
    end
end

-- Firing ---------------------------------------------------------------------------------------

function W:spread_now(ps)
    local d = self:weapon().def
    local move = Game.clamp((ps.ground_speed or 0) / 3.6, 0, 1.5)
    local base = Game.lerp(d.spread_hip + d.spread_move * move, d.spread_ads + d.spread_move * 0.25 * move, self.zoom)
    if not Game.player.grounded then base += 2.5 end
    if ps.crouched then base *= 0.75 end
    return base + self.bloom
end

function W:fire(ps)
    local r = self:weapon()
    local d = r.def
    if r.ammo <= 0 then
        play("audio/weapons/dry.wav", 0.8)
        self.cooldown = 0.25
        if r.reserve > 0 then self:begin_reload() end
        return
    end
    r.ammo -= 1
    self.cooldown = d.interval
    self.shots += 1
    Combat.stats.shots += 1
    local origin, dir = ps:aim_ray()
    -- Random cone spread (degrees).
    local spread = math.rad(self:spread_now(ps))
    local a = math.random() * math.pi * 2
    local rr = math.sqrt(math.random()) * math.tan(spread)
    local right = ps.cam.right
    local up = ps.cam.up
    local sdir = vector.normalize(dir + right * (math.cos(a) * rr) + up * (math.sin(a) * rr))
    local hit = physics.raycast(origin, sdir, d.range, nil, Game.player)
    local endp = origin + sdir * d.range
    if hit then
        endp = hit.point
        local zone = "body"
        local h = Combat.handler_of(hit.entity)
        if h and h.entity.valid then
            -- Head zone: hits above 1.5 m on an upright humanoid or marked head colliders.
            local lp = hit.point.y - h.entity.world_position.y
            if hit.entity.name:find("Head") or lp > 1.52 then zone = "head" end
            local amount = d.stun * (zone == "head" and d.head_mult or 1)
            local ok = h.fn({ amount = amount, point = hit.point, normal = hit.normal, dir = sdir,
                              source = Game.player, zone = zone, weapon = d.id })
            if ok then
                self.hits += 1
                Combat.stats.hits += 1
                Game.emit("hit_confirm", zone)
                audio.play("audio/ui/hit_tick.wav", { volume = zone == "head" and 0.75 or 0.5, bus = "ui",
                                                     pitch = zone == "head" and 1.25 or 1, max_instances = 3 })
            end
            self:impact(hit, true)
        else
            self:impact(hit, false)
        end
    end
    self:tracer(r, endp)
    -- Feedback: camera recoil, viewmodel kick, flash, sound, noise for AI.
    local ads = Game.lerp(1, d.ads_kick, self.zoom)
    local kp = d.kick_pitch * ads * (0.85 + math.random() * 0.3)
    ps.pitch = Game.clamp(ps.pitch + kp, -ps.pitch_limit, ps.pitch_limit)
    ps.yaw += (math.random() * 2 - 1) * d.kick_yaw * ads
    self.recoil_debt += kp * 0.7
    self.kick_v += d.kick_back * 38 * ads
    self.kick_rot += d.kick_rot * ads
    self.bloom = math.min(d.bloom_max, self.bloom + d.bloom * Game.lerp(1, 0.4, self.zoom))
    self.flash_t = 0.05
    if r.flash then setvis(r.flash, true); r.flash.rotation = V(0, 0, math.random() * 360) end
    self:set_flash_light(r, 9)
    if r.slide then self.slide_t = 0.09 end
    ps:add_shake(0.06 * ads)
    play(d.fire, 0.95, 0.95 + math.random() * 0.1)
    Combat.noise(Game.player.world_position, d.noise, Game.player)
    Game.emit("player_fired", d.id)
    if r.ammo == 0 and r.reserve > 0 then self.auto_reload = 0.35 end
end

function W:tracer(r, endp)
    if #self.tracers == 0 or not r.muzzle then return end
    local t = self.tracers[self.tracer_i]
    self.tracer_i = self.tracer_i % #self.tracers + 1
    local from = r.muzzle.world_position
    local len = vector.magnitude(endp - from)
    if len < 0.5 then return end
    t.from = from
    t.dir = (endp - from) / len
    t.len = len
    t.t = 0
    t.life = math.min(0.09, 0.03 + len / 900)
    t.e.position = from
    t.e:look_at(endp)
    t.e.scale = V(1, 1, math.min(len, 6))
    setvis(t.e, true)
end

function W:impact(hit, on_target)
    local n = hit.normal
    local p = hit.point + n * 0.02
    -- Emitters emit along their local +Y: point +Y along the surface normal.
    local pitch = math.deg(math.asin(Game.clamp(n.z, -1, 1)))
    local roll = -math.deg(math.atan2(n.x, n.y))
    local rot = V(pitch, 0, roll)
    if self.sparks then
        self.sparks.position = p
        self.sparks.rotation = rot
        self.sparks:emit_particles(on_target and 14 or 8)
    end
    if self.dust and not on_target then
        self.dust.position = p
        self.dust.rotation = rot
        self.dust:emit_particles(5)
    end
    play(on_target and "audio/weapons/impact_hard.wav" or "audio/weapons/impact_soft.wav", 0.7,
         0.9 + math.random() * 0.2, hit.point)
end

-- Field device (scanner) -----------------------------------------------------------------------

function W:scan()
    if self.scan_t < self.scan_cooldown then return false end
    self.scan_t = 0
    self.scan_anim = 0.001
    play("audio/foley/scan.wav", 0.8)
    local origin = Game.player.world_position
    local found = 0
    for _, e in scene.tagged("Scannable") do
        if e.valid and vector.magnitude(e.world_position - origin) < self.scan_range then
            found += 1
            Game.emit("scanned", e)
        end
    end
    self.last_scan = found
    Game.emit("scan", origin, found)
    return true
end

-- Per frame ------------------------------------------------------------------------------------

function W:update(dt)
    local ps = Game.player_state
    if not ps or not self.pivot then return end
    local playing = Game.playing()
    local cin = Game.cinematic
    if cin ~= self.was_cin then
        self.was_cin = cin
        vis_cache = {}
        setvis(self.entity, false)
        if not cin and self:weapon() then
            setvis(self:weapon().root, true)
            self:reset_parts(self:weapon())
        end
    end
    self.scan_t += dt
    if self.scan_anim > 0 and not self.scan_hold then
        self.scan_anim += dt
        if self.scan_anim > 1.3 then self.scan_anim = 0 end
    end
    local r = self:weapon()
    if not r then
        Game.weapon_hud = nil
        ps.zoom = 0
        self:tool_hud()
        return
    end
    local d = r.def
    if not self.hold_pose then self.st += dt end -- hold_pose: screenshot tests freeze an animation
    self.cooldown = math.max(0, self.cooldown - dt)

    -- Input.
    local touch = Controls.state.touch_used
    if playing then
        if Controls.pressed("switch") then
            local idx = 1
            for i, id in ORDER do if id == self.current then idx = i end end
            for k = 1, #ORDER do
                local id = ORDER[(idx + k - 1) % #ORDER + 1]
                if Game.loadout[id] and self.w[id] and id ~= self.current then self:begin_switch(id); break end
            end
        end
        if Controls.pressed("weapon1") then self:begin_switch("carbine") end
        if Controls.pressed("weapon2") then self:begin_switch("sidearm") end
        if Controls.pressed("reload") then self:begin_reload() end
        if Controls.pressed("tool") then self:scan() end
        if touch then
            if Controls.pressed("aim") then self.aim_toggle = not self.aim_toggle end
        else
            self.aim_toggle = false
        end
    end
    local aiming = playing and (self.aim_toggle or (not touch and Controls.down("aim")))
    if self.state == "reload" or self.state == "lower" or self.state == "equip" or ps.sprinting then aiming = false end
    if ps.sprinting then self.aim_toggle = false end

    -- State progression.
    if self.state == "equip" then
        self.lower_amt = 1 - smooth(self.st / d.equip)
        if self.st >= d.equip then self.state = "idle"; self.lower_amt = 0 end
    elseif self.state == "lower" then
        self.lower_amt = smooth(self.st / d.lower)
        if self.st >= d.lower then self:begin_equip(self.pending) end
    elseif self.state == "reload" then
        local u = self.st / self.reload_len
        if self.reload_sfx == 0 and u > 0.18 then play(d.cell_out, 0.8); self.reload_sfx = 1 end
        if self.reload_sfx == 1 and u > 0.58 then play(d.cell_in, 0.85); self.reload_sfx = 2 end
        if self.reload_sfx == 2 and u > 0.7 then play(d.charge, 0.6); self.reload_sfx = 3 end
        if u >= 1 then
            local need = d.mag - r.ammo
            local take = math.min(need, r.reserve)
            r.ammo += take
            r.reserve -= take
            self.state = "idle"
            self:reset_parts(r)
            Game.emit("reloaded", d.id)
        end
    end
    if self.auto_reload then
        self.auto_reload -= dt
        if self.auto_reload <= 0 then self.auto_reload = nil; self:begin_reload() end
    end

    -- Fire.
    local trig = playing and Controls.down("fire")
    local can_fire = self.state == "idle" and self.cooldown <= 0 and not cin
    if trig and can_fire and self.sprint < 0.4 then
        if d.auto or not self.trigger_held then self:fire(ps) end
    end
    self.trigger_held = trig

    -- Aim blend.
    self.zoom = Game.damp(self.zoom, aiming and 1 or 0, aiming and 14 or 11, dt)
    if self.zoom < 0.002 then self.zoom = 0 end
    ps.zoom = self.zoom
    ps.zoom_fov = Game.settings.fov * d.zoom_fov
    if aiming and not self.was_aiming then play("audio/weapons/aim.wav", 0.5) end
    self.was_aiming = aiming

    -- Recoil recovery: return most of the camera kick when the trigger is released.
    self.bloom = Game.damp(self.bloom, 0, trig and 2.5 or 7, dt)
    if not trig and self.recoil_debt > 0 then
        local back = math.min(self.recoil_debt, self.recoil_debt * (1 - math.exp(-9 * dt)) + 0.2 * dt)
        ps.pitch -= back
        self.recoil_debt -= back
    end
    if trig then self.recoil_debt = math.min(self.recoil_debt, 6) end

    -- Muzzle flash and tracers.
    if self.flash_t > 0 then
        self.flash_t -= dt
        if self.flash_t <= 0 then
            if r.flash then setvis(r.flash, false) end
            self:set_flash_light(r, 0)
        else
            self:set_flash_light(r, 9 * self.flash_t / 0.05)
        end
    end
    for _, t in self.tracers do
        if t.life > 0 then
            t.t += dt
            if t.t >= t.life then
                t.life = 0
                setvis(t.e, false)
            else
                local k = t.t / t.life
                local seg = math.min(t.len, 6)
                local head = math.min(t.len, t.len * k + seg * 0.5)
                t.e.position = t.from + t.dir * math.max(0, head - seg)
            end
        end
    end

    -- Viewmodel pose -----------------------------------------------------------------------------
    local look = Controls.look()
    if not playing then look = V(0, 0, 0) end
    -- Sway: spring toward the negative look delta (weapon lags behind the view).
    local target = V(Game.clamp(-look.x * 0.0035, -0.03, 0.03), Game.clamp(look.y * 0.0035, -0.03, 0.03), 0)
    local k, c = 140, 16
    local acc = (target - self.sway) * k - self.sway_v * c
    self.sway_v += acc * dt
    self.sway += self.sway_v * dt
    -- Recoil spring.
    local kacc = -self.kick * 260 - self.kick_v * 24
    self.kick_v += kacc * dt
    self.kick += self.kick_v * dt
    self.kick_rot = Game.damp(self.kick_rot, 0, 16, dt)
    -- Sprint and wall retract.
    self.sprint = Game.damp(self.sprint, (ps.sprinting and self.state ~= "reload") and 1 or 0, 9, dt)
    local cp, adir = ps:aim_ray()
    local wall = physics.raycast(cp, adir, 0.75, nil, Game.player)
    local rt = 0
    if wall and wall.distance < 0.75 then rt = 1 - wall.distance / 0.75 end
    self.retract = Game.damp(self.retract, rt, 12, dt)
    -- Bob follows the player's head bob phase.
    local bob = ps.bob or 0
    local spd = Game.clamp((ps.ground_speed or 0) / ps.walk_speed, 0, 1.6)
    local bscale = spd * (1 - self.zoom * 0.9) * (Game.settings.head_bob and 1 or 0.3)
    local bx = math.sin(bob) * 0.006 * bscale
    local by = -math.abs(math.cos(bob)) * 0.005 * bscale
    -- Idle breathing.
    local tn = time.now()
    local breathe = math.sin(tn * 1.6) * 0.0016 * (1 - self.zoom * 0.8)
    -- Compose.
    local zoom = smooth(self.zoom)
    local base = d.hip + (d.ads - d.hip) * zoom
    local sw = self.sway * (1 - zoom * 0.7)
    local pos = base + V(sw.x + bx, sw.y + by + breathe, 0)
    local rot = (d.hip_rot or V(0, 0, 0)) * (1 - zoom) + V(sw.y * 300 + self.kick_rot * (1 - zoom * 0.6), sw.x * -300, sw.x * 400)
    pos += V(0, 0, self.kick)
    -- Sprint pose: tilt the weapon down and across the body.
    local s = smooth(self.sprint)
    pos += V(-0.03 * s, -0.035 * s, 0.03 * s)
    rot += V(-14 * s, 28 * s, 10 * s)
    -- Wall retract: pull back and tilt up.
    local w = smooth(self.retract)
    pos += V(0.01 * w, -0.02 * w, 0.09 * w)
    rot += V(18 * w, 10 * w, 0)
    -- Equip/switch lower.
    local lw = self.lower_amt
    pos += V(0.02 * lw, -0.26 * lw, 0.05 * lw)
    rot += V(-40 * lw, 8 * lw, 0)
    -- Reload choreography: dip and roll the weapon, the support hand pulls and seats the cell.
    if self.state == "reload" then
        local u = Game.clamp(self.st / self.reload_len, 0, 1)
        local dip = smooth(u / 0.18) * (1 - smooth((u - 0.82) / 0.18))
        pos += V(-0.02 * dip, -0.04 * dip, 0.02 * dip)
        rot += V(8 * dip, 6 * dip, 24 * dip)
        if r.cell and r.hand_l then
            -- 0.15..0.30 hand to cell, 0.30..0.45 cell out and away, 0.45..0.58 new cell up,
            -- 0.58..0.68 seat, 0.68..0.85 hand back (charge whine), empty reloads add a tap.
            local out = smooth((u - 0.30) / 0.15) * (1 - smooth((u - 0.45) / 0.13))
            local seat = smooth((u - 0.45) / 0.13)
            local hand_to = smooth((u - 0.12) / 0.18) * (1 - smooth((u - 0.68) / 0.17))
            local drop = V(-0.03, -0.22, 0.06) * out
            r.cell.position = r.cell_home + drop * (1 - seat) + V(0, -0.012, 0) * bump(u, 0.56, 0.62)
            setvis(r.cell, not (u > 0.43 and u < 0.47))
            local grip = r.cell_home + V(-0.025, -0.07, 0.0)
            r.hand_l.position = r.hand_home + (grip + drop * (1 - seat) - r.hand_home) * hand_to
            r.hand_l.rotation = r.hand_rot + V(0, 0, -25 * hand_to)
        end
        if self.reload_empty and r.slide then
            r.slide.position = r.slide_home + V(0, 0, 0.022 * bump(u, 0.74, 0.86))
        end
    end
    -- Sidearm slide kick on each shot.
    if self.slide_t and r.slide then
        self.slide_t -= dt
        local kk = math.max(0, self.slide_t) / 0.09
        r.slide.position = r.slide_home + V(0, 0, 0.018 * math.sin(kk * math.pi))
        if self.slide_t <= 0 then self.slide_t = nil end
    end
    -- Scanner: raise in the left of the frame, weapon nudges right.
    if self.device then
        local sa = 0
        if self.scan_anim > 0 then sa = smooth(self.scan_anim / 0.25) * (1 - smooth((self.scan_anim - 1.0) / 0.3)) end
        setvis(self.device, sa > 0.01)
        if sa > 0.01 then
            self.device.position = self.device_home + V(0, -0.2 * (1 - sa), 0.05 * (1 - sa))
            self.device.rotation = V(10 - 25 * (1 - sa), 180 + 20, 0)
        end
        pos += V(0.03 * sa, -0.02 * sa, 0)
        rot += V(-5 * sa, -6 * sa, 0)
    end
    self.pivot.position = pos
    self.pivot.rotation = rot

    -- HUD.
    local st = ""
    if self.state == "reload" then st = "RELOADING"
    elseif self.state == "equip" or self.state == "lower" then st = ""
    elseif r.ammo == 0 then st = r.reserve > 0 and "RELOAD" or "NO CELLS"
    elseif r.ammo <= math.floor(d.mag * 0.25) then st = "LOW" end
    local hud = Game.weapon_hud or {}
    hud.name = d.label
    hud.ammo = r.ammo
    hud.reserve = r.reserve
    hud.state = st
    hud.spread = self:spread_now(ps) / 1.6
    Game.weapon_hud = hud
    self:tool_hud()
end

function W:tool_hud()
    local left = self.scan_cooldown - self.scan_t
    if self.scan_anim > 0 then
        Game.tool_hud = string.format("SCAN  %d contact%s", self.last_scan, self.last_scan == 1 and "" or "s")
    elseif left > 0 then
        Game.tool_hud = string.format("SCANNER  %.0fs", math.ceil(left))
    else
        Game.tool_hud = "SCANNER READY"
    end
end

return W
