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
-- Handling follows body-cam reference (Bodycam's calm and stressed reloads): a stress value rises
-- when the player is hit, shot at or nearly missed and decays when things go quiet. Every reload
-- draws its own small variations (roll, dip, hand placement, timing); stressed reloads are quicker
-- and shakier and can fumble the cell at the well and retry. Partial-cell (tactical) reloads stow
-- the old cell towards the vest, empty ones let it fall away. RELOAD with a full cell does a cell
-- check, and a long burst ends with the support hand re-taking its grip.
-- Writes Game.weapon_hud { name, ammo, reserve, state, spread }, Game.tool_hud, and the
-- player's zoom / zoom_fov (read by fp_player.luau for FOV, speed and look sensitivity).
local Game = require("scripts/lib/game")
local Footsteps = require("scripts/lib/footsteps")
local Controls = require("scripts/lib/controls")
local Combat = require("scripts/lib/combat")
local Squad = require("scripts/lib/squad")
local Items = require("scripts/lib/items")
local Inventory = require("scripts/lib/inventory")

local V = vector.create

-- Weapon definitions live in lib/items.luau (shared with inventory, storage, HUD and saves).
local DEFS = {}
for id, d in Items.defs do if d.kind == "weapon" then DEFS[id] = d end end

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
            local r = { def = d, root = root, st = Items.new_state(id),
                        cell = find(root, d.root .. " Cell"), slide = find(root, d.root .. " Slide"),
                        hand_l = find(root, d.root .. " Hand L"), muzzle = find(root, d.root .. " Muzzle"),
                        flash = find(root, d.root .. " Flash") }
            r.cell_home = r.cell and r.cell.position or V(0, 0, 0)
            r.hand_home = r.hand_l and r.hand_l.position or V(0, 0, 0)
            r.hand_rot = r.hand_l and r.hand_l.rotation or V(0, 0, 0)
            r.slide_home = r.slide and r.slide.position or V(0, 0, 0)
            r.cell_rot = r.cell and r.cell.rotation or V(0, 0, 0)
            setvis(root, false)
            self.w[id] = r
        end
    end
    self.kit_model = find(self.entity, "Kit")
    if self.kit_model then self.kit_home = self.kit_model.position; setvis(self.kit_model, false) end
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
    -- Loadout: the player's inventory (lib/inventory.luau) decides what is carried.
    if not Game.inventory then Inventory.reset() end
    self.current = nil
    self.pending = nil
    self:sync_inventory()
    for _, slot in Items.weapon_slots do
        local id = Inventory.in_slot(slot)
        if id and self.w[id] then self.pending = id; break end
    end
    Game.on("inventory_changed", function(id, what) self:on_inventory(id, what) end)
    self.scope_level = 1
    self.kit_t = nil
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
    self.stress = 0         -- 0 calm .. 1 under fire (decays after stress_hold seconds of quiet)
    self.stress_t = 99
    self.burst = 0          -- shots in the current trigger hold
    self.regrip_t = nil
    self.reloads = 0
    self.fumbles = 0
    self.checks = 0
    self.rest = V(0, 0, 0); self.rest_target = V(0, 0, 0)
    self.rest_rot = V(0, 0, 0); self.rest_rot_target = V(0, 0, 0)
    Game.on("player_hurt", function() self:add_stress(0.35) end)
    Game.on("near_miss", function() self:add_stress(0.22) end)
    Game.on("player_shot_at", function() self:add_stress(0.15) end)
    if self.pending then self:begin_equip(self.pending) end
end

-- Public API ---------------------------------------------------------------------------------

function W:visible(id) local r = self.w[id]; return r ~= nil and isvis(r.root) end

function W:weapon() return self.current and self.w[self.current] end

-- Points each weapon's runtime record at its inventory state (the same table, so ammo spent
-- here is what storage and checkpoints see).
function W:sync_inventory()
    for id, r in self.w do
        local st = Inventory.state(id)
        if st then r.st = st end
    end
