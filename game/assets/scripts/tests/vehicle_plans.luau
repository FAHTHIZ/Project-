-- Autotest plans for the Mule vehicle, its cargo storage, the shared inventory, the LR-4 scope
-- and the field kit (scenes/tests/vehicle|trunk|sniper.vscene, tools/scenes/build_dev_range.py).
local Game = require("scripts/lib/game")
local Inventory = require("scripts/lib/inventory")
local Items = require("scripts/lib/items")
local Squad = require("scripts/lib/squad")

local V = vector.create
local P = {}

local function ps() return Game.player_state end
local function mule() return Game.vehicles and Game.vehicles["Mule"] end
local function cargo() return Game.storages and Game.storages["Mule_cargo"] end

-- Points the player's view at a world point (yaw/pitch, as a player would turn).
local function look_at(p)
    local s = ps()
    local cp = s.cam.world_position
    local d = p - cp
    s.yaw = math.deg(math.atan2(-d.x, -d.z))
    s.pitch = math.deg(math.atan2(d.y, math.sqrt(d.x * d.x + d.z * d.z)))
end

local function item_view(id)
    local st = cargo()
    if not st then return nil end
    for _, it in st.items do if it.id == id and it.view then return it.view.entity end end
    return nil
end

local function has(list, id)
    for _, x in list do if x == id then return true end end
    return false
end

local function flat(a, b) local d = a - b; return math.sqrt(d.x * d.x + d.z * d.z) end

-- Drive in, park, shut down, then each operator gets out through their own door in turn.
P.vehicle = {
    { at = 0.6, run = function(c)
        local v = mule()
        c.check("vehicle_registered", v ~= nil and v.chassis ~= nil, "Game.vehicles.Mule")
        local seated, worst = 0, 0
        Squad.each(function(who, op)
            if op:in_vehicle() then seated += 1 end
            worst = math.max(worst, vector.magnitude(op.entity.position - v:seat_root(op.seat)))
        end)
        c.check("squad_seated", seated == 4 and worst < 0.05, string.format("%d seated, worst %.3f m", seated, worst))
        v:start_engine()
    end },
    { at = 2.0, run = function(c)
        local v = mule()
        c.check("engine_idle", v:engine_on(), v.engine)
        v:drive({ V(-6, 0, 28), V(2, 0, 26.5), V(6, 0, 22), V(7, 0, 17) }, { speed = 6 })
        c.data.p0 = v.entity.position
    end },
    { at = 4.0, run = function(c)
        local v = mule()
        c.check("drives", v:driving() and v.speed > 1.5, string.format("speed %.2f m/s", v.speed))
        c.check("wheels_spin", math.abs(v.spin) > 1, string.format("spin %.1f", v.spin))
        local worst = 0
        Squad.each(function(who, op) worst = math.max(worst, vector.magnitude(op.entity.position - v:seat_root(op.seat))) end)
        c.check("occupants_follow", worst < 0.25, string.format("worst %.3f m", worst))
    end },
    { at = 12.0, run = function(c)
        local v = mule()
        local p = v.entity.position
        c.check("parked", not v:driving() and v.speed == 0 and flat(p, V(7, 0, 17)) < 0.05,
                string.format("at %.2f %.2f", p.x, p.z))
        c.check("parked_heading", math.abs(((v.yaw + 540) % 360) - 180) < 30, string.format("yaw %.1f", v.yaw))
        v:stop_engine()
        local delays = { Anchor = 0.0, Patch = 0.5, Echo = 1.3, Tally = 1.9 }
        local doors = { driver = "fl", front_right = "fr", rear_left = "rl", rear_right = "rr" }
        Squad.each(function(who, op)
            op:exit_vehicle(doors[op.seat], { delay = delays[who], regroup = V(2 + (delays[who] * 2), 0, 12),
                                              face = V(0, 0, 0) })
        end)
    end },
    { at = 13.6, run = function(c)
        local v = mule()
        c.check("engine_off", v.engine == "off" and v.engine_vol < 0.05, string.format("vol %.2f", v.engine_vol))
        c.check("doors_open_in_turn", v.doors.fl.a > 0.5 and v.doors.rr.a < 0.05,
                string.format("fl %.2f rr %.2f", v.doors.fl.a, v.doors.rr.a))
    end },
    { at = 20.0, run = function(c)
        local v = mule()
        local out, closed = 0, 0
        for _, k in { "fl", "fr", "rl", "rr" } do if v:door_closed(k) then closed += 1 end end
        local inside = 0
        Squad.each(function(who, op)
            if not op:in_vehicle() then out += 1 end
            -- no one may end up inside the body: vehicle-local |x| < 0.98 and |z| < 2.5
            local d = op.entity.position - v.entity.position
            local r, f = v.entity.right, v.entity.forward
            local lx, lz = vector.dot(d, r), vector.dot(d, f)
            if math.abs(lx) < 0.98 and math.abs(lz) < 2.5 then inside += 1 end
        end)
        c.check("squad_out", out == 4, string.format("%d out", out))
        c.check("doors_closed", closed == 4, string.format("%d closed", closed))
        c.check("clear_of_body", inside == 0, string.format("%d inside", inside))
    end },
    { at = 26.0, run = function(c)
        local near = 0
        Squad.each(function(who, op)
            local cs = op.entity:character_state()
            if cs and cs.grounded and op.entity.position.y < 0.2 then near += 1 end
        end)
        c.check("squad_grounded", near == 4, string.format("%d grounded", near))
    end },
}

