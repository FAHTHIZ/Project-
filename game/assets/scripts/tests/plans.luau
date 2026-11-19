-- Autotest plans: lists of timed steps { at = seconds, move = vector|false, look = vector|false,
-- press = action, release = action, run = function(ctx) }. Checks call ctx.check(name, ok, detail).
local Game = require("scripts/lib/game")

local V = vector.create
local Plans = {}

local function ps() return Game.player_state end
local function pos() return Game.player.position end

-- First-person movement, look, jump, crouch, pause and interaction on the dev range.
Plans.movement = {
    { at = 0.5, run = function(c)
        c.data.p0 = pos()
        c.data.yaw0 = ps().yaw
        c.check("player_rig", Game.player ~= nil and Game.camera ~= nil, "player and camera found")
        c.check("first_person_camera", Game.camera.parent and Game.camera.parent.name == "Head", "camera under Head")
    end },
    { at = 0.5, move = V(0, 1, 0) },
    { at = 2.5, move = false, run = function(c)
        local d = pos() - c.data.p0
        local yr = math.rad(c.data.yaw0)
        local along = d.x * -math.sin(yr) + d.z * -math.cos(yr)
        c.check("walk_forward", along > 4.5 and along < 9, string.format("moved %.2f m", along))
    end },
    { at = 3.0, look = V(4, 0, 0) },
    { at = 3.5, look = false, run = function(c)
        local dy = ps().yaw - c.data.yaw0
        c.check("look_yaw", dy < -40, string.format("yaw delta %.1f", dy))
    end },
    { at = 3.6, look = V(0, -30, 0) },
    { at = 4.2, look = false, run = function(c)
        c.check("pitch_clamp", math.abs(ps().pitch - 84) < 0.01, string.format("pitch %.2f", ps().pitch))
    end },
    { at = 4.3, look = V(0, 14, 0) },
    { at = 4.67, look = false },
    { at = 4.8, look = false, run = function(c) c.data.y0 = pos().y end },
    { at = 4.9, press = "jump" },
    { at = 4.95, release = "jump" },
    { at = 5.2, run = function(c)
        c.check("jump", pos().y - c.data.y0 > 0.3, string.format("rose %.2f m", pos().y - c.data.y0))
    end },
    { at = 6.2, run = function(c)
        c.check("land", math.abs(pos().y - c.data.y0) < 0.05 and Game.player.grounded, string.format("y %.3f", pos().y))
    end },
    { at = 6.3, press = "crouch" },
    { at = 6.35, release = "crouch" },
    { at = 7.0, run = function(c)
        c.check("crouch", ps().crouched and ps().eye < 1.2, string.format("eye %.2f", ps().eye))
    end },
    { at = 7.1, press = "crouch" },
    { at = 7.15, release = "crouch" },
    { at = 7.8, run = function(c)
        c.check("stand", not ps().crouched and ps().eye > 1.55, string.format("eye %.2f", ps().eye))
        c.data.p1 = pos()
    end },
    { at = 7.9, press = "pause" },
    { at = 7.95, release = "pause" },
    { at = 8.0, move = V(0, 1, 0), run = function(c)
        c.check("pause_opens", Game.paused == true, "Game.paused")
    end },
    { at = 9.0, move = false, run = function(c)
        local d = vector.magnitude(pos() - c.data.p1)
        c.check("pause_blocks_movement", d < 0.05, string.format("moved %.3f m while paused", d))
        if Game.pause_menu then Game.pause_menu:on_click(nil, "resume") end
    end },
    { at = 9.1, run = function(c)
        c.check("pause_resumes", Game.paused == false, "Game.paused")
    end },
    { at = 9.2, move = V(0, 1, 0) },
    { at = 9.8, move = false, run = function(c)
        local d = vector.magnitude(pos() - c.data.p1)
        c.check("moves_after_resume", d > 0.5, string.format("moved %.2f m", d))
    end },
}

-- HUD presentation check (used for screenshots): forces touch controls and diagnostics on and
-- fills the objective, toast and subtitle so their layout can be inspected.
Plans.hud = {
    { at = 0.1, run = function(c)
        Game.settings.touch_controls = "on"
        Game.settings.diagnostics = true
        Game.set_objective("Reach the ranger station past the old fence line", "Operation 01: Greenline")
        Game.toast("Checkpoint reached", 30)
        Game.show_subtitle("Anchor", "Keep it quiet, Rook. Patch, Echo, on me.", 30)
        c.check("hud_api", Game.toast ~= nil and Game.set_objective ~= nil and Game.show_subtitle ~= nil, "HUD functions defined")
    end },
    { at = 1.5, run = function(c)
        c.check("hud_objective", Game.objective ~= nil and Game.objective.text ~= nil, "objective set")
    end },
}