end

-- Reacts to items entering or leaving the inventory. A newly taken weapon is raised (the one in
-- hand is lowered first, visibly, even when it is the item being handed over); a dropped current
-- weapon is lowered and the next carried weapon raised; nothing left means holstered.
function W:on_inventory(id, what)
    self:sync_inventory()
    if what == "restored" then return end
    if id and what == "taken" and self.w[id] and Inventory.has(id) and id ~= self.current then
        if self.current then self:begin_switch(id) else self:begin_equip(id) end
        return
    end
    if self.current and not Inventory.has(self.current) then
        local nxt = nil
        for _, slot in Items.weapon_slots do
            local w = Inventory.in_slot(slot)
            if not nxt and w and self.w[w] then nxt = w end
        end
        if nxt then
            self:begin_switch(nxt)
        elseif self.state ~= "lower" then
            self.pending = nil
            self:begin_lower()
        end
    end
end

-- Gives (or tops up) a weapon through the inventory.
function W:give(id, ammo)
    local r = self.w[id]
    if not r then return false end
    if not Inventory.has(id) then
        local ok, displaced, dstate = Inventory.take(id)
        if not ok then return false end
        self.last_displaced = displaced and { id = displaced, state = dstate } or nil
    end
    local st = Inventory.state(id)
    if ammo and st then st.reserve = math.min(r.def.max_reserve, st.reserve + ammo) end
    return true
end

function W:refill()
    for id, r in self.w do
        local st = Inventory.state(id)
        if st then st.reserve = r.def.max_reserve; st.ammo = r.def.mag end
    end
end

function W:save_state()
    local inv = Inventory.serialize()
    local s = { current = self.current, inventory = inv, ammo = {} }
    for id, st in inv.state do if st.ammo then s.ammo[id] = { st.ammo, st.reserve } end end
    return s
end

function W:load_state(s)
    if type(s) ~= "table" then return end
    if s.inventory then Inventory.restore(s.inventory) end
    self:sync_inventory()
    if s.current and self.w[s.current] and Inventory.has(s.current) and s.current ~= self.current then
        if self.current and self.w[self.current] then setvis(self.w[self.current].root, false) end
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

-- Lowering starts from wherever the weapon is (an interrupted raise or reload does not snap).
function W:begin_lower()
    if self.state == "kit" then self:end_kit(false) end
    self.lower_from = self.lower_amt
    self.state = "lower"
    self.st = 0
end

function W:begin_switch(id)
    if id == self.current or not self.w[id] or not Inventory.has(id) then return false end
    self.pending = id
    if self.state ~= "lower" then self:begin_lower() end
    return true
end

W.stress_hold = 2.5         -- seconds of quiet before stress starts to fall
W.stress_decay = 0.1        -- per second after that (full stress settles in about 12 s)
W.fumble_from = 0.55        -- stress above which a reload can miss the well
W.fumble_time = 0.5         -- seconds a fumble adds

function W:add_stress(x)
    self.stress = math.min(1, self.stress + x)
    self.stress_t = 0
end

local function jitter(a) return (math.random() * 2 - 1) * a end

-- A new resting hold after a reload or re-grip: the weapon never returns to the exact same spot.
function W:new_rest()
    self.rest_target = V(jitter(0.0035), jitter(0.0025), jitter(0.003))
    self.rest_rot_target = V(jitter(1.2), jitter(1.0), jitter(1.6))
end