-- The cargo bay: hatch interaction, looking at items, swap, refusals, supplies, persistence.
P.trunk = {
    { at = 0.5, run = function(c)
        Inventory.reset()
        c.check("storage_found", cargo() ~= nil, "Mule_cargo")
        local l = cargo():list()
        c.check("initial_contents", #l == 4 and has(l, "marksman") and has(l, "field_kit"), table.concat(l, ","))
        c.check("closed_items_locked", not Game.interactables[item_view("marksman").id].enabled, "prompt disabled while closed")
        look_at(mule().hatch.pivot.world_position + V(0, -0.6, 0.05))
    end },
    { at = 0.8, run = function(c)
        local f = Game.focus
        c.check("hatch_prompt", f ~= nil and f.prompt == "Open hatch", f and f.prompt or "none")
    end },
    { at = 0.85, press = "interact" }, { at = 0.9, release = "interact" },
    { at = 1.2, run = function(c)
        local a = mule():hatch_amount()
        c.check("hatch_animates", a > 0.05 and a < 0.95, string.format("hatch %.2f", a))
    end },
    { at = 2.6, run = function(c)
        c.check("hatch_open", mule():hatch_is_open(), string.format("hatch %.2f", mule():hatch_amount()))
        c.check("storage_open", cargo().open, "open")
    end },
    { at = 2.7, move = V(0, 1, 0) }, { at = 3.3, move = false },
    { at = 3.6, run = function(c)
        c.data.zpos = Game.player.position.z
        look_at(item_view("marksman").world_position + V(0, 0.05, 0))
    end },
    { at = 3.8, run = function(c)
        local f = Game.focus
        c.check("look_identifies", f ~= nil and f.prompt == "Swap PC-7 LANTERN for LR-4 HERON",
                f and f.prompt or ("none at z " .. c.data.zpos))
        c.check("description", f ~= nil and f.detail ~= nil and string.find(f.detail, "scope") ~= nil, f and f.detail or "")
    end },
    { at = 3.85, press = "interact" }, { at = 3.9, release = "interact" },
    { at = 4.0, run = function(c)
        c.check("took_marksman", Inventory.in_slot("primary") == "marksman", tostring(Inventory.in_slot("primary")))
        local l = cargo():list()
        c.check("carbine_stowed", has(l, "carbine") and not has(l, "marksman"), table.concat(l, ","))
        c.check("swap_lowers_first", Game.weapons.state == "lower" and Game.weapons.current == "carbine",
                Game.weapons.state .. " " .. tostring(Game.weapons.current))
    end },
    { at = 5.4, run = function(c)
        c.check("marksman_equipped", Game.weapons.current == "marksman" and Game.weapons.state == "idle",
                tostring(Game.weapons.current) .. " " .. Game.weapons.state)
        c.check("carbine_in_bay", item_view("carbine") ~= nil and item_view("carbine").position.y > -1, "visible in slot")
        -- cells full: a cell pack is refused, not consumed
        Game.weapons:refill()
        local n = #cargo():list()
        local i = cargo():find("cell_pack")
        local ok = cargo():take(i)
        c.check("supply_refused_when_full", not ok and #cargo():list() == n, "kept in storage")
        Game.weapons.w.marksman.st.reserve = 2
        ok = cargo():take(cargo():find("cell_pack"))
        c.check("supply_consumed", ok and Game.weapons.w.marksman.st.reserve > 2 and #cargo():list() == n - 1,
                string.format("reserve %d", Game.weapons.w.marksman.st.reserve))
        ok = cargo():take(cargo():find("field_kit"))
        c.check("kit_taken", ok and Inventory.in_slot("utility") == "field_kit", tostring(Inventory.in_slot("utility")))
    end },
    { at = 5.6, run = function(c)
        -- inventory rules
        local ok, reason = Inventory.take("not_an_item")
        c.check("invalid_item", ok == false and reason == "unknown", tostring(reason))
        ok, reason = Inventory.take("marksman")
        c.check("duplicate_refused", ok == false and reason == "carried", tostring(reason))
        local st = Inventory.drop("sidearm")
        c.check("drop", st ~= nil and not Inventory.has("sidearm"), "dropped sidearm")
        st.ammo = 3
        ok = Inventory.take("sidearm", st)
        c.check("repick_keeps_state", ok and Inventory.state("sidearm").ammo == 3, "ammo 3")
        -- checkpoint snapshot then mutate then restore
        c.data.inv = Inventory.serialize()
        c.data.sto = Game.Storage.serialize_all()
        Inventory.state("marksman").ammo = 0
        cargo():take(cargo():find("carbine"))
    end },
    { at = 7.2, run = function(c)
        c.check("swap_back", Inventory.in_slot("primary") == "carbine" and has(cargo():list(), "marksman"),
                tostring(Inventory.in_slot("primary")))
        Inventory.restore(c.data.inv)
        Game.Storage.restore_all(c.data.sto)
        c.check("save_restore_inventory", Inventory.in_slot("primary") == "marksman" and Inventory.state("marksman").ammo == 5,
                tostring(Inventory.in_slot("primary")))
        local l = cargo():list()
        c.check("save_restore_storage", has(l, "carbine") and not has(l, "marksman"), table.concat(l, ","))
        -- close and reopen keeps contents
        mule():toggle_hatch(Game.player)
    end },
    { at = 9.0, run = function(c)
        c.check("hatch_closed", mule():hatch_amount() < 0.01 and not cargo().open, string.format("%.2f", mule():hatch_amount()))
        c.data.before = table.concat(cargo():list(), ",")
        mule():toggle_hatch(Game.player)
    end },
    { at = 10.8, run = function(c)
        c.check("reopen_preserves", cargo().open and table.concat(cargo():list(), ",") == c.data.before, c.data.before)
    end },
}

-- LR-4 scope steps and sway, the field kit and interrupted equips.
P.sniper = {
    { at = 0.4, run = function(c)
        Inventory.reset({ primary = "marksman", secondary = "sidearm", tool = "scanner", utility = "field_kit" })
    end },
    { at = 1.6, run = function(c)
        c.check("marksman_ready", Game.weapons.current == "marksman" and Game.weapons.state == "idle",
                tostring(Game.weapons.current) .. " " .. Game.weapons.state)
        look_at(V(0, 1.3, -6))
    end },
    { at = 1.7, press = "aim" },
    { at = 2.6, run = function(c)
        c.check("scoped", Game.scope ~= nil and Game.weapons.scoped, "Game.scope")
        c.check("scope_hides_viewmodel", not Game.weapons:visible("marksman"), "hidden")
        local want = Game.settings.fov * 0.30
        c.check("scope_fov", math.abs(ps().fov - want) < 2.0, string.format("fov %.1f want %.1f", ps().fov, want))
        c.check("scope_sensitivity", ps().zoom_sens < 0.6, string.format("%.2f", ps().zoom_sens))
        c.data.yaw = ps().yaw
    end },
    { at = 2.65, press = "tool" }, { at = 2.7, release = "tool" },
    { at = 3.4, run = function(c)
        c.check("zoom_step_2", Game.scope and Game.scope.level == 2 and math.abs(ps().fov - Game.settings.fov * 0.16) < 1.5,
                string.format("fov %.1f", ps().fov))
        c.check("sway_bounded", math.abs(ps().yaw - c.data.yaw) < 1.0, string.format("%.2f deg", ps().yaw - c.data.yaw))
        c.data.ammo = Game.weapons.w.marksman.st.ammo
        c.data.hits = Game.weapons.hits
        look_at(V(0, 1.35, -6))
    end },
    { at = 3.45, press = "fire" }, { at = 3.5, release = "fire" },
    { at = 3.7, run = function(c)
        c.check("scoped_shot", Game.weapons.w.marksman.st.ammo == c.data.ammo - 1 and Game.weapons.hits > c.data.hits,
                string.format("ammo %d hits %d", Game.weapons.w.marksman.st.ammo, Game.weapons.hits))
    end },
    { at = 3.8, press = "fire" }, { at = 3.85, release = "fire" },
    { at = 3.95, run = function(c)
        c.check("bolt_interval", Game.weapons.w.marksman.st.ammo == c.data.ammo - 1, "second shot blocked by interval")
    end },
    { at = 4.0, release = "aim" },
    { at = 4.8, run = function(c)
        c.check("unscoped", Game.scope == nil and Game.weapons:visible("marksman"), "viewmodel back")
    end },
    -- interrupted equip: switch to the sidearm, then back while it is still rising
    { at = 4.9, press = "weapon2" }, { at = 4.95, release = "weapon2" },
    { at = 5.45, run = function(c) c.data.low = Game.weapons.lower_amt; c.data.st = Game.weapons.state end },
    { at = 5.46, press = "weapon1" }, { at = 5.5, release = "weapon1" },
    { at = 5.53, run = function(c)
        c.check("interrupted_equip_no_snap", Game.weapons.state == "lower" and Game.weapons.lower_amt >= c.data.low - 0.02,
                string.format("%s %.2f -> %s %.2f", c.data.st, c.data.low, Game.weapons.state, Game.weapons.lower_amt))
    end },
    { at = 7.0, run = function(c)
        c.check("back_to_marksman", Game.weapons.current == "marksman" and Game.weapons.state == "idle", Game.weapons.state)
        ps().health = 30
        ps().since_hit = 0
    end },
    { at = 7.1, press = "utility" }, { at = 7.15, release = "utility" },
    { at = 7.3, run = function(c) c.check("kit_starts", Game.weapons.state == "kit", Game.weapons.state) end },
    { at = 9.2, run = function(c)
        c.check("kit_heals", ps().health >= 89, string.format("health %.0f", ps().health))
        c.check("kit_charge_spent", Inventory.state("field_kit").charges == 1, "1 left")
        c.check("kit_weapon_back", Game.weapons.state == "idle", Game.weapons.state)
        ps().health = 20
        ps().since_hit = 0
    end },
    { at = 9.3, press = "utility" }, { at = 9.35, release = "utility" },
    { at = 11.4, run = function(c)
        c.check("kit_used_up", not Inventory.has("field_kit"), "removed after last charge")
        c.check("kit_hud_cleared", Game.kit_hud == nil, tostring(Game.kit_hud))
        ps().health = ps().max_health
    end },
    { at = 11.5, press = "utility" }, { at = 11.55, release = "utility" },
    { at = 11.8, run = function(c)
        c.check("no_kit_no_use", Game.weapons.state == "idle", Game.weapons.state)
    end },
}

-- Screenshot scene: the squad seated in the parked Mule, seen from outside.
P.vehicle_look = {
    { at = 0.5, run = function() look_at(V(-16, 1.2, 28)) end },
    { at = 30 },
}

-- Evidence views (no checks): the open bay with its contents, and the LR-4 scoped at zoom step 2.
P.trunk_look = {
    { at = 0.5, run = function() mule():set_hatch(true, "test") end },
    { at = 0.6, run = function() look_at(V(0, 0.95, 17.6)) end },
    { at = 30 },
}
P.scope_look = {
    { at = 0.4, run = function()
        Inventory.reset({ primary = "marksman", secondary = "sidearm", tool = "scanner", utility = "field_kit" })
    end },
    { at = 1.6, run = function() look_at(V(0, 1.35, -6)) end },
    { at = 1.7, press = "aim" },
    { at = 2.6, press = "tool" }, { at = 2.65, release = "tool" },
    { at = 30 },
}

-- Arms case (scenes/tests/armory.vscene): the always-open case swaps the carried primary for the
-- KV-5, BR-9 and MR-6; the BR-9 fires a pellet fan with a pump stroke; the MR-6 scope has one step.
local function case() return Game.storages and Game.storages["armory_case"] end
local function aim_target(name)
    local t = scene.find(name)
    local cp = ps().cam.world_position
    local d = t.world_position + V(0, 1.2, 0) - cp
    ps().yaw = math.deg(math.atan2(-d.x, -d.z))
    ps().pitch = math.deg(math.asin(d.y / vector.magnitude(d)))
end
P.armory = {
    { at = 0.5, run = function(c)
        Inventory.reset()
        c.check("case_found", case() ~= nil, "armory_case")
        local l = case():list()
        c.check("case_contents", #l == 3 and has(l, "pdw") and has(l, "breacher") and has(l, "dmr"), table.concat(l, ","))
        c.check("case_open", case().open == true, "no hatch gating")
        c.check("viewmodels", Game.weapons.w.pdw ~= nil and Game.weapons.w.breacher ~= nil and Game.weapons.w.dmr ~= nil,
                "PDW, Breacher and DMR roots found")
        c.check("pump_part", Game.weapons.w.breacher.slide ~= nil, "Breacher Slide")
        local ok = case():take(case():find("breacher"))
        c.check("took_breacher", ok and Inventory.in_slot("primary") == "breacher", tostring(Inventory.in_slot("primary")))
        local l2 = case():list()
        c.check("carbine_in_case", has(l2, "carbine") and not has(l2, "breacher"), table.concat(l2, ","))
    end },
    { at = 2.4, run = function(c)
        c.check("breacher_equipped", Game.weapons.current == "breacher" and Game.weapons.state == "idle",
                tostring(Game.weapons.current) .. " " .. Game.weapons.state)
        aim_target("Target 0")
        c.data.hits0 = Game.weapons.hits
        c.data.shots0 = Game.weapons.shots
    end },
    { at = 2.45, press = "fire" }, { at = 2.5, release = "fire" },
    { at = 2.62, run = function(c)
        local r = Game.weapons.w.breacher
        c.check("one_shell_per_pull", r.st.ammo == 5 and Game.weapons.shots == c.data.shots0 + 1,
                string.format("ammo %d", r.st.ammo))
        c.check("fan_hits_once", Game.weapons.hits == c.data.hits0 + 1, string.format("%d confirms", Game.weapons.hits - c.data.hits0))
    end },
    { at = 2.85, run = function(c)
        local r = Game.weapons.w.breacher
        local dz = (r.slide.position - r.slide_home).z
        c.check("pump_strokes", dz > 0.03, string.format("pump +%.3f m", dz))
    end },
    { at = 3.2, run = function(c)
        local r = Game.weapons.w.breacher
        c.check("pump_returns", vector.magnitude(r.slide.position - r.slide_home) < 0.01, "pump home")
        local ok = case():take(case():find("dmr"))
        c.check("took_dmr", ok and Inventory.in_slot("primary") == "dmr", tostring(Inventory.in_slot("primary")))
        c.check("breacher_back_in_case", has(case():list(), "breacher"), table.concat(case():list(), ","))
    end },
    { at = 5.0, run = function(c)
        c.check("dmr_equipped", Game.weapons.current == "dmr" and Game.weapons.state == "idle",
                tostring(Game.weapons.current) .. " " .. Game.weapons.state)
        aim_target("Target 4")
        c.data.shots1 = Game.weapons.shots
    end },
    { at = 5.05, press = "aim" },
    { at = 5.8, run = function(c)
        c.check("dmr_scoped", Game.scope ~= nil and Game.scope.levels == 1, Game.scope and tostring(Game.scope.levels) or "nil")
    end },
    { at = 5.8, press = "fire" }, { at = 5.85, release = "fire" },
    { at = 6.15, press = "fire" }, { at = 6.2, release = "fire" },
    { at = 6.5, release = "aim", run = function(c)
        c.check("dmr_semi_follow_up", Game.weapons.shots == c.data.shots1 + 2, string.format("%d shots", Game.weapons.shots - c.data.shots1))
        local ok = case():take(case():find("pdw"))
        c.check("took_pdw", ok and Inventory.in_slot("primary") == "pdw", tostring(Inventory.in_slot("primary")))
    end },
    { at = 8.0, run = function(c)
        c.check("pdw_equipped", Game.weapons.current == "pdw" and Game.weapons.state == "idle",
                tostring(Game.weapons.current) .. " " .. Game.weapons.state)
        aim_target("Target 0")
        c.data.shots2 = Game.weapons.shots
    end },
    { at = 8.05, press = "fire" },
    { at = 8.55, release = "fire", run = function(c)
        local n = Game.weapons.shots - c.data.shots2
        c.check("pdw_auto_rate", n >= 6 and n <= 9, string.format("%d shots in 0.5 s", n))
    end },
}

return P
