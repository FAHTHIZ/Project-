-- SPECIAL OPS item definitions: the single source of truth for every carriable thing.
-- The same definition drives the first-person viewmodel (weapons.luau), the HUD, inventory
-- slots and carry limits (lib/inventory.luau), world/storage pickups (lib/storage.luau),
-- audio, checkpoint saves and what squad operators visibly carry.
--
-- All weapons are fictional stun-pulse emitters with invented, abstract game values. They do not
-- model a real firearm's mechanism, ballistics or performance.
--
-- Fields
--   id, label, desc        identity and the text shown in prompts / storage descriptions
--   kind                   "weapon" | "tool" | "utility" | "supply"
--   slot                   inventory slot it occupies; nil for supplies (consumed on pickup)
--   world                  model shown when the item sits in storage or on the ground
--   weapon fields          viewmodel root, magazine, timing and feel (read by weapons.luau)
local V = vector.create

local Items = {}

Items.defs = {
    carbine = {
        id = "carbine", label = "PC-7 LANTERN", kind = "weapon", slot = "primary",
        desc = "Pulse carbine. Steady, forgiving, good at any range you can see.",
        world = "models/weapons/pc7_world.glb", root = "Carbine",
        mag = 30, reserve = 150, max_reserve = 240, interval = 0.095, auto = true,
        stun = 22, head_mult = 1.8, range = 140,
        spread_hip = 1.6, spread_ads = 0.18, spread_move = 1.6, bloom = 0.35, bloom_max = 2.4,
        kick_pitch = 0.62, kick_yaw = 0.28, ads_kick = 0.55, kick_back = 0.028, kick_rot = 3.2,
        reload = 1.75, reload_empty = 2.25, equip = 0.38, lower = 0.2,
        hip = V(0.155, -0.18, -0.40), ads = V(0, -0.1131, -0.30), hip_rot = V(1.5, 3.5, 0), zoom_fov = 0.72,
        muzzle = V(0, 0.045, -0.56), cell = V(0, 0, 0),
        fire = "audio/weapons/pc7_fire.wav", cell_out = "audio/weapons/pc7_cell_out.wav",
        cell_in = "audio/weapons/pc7_cell_in.wav", charge = "audio/weapons/pc7_charge.wav", noise = 38,
    },
    marksman = {
        id = "marksman", label = "LR-4 HERON", kind = "weapon", slot = "primary",
        desc = "Long pulse emitter with a two-step scope. Slow, quiet, one careful shot at a time.",
        world = "models/weapons/lr4_world.glb", root = "Marksman",
        mag = 5, reserve = 20, max_reserve = 30, interval = 0.85, auto = false,
        stun = 64, head_mult = 1.5, range = 240,
        spread_hip = 4.0, spread_ads = 0.03, spread_move = 2.6, bloom = 0.0, bloom_max = 0.0,
        kick_pitch = 1.6, kick_yaw = 0.25, ads_kick = 0.7, kick_back = 0.05, kick_rot = 5.0,
        reload = 2.3, reload_empty = 2.7, equip = 0.62, lower = 0.3,
        hip = V(0.16, -0.17, -0.42), ads = V(0, -0.1175, -0.27), hip_rot = V(2.0, 4.0, 0), zoom_fov = 0.62,
        -- Scope: once the aim blend passes `scope_at` the view switches to the scope overlay and
        -- the field of view steps through these multipliers (toggled with the tool action).
        scope = { 0.30, 0.16 }, scope_at = 0.82, scope_sway = 0.22,
        muzzle = V(0, 0.05, -0.74), cell = V(0, 0, 0),
        fire = "audio/weapons/lr4_fire.wav", cell_out = "audio/weapons/lr4_cell_out.wav",
        cell_in = "audio/weapons/lr4_cell_in.wav", charge = "audio/weapons/lr4_charge.wav", noise = 24,
        zoom_sfx = "audio/weapons/lr4_zoom.wav",
    },
    pdw = {
        id = "pdw", label = "KV-5 HORNET", kind = "weapon", slot = "primary",
        desc = "Compact pulse PDW with a red-dot sight. Fast, short, made for corridors.",
        world = "models/weapons/kv5_world.glb", root = "PDW",
        mag = 40, reserve = 160, max_reserve = 240, interval = 0.07, auto = true,
        stun = 15, head_mult = 1.7, range = 70,
        spread_hip = 1.3, spread_ads = 0.35, spread_move = 1.0, bloom = 0.22, bloom_max = 2.0,
        kick_pitch = 0.42, kick_yaw = 0.34, ads_kick = 0.6, kick_back = 0.02, kick_rot = 2.6,
        reload = 1.5, reload_empty = 1.95, equip = 0.3, lower = 0.16,
        hip = V(0.14, -0.155, -0.36), ads = V(0, -0.103, -0.27), hip_rot = V(1.5, 3.5, 0), zoom_fov = 0.8,
        muzzle = V(0, 0.05, -0.39), cell = V(0, 0, 0),
        fire = "audio/weapons/kv5_fire.wav", cell_out = "audio/weapons/pc7_cell_out.wav",
        cell_in = "audio/weapons/pc7_cell_in.wav", charge = "audio/weapons/pc7_charge.wav", noise = 30,
    },
    breacher = {
        id = "breacher", label = "BR-9 RAM", kind = "weapon", slot = "primary",
        desc = "Pump-action breaching emitter. Throws a wide pulse fan; brutal up close, useless far out.",
        world = "models/weapons/br9_world.glb", root = "Breacher",
        mag = 6, reserve = 24, max_reserve = 36, interval = 0.78, auto = false,
        -- `pellets` sub-pulses per trigger pull, each with its own stun and a cone of `pellet_spread` deg
        pellets = 8, pellet_spread = 3.4, stun = 11, head_mult = 1.3, range = 26,
        spread_hip = 0.6, spread_ads = 0.2, spread_move = 0.6, bloom = 0.0, bloom_max = 0.0,
        kick_pitch = 2.4, kick_yaw = 0.5, ads_kick = 0.75, kick_back = 0.06, kick_rot = 6.5,
        reload = 2.4, reload_empty = 2.9, equip = 0.5, lower = 0.26,
        hip = V(0.15, -0.17, -0.40), ads = V(0, -0.0945, -0.25), hip_rot = V(1.8, 3.5, 0), zoom_fov = 0.85,
        muzzle = V(0, 0.058, -0.565), cell = V(0, 0, 0),
        -- pump: the "Slide" part racks back `slide_travel` m, `slide_delay` s after the shot
        slide_travel = 0.07, slide_time = 0.42, slide_delay = 0.16,
        fire = "audio/weapons/br9_fire.wav", cell_out = "audio/weapons/lr4_cell_out.wav",
        cell_in = "audio/weapons/lr4_cell_in.wav", charge = "audio/weapons/br9_pump.wav", noise = 44,
        pump_sfx = "audio/weapons/br9_pump.wav",
    },
    dmr = {
        id = "dmr", label = "MR-6 KESTREL", kind = "weapon", slot = "primary",
        desc = "Semi-automatic marksman emitter with a fixed 4x prism optic. Follow-ups without the wait.",
        world = "models/weapons/mr6_world.glb", root = "DMR",
        mag = 12, reserve = 48, max_reserve = 72, interval = 0.26, auto = false,
        stun = 38, head_mult = 1.6, range = 200,
        spread_hip = 3.0, spread_ads = 0.06, spread_move = 2.0, bloom = 0.25, bloom_max = 1.2,
        kick_pitch = 1.1, kick_yaw = 0.3, ads_kick = 0.65, kick_back = 0.035, kick_rot = 3.8,
        reload = 2.0, reload_empty = 2.45, equip = 0.5, lower = 0.26,
        hip = V(0.155, -0.165, -0.41), ads = V(0, -0.116, -0.26), hip_rot = V(1.8, 4.0, 0), zoom_fov = 0.66,
        scope = { 0.25 }, scope_at = 0.84, scope_sway = 0.16,
        muzzle = V(0, 0.045, -0.67), cell = V(0, 0, 0),
        fire = "audio/weapons/mr6_fire.wav", cell_out = "audio/weapons/lr4_cell_out.wav",
        cell_in = "audio/weapons/lr4_cell_in.wav", charge = "audio/weapons/lr4_charge.wav", noise = 28,
        zoom_sfx = "audio/weapons/lr4_zoom.wav",
    },
    sidearm = {
        id = "sidearm", label = "SP-2 WREN", kind = "weapon", slot = "secondary",
        desc = "Pulse sidearm. Light and quick to raise.",
        world = "models/weapons/sp2_world.glb", root = "Sidearm",
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
    scanner = {
        id = "scanner", label = "FIELD SCANNER", kind = "tool", slot = "tool",
        desc = "Pings nearby contacts and reads devices.",
        world = "models/env/field_device.glb",
    },
    field_kit = {
        id = "field_kit", label = "FK-1 FIELD KIT", kind = "utility", slot = "utility",
        desc = "Patch's spare kit. Two quick patch-ups when you can't wait it out.",
        world = "models/props/field_kit.glb", charges = 2, heal = 60, use_time = 1.6,
        use_sfx = "audio/weapons/kit_use.wav",
    },
    cell_pack = {
        id = "cell_pack", label = "CELL PACK", kind = "supply",
        desc = "Spare charge cells. Tops up every weapon you carry.",
        world = "models/props/cell_pack.glb", refill = 0.5,
    },
}

-- Slot order used for display and for weapon cycling.
Items.slots = { "primary", "secondary", "tool", "utility" }
Items.weapon_slots = { "primary", "secondary" }

function Items.get(id) return id and Items.defs[id] or nil end

function Items.is_weapon(id)
    local d = Items.defs[id]
    return d ~= nil and d.kind == "weapon"
end

-- Fresh per-item state (ammo, charges). Weapons start full.
function Items.new_state(id)
    local d = Items.defs[id]
    if not d then return nil end
    if d.kind == "weapon" then return { ammo = d.mag, reserve = d.reserve } end
    if d.charges then return { charges = d.charges } end
    return {}
end

-- Short line for prompts and storage readouts.
function Items.summary(id, st)
    local d = Items.defs[id]
    if not d then return "" end
    if d.kind == "weapon" and st then
        return string.format("%s  %d / %d", d.label, st.ammo or 0, st.reserve or 0)
    elseif d.charges and st then
        return string.format("%s  x%d", d.label, st.charges or 0)
    end
    return d.label
end

return Items