-- Pause and settings modal (screenshots and a basic open/close check).
Plans.pause_ui = {
    { at = 0.3, press = "pause" },
    { at = 0.35, release = "pause" },
    { at = 0.5, run = function(c)
        c.check("pause_open", Game.paused == true, "Game.paused")
        if Game.pause_menu then Game.pause_menu:on_click(nil, "settings") end
    end },
    { at = 0.8, run = function(c)
        local m = Game.pause_menu
        c.check("settings_open", m ~= nil and m.settings_panel ~= nil and m.settings_panel:visible(), "settings panel visible")
    end },
}

-- Weapons on the dev range: equip, aim, automatic and semi-automatic fire, hits on a target,
-- recoil recovery, reload, switching, sprint and pause blocking, and the scanner tool.
local function wp() return Game.weapons end
local function aim_at(name, h)
    local t = scene.find(name)
    local cam = ps().cam.world_position
    local p = t.world_position + V(0, h or 1.3, 0)
    local d = p - cam
    ps().yaw = math.deg(math.atan2(-d.x, -d.z))
    ps().pitch = math.deg(math.asin(d.y / vector.magnitude(d)))
end
local function shots() return wp() and wp().shots or 0 end
Plans.weapons = {
    { at = 0.3, run = function(c)
        c.check("weapons_script", wp() ~= nil and wp().pivot ~= nil, "Game.weapons with VM Pivot")
        c.check("loadout", wp().w.carbine ~= nil and wp().w.sidearm ~= nil, "carbine and sidearm parts found")
    end },
    { at = 0.8, run = function(c)
        local h = Game.weapon_hud
        c.check("equip_carbine", wp().current == "carbine" and wp().state == "idle", tostring(wp().state))
        c.check("hud_weapon", h ~= nil and h.name == "PC-7 LANTERN" and h.ammo == 30, h and (h.name .. " " .. h.ammo) or "nil")
        aim_at("Target 0")
        c.data.pitch0 = ps().pitch
    end },
    { at = 0.85, press = "aim" },
    { at = 1.3, run = function(c)
        c.check("aim_zoom", ps().zoom > 0.9 and ps().zoom_fov ~= nil, string.format("zoom %.2f", ps().zoom))
        c.data.s0 = shots(); c.data.hits0 = wp().hits; c.data.downs0 = Game.combat.stats.downs
    end },
    { at = 1.3, press = "fire" },
    { at = 1.8, release = "fire", run = function(c)
        local n = shots() - c.data.s0
        c.check("auto_fire", n >= 4 and n <= 7, string.format("%d shots in 0.5 s", n))
        c.check("ammo_spent", wp().w.carbine.st.ammo == 30 - n, string.format("ammo %d", wp().w.carbine.st.ammo))
        c.check("hits_target", wp().hits - c.data.hits0 >= 3, string.format("%d hits", wp().hits - c.data.hits0))
        c.check("recoil_kicks", ps().pitch > c.data.pitch0 + 0.5, string.format("pitch +%.2f", ps().pitch - c.data.pitch0))
    end },
    { at = 2.4, run = function(c)
        c.check("target_down", Game.combat.stats.downs > c.data.downs0, "target stunned")
        c.check("recoil_recovers", math.abs(ps().pitch - c.data.pitch0) < 1.5,
                string.format("pitch offset %.2f", ps().pitch - c.data.pitch0))
        c.data.reserve0 = wp().w.carbine.st.reserve
        c.data.ammo0 = wp().w.carbine.st.ammo
    end },
    { at = 2.4, release = "aim" },
    { at = 2.5, press = "reload" },
    { at = 2.55, release = "reload", run = function(c)
        c.check("reload_starts", wp().state == "reload", tostring(wp().state))
    end },
    { at = 4.5, run = function(c)
        local r = wp().w.carbine
        c.check("reload_fills", r.st.ammo == 30 and r.st.reserve == c.data.reserve0 - (30 - c.data.ammo0),
                string.format("ammo %d reserve %d", r.st.ammo, r.st.reserve))
        c.check("reload_parts_reset", vector.magnitude(r.cell.position - r.cell_home) < 1e-3, "cell home")
        r.st.ammo = 1
        c.data.s1 = shots()
    end },
    { at = 4.5, press = "fire" },
    { at = 4.9, release = "fire", run = function(c)
        c.check("empty_stops", shots() - c.data.s1 == 1, string.format("%d shots", shots() - c.data.s1))
    end },
    { at = 5.0, run = function(c)
        c.check("auto_reload", wp().state == "reload", tostring(wp().state))
    end },
    { at = 7.6, press = "switch" },
    { at = 7.65, release = "switch" },
    { at = 8.4, run = function(c)
        c.check("switch_sidearm", wp().current == "sidearm" and wp().state == "idle", tostring(wp().current))
        c.check("hud_sidearm", Game.weapon_hud.name == "SP-2 WREN", Game.weapon_hud.name)
        c.check("carbine_hidden", not wp():visible("carbine") and wp():visible("sidearm"), "visibility")
        aim_at("Target 1")
        c.data.s2 = shots()
    end },
    { at = 8.4, press = "fire" },
    { at = 9.0, release = "fire", run = function(c)
        c.check("semi_auto", shots() - c.data.s2 == 1, string.format("%d shots holding the trigger", shots() - c.data.s2))
    end },
    { at = 9.1, press = "fire" },
    { at = 9.15, release = "fire" },
    { at = 9.4, press = "fire" },
    { at = 9.45, release = "fire", run = function(c)
        c.check("semi_auto_taps", shots() - c.data.s2 == 3, string.format("%d shots", shots() - c.data.s2))
    end },
    { at = 9.5, press = "weapon1" },
    { at = 9.55, release = "weapon1" },
    { at = 10.3, run = function(c)
        c.check("weapon1_key", wp().current == "carbine", tostring(wp().current))
        c.data.s3 = shots()
    end },
    { at = 10.3, move = V(0, 1, 0), press = "sprint" },
    { at = 10.8, press = "fire" },
    { at = 11.3, release = "fire", run = function(c)
        c.check("sprint_blocks_fire", shots() == c.data.s3, string.format("%d shots while sprinting", shots() - c.data.s3))
    end },
    { at = 11.3, move = false, release = "sprint" },
    { at = 11.8, press = "tool" },
    { at = 11.85, release = "tool" },
    { at = 12.1, run = function(c)
        c.check("scan_tool", Game.tool_hud ~= nil and Game.tool_hud:find("SCAN ") ~= nil and wp().last_scan >= 1,
                tostring(Game.tool_hud))
    end },
    { at = 12.2, press = "pause" },
    { at = 12.25, release = "pause", run = function(c) c.data.s4 = shots() end },
    { at = 12.3, press = "fire" },
    { at = 12.8, release = "fire", run = function(c)
        c.check("pause_blocks_fire", shots() == c.data.s4 and Game.paused, string.format("%d shots", shots() - c.data.s4))
        if Game.pause_menu then Game.pause_menu:on_click(nil, "resume") end
    end },
    { at = 13.0, run = function(c)
        local st = wp():save_state()
        c.check("save_state", st.ammo.carbine ~= nil and st.current == "carbine", "weapon state serialises")
    end },
}

