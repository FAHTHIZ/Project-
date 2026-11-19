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
        hip = V(0.15, -0.165, -0.40), ads = V(0, -0.1135, -0.30), hip_rot = V(1.5, 3.5, 0), zoom_fov = 0.72,
        muzzle = V(0, 0.045, -0.52), cell = V(0, 0, 0),
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