function W:begin_reload()
    local r = self:weapon()
    if not r or self.state ~= "idle" then return false end
    if r.st.ammo >= r.def.mag then return self:begin_check() end
    if r.st.reserve <= 0 then return false end
    local d, s = r.def, self.stress
    self.state = "reload"
    self.st = 0
    self.reload_empty = r.st.ammo == 0
    -- Stress hurries the hands (up to 12 % quicker); every reload varies its timing a little.
    local base = (self.reload_empty and d.reload_empty or d.reload) * (1 - 0.12 * s) * (0.97 + math.random() * 0.06)
    self.reload_base = base
    self.fumble = s > self.fumble_from and math.random() < 0.25 + (s - self.fumble_from) * 1.6
    self.reload_len = base + (self.fumble and self.fumble_time or 0)
    self.rv = { roll = 24 + jitter(7) + 8 * s, dip = 0.85 + math.random() * 0.3, yaw = jitter(3),
                hand = V(jitter(0.008), jitter(0.006), jitter(0.006)), shake = s, seed = math.random() * 100 }
    self.reload_sfx = 0
    self.fumble_sfx = false
    self.reloads += 1
    if self.fumble then self.fumbles += 1 end
    Game.emit("reload_started", d.id, self.reload_empty)
    return true
end

-- Reload phase 0..1 on the calm timeline. A fumble holds the phase at the well for fumble_time
-- and returns the extra 0..1 fumble progress.
function W:reload_phase()
    local t, base = self.st, self.reload_base or self.reload_len
    if self.fumble then
        local f0 = 0.555 * base
        if t >= f0 then
            if t < f0 + self.fumble_time then return 0.555, (t - f0) / self.fumble_time end
            t -= self.fumble_time
        end
    end
    return Game.clamp(t / base, 0, 1), nil
end

-- Cell check: tilt the weapon in, thumb the cell out a little, read the charge window, seat it.
W.check_time = 1.25
function W:begin_check()
    local r = self:weapon()
    if not r or self.state ~= "idle" or not r.cell then return false end
    self.state = "check"
    self.st = 0
    self.check_said = false
    self.checks += 1
    return true
end

local function cell_words(ammo, mag)
    local f = ammo / math.max(1, mag)
    if f >= 0.99 then return "full" elseif f >= 0.7 then return "nearly full"
    elseif f >= 0.4 then return "about half" elseif f > 0.15 then return "low" end
    return "almost dry"
end
W.cell_words = cell_words

function W:reset_parts(r)
    if r.cell then r.cell.position = r.cell_home; r.cell.rotation = r.cell_rot; setvis(r.cell, true) end
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
    if r.st.ammo <= 0 then
        play("audio/weapons/dry.wav", 0.8)
        self.cooldown = 0.25
        if r.st.reserve <= 0 then Game.emit("dry_fire", d.id) end
        if r.st.reserve > 0 then self:begin_reload() end
        return
    end
    r.st.ammo -= 1
    self.cooldown = d.interval
    self.shots += 1
    self.burst += 1
    if self.stress < 0.3 then self.stress = math.min(0.3, self.stress + 0.012) end
    Combat.stats.shots += 1
    local origin, dir = ps:aim_ray()
    -- Random cone spread (degrees). Spread emitters (d.pellets) cast several sub-pulses inside an
    -- extra pellet cone; hit feedback fires once per trigger pull, using the best zone hit.
    local spread = math.rad(self:spread_now(ps))
    local right = ps.cam.right
    local up = ps.cam.up
    local a = math.random() * math.pi * 2
    local rr = math.sqrt(math.random()) * math.tan(spread)
    local cdir = vector.normalize(dir + right * (math.cos(a) * rr) + up * (math.sin(a) * rr))
    local pellets = d.pellets or 1
    local pcone = math.tan(math.rad(d.pellet_spread or 0))
    local confirmed = nil
    for i = 1, pellets do
        local sdir = cdir
        if pellets > 1 then
            -- even ring pattern with jitter so fans read as a fan, not a random blob
            local pa = (i / pellets) * math.pi * 2 + (math.random() - 0.5) * 0.9
            local pr = (i == 1) and 0 or pcone * (0.45 + math.random() * 0.55)
            sdir = vector.normalize(cdir + right * (math.cos(pa) * pr) + up * (math.sin(pa) * pr))
        end
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
                if ok and confirmed ~= "head" then confirmed = zone end
                self:impact(hit, true, i > 2)
            else
                self:impact(hit, false, i > 2)
            end
        end
        if i <= 3 then self:tracer(r, endp) end
    end
    if confirmed then
        self.hits += 1
        Combat.stats.hits += 1
        Game.emit("hit_confirm", confirmed)
        audio.play("audio/ui/hit_tick.wav", { volume = confirmed == "head" and 0.75 or 0.5, bus = "ui",
                                             pitch = confirmed == "head" and 1.25 or 1, max_instances = 3 })
    end
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
    if r.slide then self.slide_t = (d.slide_delay or 0) + (d.slide_time or 0.09); self.slide_sfx = d.pump_sfx end
    ps:add_shake(0.06 * ads)
    play(d.fire, 0.95, 0.95 + math.random() * 0.1)
    Combat.noise(Game.player.world_position, d.noise, Game.player)
    Squad.state().player_shot_t = time.now()   -- the lead opened fire: weapons free for the squad
    Game.emit("player_fired", d.id)
    if r.st.ammo == 0 and r.st.reserve > 0 then self.auto_reload = 0.35 end
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