-- Viewmodel poses for screenshots (no checks beyond reaching the pose).
Plans.vm_ads = { { at = 0.6, press = "aim" }, { at = 1.6, run = function(c) local p = Game.weapons.pivot.position; c.check("ads", ps().zoom > 0.9, string.format("zoom %.2f pivot %.3f %.3f %.3f t %.2f", ps().zoom, p.x, p.y, p.z, time.now())) end } }
Plans.vm_reload = { { at = 0.5, run = function() Game.weapons.w.carbine.st.ammo = 20 end }, { at = 0.6, press = "reload" }, { at = 0.62, release = "reload" },
                    { at = 1.2, run = function() Game.weapons.hold_pose = true; Game.weapons.st = Game.weapons.reload_len * 0.36 end } }
Plans.vm_sidearm = { { at = 0.4, press = "weapon2" }, { at = 0.45, release = "weapon2" }, { at = 0.8, press = "aim" } }
Plans.vm_scan = { { at = 0.6, press = "tool" }, { at = 0.65, release = "tool" },
                  { at = 0.9, run = function() Game.weapons.scan_anim = 0.6; Game.weapons.scan_hold = true end } }
-- Screenshot plans keep their held input until the capture: the driver releases everything at END.
for _, n in { "vm_ads", "vm_reload", "vm_sidearm", "vm_scan" } do table.insert(Plans[n], { at = 25 }) end

for k, v in require("scripts/tests/squad_plans") do Plans[k] = v end
for k, v in require("scripts/tests/vehicle_plans") do Plans[k] = v end
for k, v in require("scripts/tests/world_plans") do Plans[k] = v end

return Plans