function W:impact(hit, on_target, quiet)
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
    local surf = (not on_target) and Footsteps.impact_surface(hit) or nil
    self.last_surface = surf
    -- debris by surface: a spray of soil, chips off stone, a few splinters, nothing off metal
    local dust = surf == "dirt" and 7 or surf == "stone" and 5 or surf == "wood" and 3 or 0
    if self.dust and not on_target and dust > 0 then
        self.dust.position = p
        self.dust.rotation = rot
        self.dust:emit_particles(dust)
    end
    if quiet then return end
    play(W.impact_clip(on_target, surf), surf == "metal" and 0.6 or 0.7, 0.9 + math.random() * 0.2, hit.point)
end

-- the impact sound for a hit: bodies thump, the world answers with its surface (two takes each)
W.impact_n = 0
function W.impact_clip(on_target, surf)
    if on_target then return "audio/weapons/impact_hard.wav" end
    if not surf then return "audio/weapons/impact_soft.wav" end
    W.impact_n += 1
    return "audio/weapons/impact_" .. surf .. "_" .. (W.impact_n % 2) .. ".wav"
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

-- Scope zoom steps ------------------------------------------------------------------------------

function W:cycle_scope()
    local d = self:weapon() and self:weapon().def
    if not d or not d.scope then return end
    self.scope_level = self.scope_level % #d.scope + 1
    play(d.zoom_sfx or "audio/weapons/aim.wav", 0.5, self.scope_level == 1 and 0.92 or 1.08)
    Game.emit("scope_zoom", self.scope_level)
end

-- Field kit (utility slot) -------------------------------------------------------------------------
-- Lowers the weapon, brings the kit up in the left of the frame, applies the patch two thirds of
-- the way through and raises the weapon again. Interrupting (switch, take) cancels without
-- spending the charge.

function W:use_kit(ps)
    local id = Inventory.in_slot("utility")
    local kd = Items.get(id)
    if not kd or not kd.heal then return false end
    if self.state ~= "idle" or ps.sprinting then return false end
    if ps.health >= ps.max_health - 0.5 then
        if Game.toast then Game.toast("Health is full", 1.4) end
        return false
    end
    self.kit = { id = id, def = kd, applied = false }
    self.lower_from = self.lower_amt
    self.state = "kit"
    self.st = 0
    play(kd.use_sfx or "audio/foley/item_pick.wav", 0.75)
    Game.emit("kit_started", id)
    return true
end

function W:update_kit(dt, ps, d)
    local k = self.kit
    if not k then self.state = "idle"; return end
    local len = k.def.use_time or 1.6
    local u = self.st / len
    self.lower_amt = smooth(u / 0.2) * (1 - smooth((u - 0.8) / 0.2))
    if not k.applied and u >= 0.62 then
        k.applied = true
        ps.health = math.min(ps.max_health, ps.health + k.def.heal)
        Inventory.spend(k.id)
        Game.emit("kit_used", k.id)
    end
    if u >= 1 then self:end_kit(true) end
end

function W:end_kit(done)
    self.kit = nil
    if self.state == "kit" then self.state = "idle"; self.lower_amt = done and 0 or self.lower_amt end
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
            local order = {}
            for _, slot in Items.weapon_slots do
                local id = Inventory.in_slot(slot)
                if id and self.w[id] then table.insert(order, id) end
            end
            local idx = 0
            for i, id in order do if id == self.current then idx = i end end
            local nxt = order[idx % math.max(1, #order) + 1]
            if nxt and nxt ~= self.current then self:begin_switch(nxt) end
        end
        if Controls.pressed("weapon1") and Inventory.in_slot("primary") then self:begin_switch(Inventory.in_slot("primary")) end
        if Controls.pressed("weapon2") and Inventory.in_slot("secondary") then self:begin_switch(Inventory.in_slot("secondary")) end
        -- Tap RELOAD to reload; hold it to check the cell instead (the reload turns into a check
        -- before the hand reaches the cell). With a full cell a tap checks too.
        if Controls.pressed("reload") then self:begin_reload(); self.reload_hold = 0 end
        if self.reload_hold then
            if Controls.down("reload") then
                self.reload_hold += dt
                if self.reload_hold >= 0.28 then
                    self.reload_hold = nil
                    if self.state == "reload" and self.st < 0.12 * (self.reload_base or 1) + 0.28 then
                        self.state = "idle"
                        self.reloads -= 1
                        if self.fumble then self.fumbles -= 1 end
                        self:begin_check()
                        self:reset_parts(r)
                        self.xfade = { t = 0, pos = self.pivot.position, rot = self.pivot.rotation }
                    end
                end
            else
                self.reload_hold = nil
            end
        end
        if Controls.pressed("tool") then
            if self.scoped then self:cycle_scope() else self:scan() end
        end
        if Controls.pressed("utility") then self:use_kit(ps) end
        if touch then
            if Controls.pressed("aim") then self.aim_toggle = not self.aim_toggle end
        else
            self.aim_toggle = false
        end
    end
    local aiming = playing and (self.aim_toggle or (not touch and Controls.down("aim")))
    if self.state ~= "idle" or ps.sprinting then aiming = false end
    if ps.sprinting then self.aim_toggle = false end

    -- State progression.
    if self.state == "equip" then
        self.lower_amt = 1 - smooth(self.st / d.equip)
        if self.st >= d.equip then self.state = "idle"; self.lower_amt = 0 end
    elseif self.state == "lower" then
        local from = self.lower_from or 0
        local len = math.max(0.05, d.lower * (1 - from))
        self.lower_amt = from + (1 - from) * smooth(self.st / len)
        if self.st >= len then
            if self.pending and Inventory.has(self.pending) then
                self:begin_equip(self.pending)
            else
                -- nothing to raise: holster
                self.pending = nil
                setvis(r.root, false)
                self.current = nil
                self.state = "idle"
                self.zoom = 0
                ps.zoom = 0
                return
            end
        end
    elseif self.state == "kit" then
        self:update_kit(dt, ps, d)
    elseif self.state == "check" then
        local u = self.st / self.check_time
        if not self.check_said and u > 0.45 then
            self.check_said = true
            play(d.cell_out, 0.35, 1.15)
            local text = "Cell " .. cell_words(r.st.ammo, d.mag)
            if Game.toast then Game.toast(text, 1.4) end
            self.check_text = text
        end
        if u >= 1 then
            play(d.cell_in, 0.4, 1.1)
            self.state = "idle"
            self:reset_parts(r)
            self:new_rest()
        end
    elseif self.state == "reload" then
        local u, fu = self:reload_phase()
        if fu and not self.fumble_sfx then
            self.fumble_sfx = true
            play(d.cell_in, 0.5, 1.3)      -- the cell's edge knocks the well
        end
        if self.reload_sfx == 0 and u > 0.18 then play(d.cell_out, 0.8); self.reload_sfx = 1 end
        if self.reload_sfx == 1 and u > 0.58 then play(d.cell_in, 0.85); self.reload_sfx = 2 end
        if self.reload_sfx == 2 and u > 0.7 then play(d.charge, 0.6); self.reload_sfx = 3 end
        if u >= 1 then
            local need = d.mag - r.st.ammo
            local take = math.min(need, r.st.reserve)
            r.st.ammo += take
            r.st.reserve -= take
            self.state = "idle"
            self:reset_parts(r)
            self:new_rest()
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
    if not trig and self.trigger_held and self.burst >= 8 and self.state == "idle" then self.regrip_t = 0 end
    if not trig then self.burst = 0 end
    self.trigger_held = trig
    self.stress_t += dt
    if self.stress_t > self.stress_hold then self.stress = math.max(0, self.stress - self.stress_decay * dt) end
    Game.stress = self.stress

    -- Aim blend.
    self.zoom = Game.damp(self.zoom, aiming and 1 or 0, aiming and 14 or 11, dt)
    if self.zoom < 0.002 then self.zoom = 0 end
    ps.zoom = self.zoom
    ps.zoom_fov = Game.settings.fov * d.zoom_fov
    ps.zoom_sens = 1
    -- Scope: past scope_at the view goes through the lens; the viewmodel is hidden behind it.
    local scoped = d.scope ~= nil and self.zoom > (d.scope_at or 0.8) and aiming
    if scoped ~= (self.scoped == true) then
        self.scoped = scoped
        setvis(r.root, not scoped)
        if scoped then play(d.zoom_sfx or "audio/weapons/aim.wav", 0.45, 1.0) end
        self.sway_prev = nil
    end
    if scoped then
        local mult = d.scope[self.scope_level] or d.scope[1]
        ps.zoom_fov = Game.settings.fov * mult
        ps.zoom_sens = mult / d.zoom_fov
        -- breathing sway, steadier crouched; applied as a delta so it never accumulates
        local amp = (d.scope_sway or 0.2) * (ps.crouched and 0.45 or 1) * (self.scope_level == 2 and 1.25 or 1)
        local tn2 = time.now()
        local sx = (math.sin(tn2 * 0.83) * 0.6 + math.sin(tn2 * 1.91 + 0.7) * 0.3) * amp
        local sy = (math.sin(tn2 * 1.27 + 1.3) * 0.5 + math.sin(tn2 * 0.53) * 0.3) * amp
        if self.sway_prev then
            ps.yaw += sx - self.sway_prev.x
            ps.pitch += sy - self.sway_prev.y
        end
        self.sway_prev = V(sx, sy, 0)
    end
    Game.scope = scoped and { level = self.scope_level, levels = #d.scope } or nil
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
    self.sprint = Game.damp(self.sprint, (ps.sprinting and self.state ~= "reload" and self.state ~= "check") and 1 or 0, 9, dt)
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
    -- Resting hold drifts to the last re-grip's offset.
    self.rest = Game.damp(self.rest, self.rest_target, 3, dt)
    self.rest_rot = Game.damp(self.rest_rot, self.rest_rot_target, 3, dt)
    pos += self.rest * (1 - zoom)
    rot += self.rest_rot * (1 - zoom)
    -- Re-grip after a long burst: the support hand lets go, slides and clamps again.
    if self.regrip_t and r.hand_l then
        self.regrip_t += dt
        local g = bump(self.regrip_t / 0.55, 0.0, 1.0)
        r.hand_l.position = r.hand_home + V(0.004, -0.012, 0.018) * g
        r.hand_l.rotation = r.hand_rot + V(0, 0, -9 * g)
        pos += V(0.002, -0.004, 0) * g
        rot += V(-1.5, 0, 2.5) * g
        if self.regrip_t >= 0.55 then
            self.regrip_t = nil
            r.hand_l.position = r.hand_home; r.hand_l.rotation = r.hand_rot
            self:new_rest()
        end
    end
    -- Stress tremor: a small irregular shake that grows with stress (hip only, faded in ADS).
    if self.stress > 0.05 then
        local tr = self.stress * self.stress * (1 - zoom * 0.75)
        pos += V(math.sin(tn * 13.1) + math.sin(tn * 21.7) * 0.6, math.sin(tn * 17.3 + 1.1) * 0.8, 0) * 0.0009 * tr
        rot += V(math.sin(tn * 11.3 + 2) * 0.35, math.sin(tn * 9.7) * 0.3, math.sin(tn * 15.1) * 0.4) * tr
    end
    -- Cell check: roll the weapon in and up, thumb the cell 2 cm out, read it, push it home.
    if self.state == "check" and r.cell then
        local u = Game.clamp(self.st / self.check_time, 0, 1)
        local tilt = smooth(u / 0.25) * (1 - smooth((u - 0.78) / 0.22))
        pos += V(-0.035 * tilt, 0.012 * tilt, 0.025 * tilt)
        rot += V(10 * tilt, 14 * tilt, 38 * tilt)
        local pull = smooth((u - 0.22) / 0.16) * (1 - smooth((u - 0.66) / 0.14))
        r.cell.position = r.cell_home + V(-0.004, -0.022, 0.002) * pull
        if r.hand_l then
            local h = smooth((u - 0.1) / 0.15) * (1 - smooth((u - 0.74) / 0.18))
            r.hand_l.position = r.hand_home + (r.cell_home + V(-0.025, -0.07, 0) - r.hand_home) * h + V(0, -0.022, 0) * pull
            r.hand_l.rotation = r.hand_rot + V(0, 0, -25 * h)
        end
    end
    -- Reload choreography: dip and roll the weapon, the support hand pulls and seats the cell.
    if self.state == "reload" then
        local u, fu = self:reload_phase()
        local rv = self.rv or { roll = 24, dip = 1, yaw = 0, hand = V(0, 0, 0), shake = 0, seed = 0 }
        local dip = smooth(u / 0.18) * (1 - smooth((u - 0.82) / 0.18)) * rv.dip
        pos += V(-0.02 * dip, -0.04 * dip, 0.02 * dip)
        rot += V(8 * dip, (6 + rv.yaw) * dip, rv.roll * dip)
        if rv.shake > 0.05 then
            local k = rv.shake * dip
            rot += V(math.sin(tn * 19 + rv.seed) * 0.8, 0, math.sin(tn * 23 + rv.seed) * 1.1) * k
        end
        if r.cell and r.hand_l then
            -- 0.15..0.30 hand to cell, 0.30..0.45 cell out and away, 0.45..0.58 new cell up,
            -- 0.58..0.68 seat, 0.68..0.85 hand back (charge whine), empty reloads add a tap.
            -- Partial cells are stowed (down and back to the vest); empty ones drop and tumble.
            local out = smooth((u - 0.30) / 0.15) * (1 - smooth((u - 0.45) / 0.13))
            local seat = smooth((u - 0.45) / 0.13)
            local hand_to = smooth((u - 0.12) / 0.18) * (1 - smooth((u - 0.68) / 0.17))
            local away = self.reload_empty and V(-0.02, -0.30, 0.05) or V(-0.09, -0.24, 0.11)
            local drop = away * out
            local miss = V(0, 0, 0)
            if fu then
                -- Fumble: the cell's nose catches the well's lip, the hand pulls it back and re-aims.
                local f = math.sin(fu * math.pi)
                miss = V(0.007 * f, -0.028 * f, 0.004 * f) + V(math.sin(fu * 31) * 0.0015, 0, 0) * f
                rot += V(1.5 * f, 0, -3 * f)
            end
            r.cell.position = r.cell_home + drop * (1 - seat) + V(0, -0.012, 0) * bump(u, 0.56, 0.62) + miss
            if self.reload_empty then
                r.cell.rotation = r.cell_rot + V(55 * out, 0, 30 * out) * (1 - seat)
            else
                r.cell.rotation = r.cell_rot + V(-20 * out, 15 * out, 0) * (1 - seat)
            end
            setvis(r.cell, not (u > 0.43 and u < 0.47))
            local grip = r.cell_home + V(-0.025, -0.07, 0.0) + rv.hand
            r.hand_l.position = r.hand_home + (grip + drop * (1 - seat) + miss - r.hand_home) * hand_to
            r.hand_l.rotation = r.hand_rot + V(0, 0, -25 * hand_to)
        end
        if self.reload_empty and r.slide then
            r.slide.position = r.slide_home + V(0, 0, 0.022 * bump(u, 0.74, 0.86))
        end
    end
    -- Slide kick (sidearm) or pump stroke (breacher) after each shot.
    if self.slide_t and r.slide then
        self.slide_t -= dt
        local d = r.def
        local delay, dur = d.slide_delay or 0, d.slide_time or 0.09
        local u = delay + dur - math.max(0, self.slide_t)
        local kk = Game.clamp((u - delay) / dur, 0, 1)
        if u >= delay and self.slide_sfx then play(self.slide_sfx, 0.85); self.slide_sfx = nil end
        r.slide.position = r.slide_home + V(0, 0, (d.slide_travel or 0.018) * math.sin(kk * math.pi))
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
    if self.kit_model then
        local ka = 0
        if self.state == "kit" then
            local u = self.st / ((self.kit and self.kit.def.use_time) or 1.6)
            ka = smooth((u - 0.1) / 0.25) * (1 - smooth((u - 0.78) / 0.18))
        end
        setvis(self.kit_model, ka > 0.01)
        if ka > 0.01 then
            self.kit_model.position = self.kit_home + V(0.02 * (1 - ka), -0.22 * (1 - ka), 0.04 * (1 - ka))
            self.kit_model.rotation = V(28 - 20 * (1 - ka), 18, -6)
        end
    end
    if self.xfade then
        -- Blend out of an interrupted pose (reload turned into a cell check) instead of snapping.
        self.xfade.t += dt
        local k = smooth(self.xfade.t / 0.22)
        pos = self.xfade.pos + (pos - self.xfade.pos) * k
        rot = self.xfade.rot + (rot - self.xfade.rot) * k
        if k >= 1 then self.xfade = nil end
    end
    self.pivot.position = pos
    self.pivot.rotation = rot

    -- HUD.
    local st = ""
    if self.state == "reload" then st = "RELOADING"
    elseif self.state == "check" then st = "CHECKING"
    elseif self.state == "equip" or self.state == "lower" then st = ""
    elseif r.st.ammo == 0 then st = r.st.reserve > 0 and "RELOAD" or "NO CELLS"
    elseif r.st.ammo <= math.floor(d.mag * 0.25) then st = "LOW" end
    local hud = Game.weapon_hud or {}
    hud.name = d.label
    hud.ammo = r.st.ammo
    hud.reserve = r.st.reserve
    hud.state = st
    hud.mag = d.mag
    hud.reload = self.state == "reload" and Game.clamp(self.st / math.max(0.01, self.reload_len or 1), 0, 1) or nil
    hud.spread = self:spread_now(ps) / 1.6
    Game.weapon_hud = hud
    self:tool_hud()
end

function W:tool_hud()
    local kid = Inventory.in_slot("utility")
    local kst = kid and Inventory.state(kid)
    Game.kit_hud = kst and kst.charges and string.format("KIT x%d", kst.charges) or nil
    if self.scoped then
        Game.tool_hud = "ZOOM STEP [T]"
        return
    end
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
