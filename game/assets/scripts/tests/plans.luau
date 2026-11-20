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
        -- queue hygiene: three objectives in a row leave at most one waiting objective toast
        Game.set_objective("Cross the footbridge")
        Game.set_objective("Check the cabin")
        Game.set_objective("Reach the relay mast")
        local q, n = Game.toast_queue, 0
        for i = 2, #q do if q[i].kind == "objective" then n += 1 end end
        Game.toast("Checkpoint reached", 30)
        local dup = 0
        for _, t in q do if t.text == "Checkpoint reached" then dup += 1 end end
        c.check("hud_toast_queue", n == 1 and q[#q].text ~= "New objective: Cross the footbridge" and dup == 1,
            string.format("waiting objective toasts %d, duplicate checkpoint toasts %d, queue %d", n, dup, #q))
        Game.present.title = "OPERATION 02"
        c.toast_t = q[1] and q[1].t
        c.toast_head = q[1]
    end },
    { at = 2.5, run = function(c)
        local q = Game.toast_queue
        c.check("hud_toast_waits_for_title", q[1] ~= nil and q[1].t == c.toast_t,
            string.format("toast timer %.2f -> %.2f while the title card is up", c.toast_t or -1, q[1] and q[1].t or -1))
        local ret, comp = scene.find("Reticle"), scene.find("Compass")
        c.check("hud_card_clears_centre", ret ~= nil and comp ~= nil and not ret:visible() and not comp:visible(),
            "reticle and compass hidden under the chapter card")
        Game.present.title = nil
        -- a long two-line radio line gets a taller plate than a one-word bark
        Game.show_subtitle("Lamplight", "Halyard, Lamplight. Three nights ago, three posts on the Northline corridor were hit. Every public statement says Lydria did it.", 30)
    end },
    { at = 3.0, run = function(c)
        local q = Game.toast_queue
        c.check("hud_toast_resumes", q[1] ~= c.toast_head or q[1].t < c.toast_t, "toast timer runs again after the title card")
        c.check("hud_stale_objective_toast", q[1] == nil or q[1].text ~= "New objective: Reach the ranger station past the old fence line",
            "the superseded objective toast was cut short")
        local ret = scene.find("Reticle")
        c.check("hud_reticle_back", ret ~= nil and ret:visible(), "reticle returns after the card")
        local sub = scene.find("Subtitle")
        local h = sub and sub:get("UiRect").size[2] or 0
        c.check("hud_subtitle_plate_fits", h >= 2 * 30 + 40, string.format("plate height %d for a two-line line", h))
    end },
}

-- Pause and settings modal (screenshots and a basic open/close check).
-- Front end: boot cards play, a tap skips to the reveal, the title waits for "start", the list
-- slides in fully opaque, and returning to the menu (booted) goes straight to the list.
Plans.menu_flow = {
    { at = 0.3, run = function(c)
        local m = Game.menu
        c.check("menu_up", m ~= nil, "Game.menu")
        c.check("boot_first", m.phase == "boot" and m.el["Boot"]:visible(), "phase " .. tostring(m.phase))
        c.check("list_hidden_in_boot", not m.main:visible(), "list hidden")
    end },
    { at = 1.6, run = function(c)
        local m = Game.menu
        local op = m.el["Boot Studio"]:get("UiRect").opacity
        c.check("studio_card_fades_in", op > 0.5, string.format("opacity %.2f", op))
        m:on_click(nil, "skip_boot")
        c.check("skip_jumps_to_reveal", m.t >= 8.6, string.format("t %.2f", m.t))
    end },
    { at = 5.0, run = function(c)
        local m = Game.menu
        c.check("title_phase", m.phase == "title" and m.el["Menu Press"]:visible(), "phase " .. tostring(m.phase))
        c.check("boot_gone", not m.el["Boot"]:visible(), "boot hidden")
        m:on_click(nil, "start")
    end },
    { at = 6.5, run = function(c)
        local m = Game.menu
        c.check("main_phase", m.phase == "main" and m.main:visible(), "phase " .. tostring(m.phase))
        local r = m.rows[5]:get("UiRect")
        c.check("rows_settled", r.opacity > 0.99 and math.abs(r.position[1]) < 0.5,
                string.format("row5 opacity %.2f x %.2f", r.opacity, r.position[1]))
        c.check("booted_flag", Game.front_end_booted == true, "front_end_booted")
        local l = scene.find("Menu Continue Label")
        local txt = l and l:get("UiText").text or ""
        c.check("caps_labels", txt == string.upper(txt) and #txt > 0, txt)
    end },
}

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
        -- body-cam lens setting drives the Environment (VICTUS ADR-0146)
        local env = scene.find("Environment"):get("Environment")
        c.check("lens_on_by_default", math.abs(env.film_grain - Game.LENS.film_grain) < 1e-3,
            string.format("film_grain %.3f", env.film_grain))
        for _ = 1, 4 do m:change("lens_effects", "-") end
        env = scene.find("Environment"):get("Environment")
        c.check("lens_off", Game.settings.lens_effects == 0 and env.film_grain == 0 and env.chromatic_aberration == 0
            and env.lens_distortion == 0, string.format("setting %.2f grain %.3f", Game.settings.lens_effects, env.film_grain))
        m:change("lens_effects", "+"); m:change("lens_effects", "+")
        env = scene.find("Environment"):get("Environment")
        c.check("lens_half", math.abs(env.chromatic_aberration - Game.LENS.chromatic_aberration * 0.5) < 1e-3,
            string.format("ca %.3f", env.chromatic_aberration))
        Game.settings.lens_effects = 1.0; Game.apply_lens()
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

-- Body-cam handling: calm tactical reload stows the cell, stress builds from incoming fire, a
-- stressed empty reload fumbles at the well and retries, held RELOAD checks the cell, a long burst
-- ends with a re-grip.
Plans.reload_feel = {
    { at = 0.5, run = function(c)
        c.check("calm_start", wp().state == "idle" and wp().stress < 0.01, string.format("%s stress %.2f", wp().state, wp().stress))
        wp().w.carbine.st.ammo = 10
    end },
    { at = 0.6, press = "reload" },
    { at = 0.65, release = "reload", run = function(c)
        c.check("tactical_reload", wp().state == "reload" and not wp().reload_empty and not wp().fumble,
                string.format("%s empty %s fumble %s", wp().state, tostring(wp().reload_empty), tostring(wp().fumble)))
    end },
    { at = 1.38, run = function(c)
        local r = wp().w.carbine
        local d = r.cell.position - r.cell_home
        c.check("tactical_cell_stowed", d.x < -0.05 and d.z > 0.05, string.format("cell offset %.3f %.3f %.3f", d.x, d.y, d.z))
    end },
    { at = 2.7, run = function(c)
        local r = wp().w.carbine
        c.check("tactical_fills", wp().state == "idle" and r.st.ammo == 30, string.format("%s ammo %d", wp().state, r.st.ammo))
        c.check("rest_varies", vector.magnitude(wp().rest_target) > 0, "new resting hold")
        Game.emit("near_miss", pos() + V(3, 1.5, -6))
        c.check("near_miss_stress", wp().stress >= 0.2, string.format("stress %.2f", wp().stress))
        wp():add_stress(1)
        wp().fumble_from = 0       -- make the fumble certain for the check
        r.st.ammo = 0
    end },
    { at = 2.8, press = "reload" },
    { at = 2.85, release = "reload", run = function(c)
        local w = wp()
        c.check("stressed_reload", w.state == "reload" and w.reload_empty and w.fumble and w.reload_base < 2.25 * 0.92,
                string.format("fumble %s base %.2f len %.2f", tostring(w.fumble), w.reload_base or -1, w.reload_len or -1))
    end },
    { at = 4.15, run = function(c)
        local u, fu = wp():reload_phase()
        c.check("fumble_holds_at_well", wp().state == "reload" and fu ~= nil and math.abs(u - 0.555) < 1e-3,
                string.format("phase %.3f fumble %s", u, tostring(fu)))
    end },
    { at = 5.6, run = function(c)
        local r = wp().w.carbine
        c.check("fumble_recovers", wp().state == "idle" and r.st.ammo == 30 and wp().fumbles == 1
                and vector.magnitude(r.cell.position - r.cell_home) < 1e-3,
                string.format("%s ammo %d fumbles %d", wp().state, r.st.ammo, wp().fumbles))
        c.check("stress_holds", wp().stress > 0.8, string.format("stress %.2f", wp().stress))
        wp().fumble_from = 0.55
        wp().stress = 0
    end },
    { at = 5.8, press = "reload" },
    { at = 5.85, release = "reload", run = function(c)
        c.check("full_cell_checks", wp().state == "check", tostring(wp().state))
    end },
    { at = 6.5, run = function(c)
        c.check("check_reads_cell", wp().check_text == "Cell full", tostring(wp().check_text))
    end },
    { at = 7.3, run = function(c)
        c.check("check_ends", wp().state == "idle", tostring(wp().state))
        wp().w.carbine.st.ammo = 14
        c.data.res = wp().w.carbine.st.reserve
    end },
    { at = 7.5, press = "reload" },
    { at = 7.6, run = function(c) c.check("hold_starts_reload", wp().state == "reload", tostring(wp().state)) end },
    { at = 8.0, run = function(c)
        c.check("hold_turns_into_check", wp().state == "check" and wp().w.carbine.st.ammo == 14, tostring(wp().state))
    end },
    { at = 8.1, release = "reload" },
    { at = 9.0, run = function(c)
        c.check("check_reads_half", wp().check_text == "Cell about half" and wp().w.carbine.st.reserve == c.data.res,
                tostring(wp().check_text))
    end },
    { at = 9.6, run = function(c)
        c.check("check_done", wp().state == "idle", tostring(wp().state))
        aim_at("Target 0")
        wp().w.carbine.st.ammo = 30
    end },
    { at = 9.7, press = "fire" },
    { at = 10.7, release = "fire" },
    { at = 10.8, run = function(c)
        c.check("burst_regrip", wp().regrip_t ~= nil, string.format("regrip %s", tostring(wp().regrip_t)))
    end },
    { at = 11.6, run = function(c)
        local r = wp().w.carbine
        c.check("regrip_done", wp().regrip_t == nil and vector.magnitude(r.hand_l.position - r.hand_home) < 1e-3, "hand home")
    end },
    -- Body-cam lens: rolls into a strafe, jolts at sprinting footfalls, settles when still.
    { at = 12.0, move = V(1, 0, 0) },
    { at = 12.5, run = function(c)
        local z = ps().cam.rotation.z - math.cos(ps().bob) * 0.02 * 25
        c.check("strafe_roll", math.abs(ps().body.roll) > 0.6, string.format("roll %.2f deg (cam z %.2f)", ps().body.roll, z))
    end },
    { at = 12.6, move = false },
    { at = 13.0, move = V(0, 1, 0), press = "sprint", run = function(c) c.data.ymin = 0 end },
    { at = 13.1, run = function(c) c.data.ymin = math.min(c.data.ymin, ps().body.y) end },
    { at = 13.4, run = function(c) c.data.ymin = math.min(c.data.ymin, ps().body.y) end },
    { at = 13.7, run = function(c) c.data.ymin = math.min(c.data.ymin, ps().body.y) end },
    { at = 14.0, run = function(c) c.data.ymin = math.min(c.data.ymin, ps().body.y) end },
    { at = 14.3, run = function(c)
        c.data.ymin = math.min(c.data.ymin, ps().body.y)
        c.check("sprint_footfall_jolt", c.data.ymin < -0.003, string.format("lowest %.4f m", c.data.ymin))
    end },
    { at = 14.3, move = false, release = "sprint" },
    { at = 16.5, run = function(c)
        local b = ps().body
        c.check("lens_settles", math.abs(b.roll) < 0.1 and math.abs(b.pitch) < 0.1 and math.abs(b.y) < 0.002,
                string.format("roll %.3f pitch %.3f y %.4f", b.roll, b.pitch, b.y))
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
-- Sight pictures of the other primaries (scenes/tests/vm_ads_<id>.vscene): give, equip, aim.
local Inventory = require("scripts/lib/inventory")
for _, id in { "pdw", "breacher", "dmr" } do
    Plans["vm_ads_" .. id] = {
        { at = 0.3, run = function() Inventory.reset(); Game.weapons:give(id) end },
        { at = 2.2, press = "aim" },
        { at = 3.4, run = function(c) c.check("ads", ps().zoom > 0.9 and Game.weapons.current == id,
            string.format("%s zoom %.2f", tostring(Game.weapons.current), ps().zoom)) end },
    }
end
for _, n in { "vm_ads", "vm_reload", "vm_sidearm", "vm_scan", "vm_ads_pdw", "vm_ads_breacher", "vm_ads_dmr" } do table.insert(Plans[n], { at = 25 }) end

-- Footsteps: one footfall per head-bob half cycle, surface detection, AI hearing reach by gait
-- (walk short, sprint far, crouch silent) and a landing thump after a jump.
Plans.footsteps = {
    { at = 0.3, run = function(c)
        local Footsteps = require("scripts/lib/footsteps")
        local Combat = require("scripts/lib/combat")
        c.data.steps, c.data.noises = {}, {}
        Game.on("player_step", function(surf, speed) table.insert(c.data.steps, { t = time.now(), s = surf, v = speed }) end)
        Combat.on_noise(function(p, r, src)
            if src and src.valid and Game.player and src.id == Game.player.id then table.insert(c.data.noises, { t = time.now(), r = r }) end
        end)
        local s = Footsteps.surface_at(Game.player.position, Game.player)
        c.check("surface_detected", s == "concrete", "range ground = " .. tostring(s))
        local w = Footsteps.weather()
        c.check("weather_read", w and w.wet >= 0, string.format("wet %.2f puddles %.2f", w.wet, w.puddles))
    end },
    -- walk 3 s
    { at = 0.5, move = V(0, 1, 0), run = function(c) c.data.mark = { #c.data.steps, #c.data.noises, time.now() } end },
    { at = 3.5, move = false, run = function(c)
        local n = #c.data.steps - c.data.mark[1]
        local rate = n / (time.now() - c.data.mark[3])
        c.check("walk_cadence", rate > 1.6 and rate < 3.4, string.format("%d steps, %.2f/s", n, rate))
        local maxr = 0
        for i = c.data.mark[2] + 1, #c.data.noises do maxr = math.max(maxr, c.data.noises[i].r) end
        c.check("walk_noise_short", maxr > 0 and maxr < 3, string.format("max reach %.1f m", maxr))
        c.data.walk_rate = rate
    end },
    -- turn around and sprint 2 s
    { at = 3.6, look = V(18, 0, 0) },
    { at = 4.1, look = false },
    { at = 4.3, move = V(0, 1, 0), press = "sprint", run = function(c) c.data.mark = { #c.data.steps, #c.data.noises, time.now() } end },
    { at = 6.3, move = false, release = "sprint", run = function(c)
        local n = #c.data.steps - c.data.mark[1]
        local rate = n / (time.now() - c.data.mark[3])
        c.check("sprint_cadence", rate > c.data.walk_rate, string.format("%d steps, %.2f/s (walk %.2f/s)", n, rate, c.data.walk_rate))
        local maxr = 0
        for i = c.data.mark[2] + 1, #c.data.noises do maxr = math.max(maxr, c.data.noises[i].r) end
        c.check("sprint_noise_far", maxr > 5, string.format("max reach %.1f m", maxr))
    end },
    -- crouch-walk 2 s: steps, but no noise
    { at = 6.8, press = "crouch" },
    { at = 6.85, release = "crouch" },
    { at = 7.2, move = V(0, 1, 0), run = function(c) c.data.mark = { #c.data.steps, #c.data.noises, time.now() } end },
    { at = 9.2, move = false, run = function(c)
        local n = #c.data.steps - c.data.mark[1]
        local nn = #c.data.noises - c.data.mark[2]
        c.check("crouch_silent", n >= 2 and nn == 0, string.format("%d steps, %d noises", n, nn))
    end },
    { at = 9.3, press = "crouch" },
    { at = 9.35, release = "crouch" },
    -- jump: the landing makes a noise
    { at = 9.9, press = "jump", run = function(c) c.data.mark = { #c.data.steps, #c.data.noises, time.now() } end },
    { at = 9.95, release = "jump" },
    { at = 11.0, run = function(c)
        local nn = #c.data.noises - c.data.mark[2]
        c.check("landing_noise", nn >= 1 and Game.player.grounded, string.format("%d noises after the jump", nn))
    end },
}

for k, v in require("scripts/tests/squad_plans") do Plans[k] = v end
for k, v in require("scripts/tests/vehicle_plans") do Plans[k] = v end
for k, v in require("scripts/tests/world_plans") do Plans[k] = v end


-- Story run-through for the interior chapters (scenes/tests/story_op04..07.vscene): every quarter
-- second the driver walks Rook to the current waypoint, uses any enabled interactable the mission
-- registered, and stuns contractors that are hostile (not dormant, not under parley). It checks the
-- chapter reaches Campaign.complete and logs the stage path. Dialogue plays at real length.
local function story_plan(chapter, seconds)
    local steps = {}
    table.insert(steps, { at = 0.2, run = function(c)
        local Campaign = require("scripts/lib/campaign")
        c.data.stages = {}
        c.data.real_complete = Campaign.complete
        Campaign.complete = function(id) c.data.completed = id end
        c.data.now, c.data.walk, c.data.times = 0, 0, {}
        Game.on("mission_stage", function(name)
            table.insert(c.data.stages, name)
            table.insert(c.data.times, string.format("%s@%.0f", name, c.data.now))
        end)
    end })
    local t = 1.0
    while t < seconds do
        local at_t = t
        table.insert(steps, { at = t, run = function(c)
            if c.data.completed then return end
            c.data.now = at_t
            local m = Game.mission
            if not m or not m.stage_name then return end
            local wp = Game.waypoint
            if wp and wp.pos and Game.player then
                -- distance a player would have walked (the driver teleports), for the playtime estimate
                local d = Game.player.position - (wp.pos + V(0.6, 0.15, 0.6))
                local flat_d = math.sqrt(d.x * d.x + d.z * d.z)
                if flat_d > 1.5 then c.data.walk += flat_d end
                Game.player.position = wp.pos + V(0.6, 0.15, 0.6)
            end
            if not m.talking then
                -- try every enabled interactable in reach (some refuse until others are used)
                for _, r in Game.interactables do
                    if m.talking then break end
                    if r.enabled and r.entity.valid and r.fn then
                        local d = r.entity.position - Game.player.position
                        if not wp or vector.magnitude(d) < 4 then r.fn() end
                    end
                end
            end
            -- the relay is scanned with the field scanner, not used
            if m.stage_name == "relay" and m.flags and not m.flags.scanned then
                Game.emit("scanned", scene.find("Mark Relay Cell"))
            end
            local Squad = require("scripts/lib/squad")
            for _, rr in Squad.state().enemies do
                local e = rr.ctl
                if e and rr.entity.valid and not e.down and not e.dormant and not e.parley and not e.gone then
                    e:go_down(nil)
                end
            end
        end })
        t += 0.25
    end
    table.insert(steps, { at = seconds + 0.5, run = function(c)
        -- the open world is continuous: prologue..op02 hand over to the next chapter in place
        local reached = c.data.completed == chapter
        local handover = ({ prologue = "trail", op01 = "fence", op02 = "yard" })[chapter]
        if handover then
            reached = false
            for _, st in c.data.stages do if st == handover then reached = true end end
        end
        c.check(chapter .. "_complete", reached,
                "completed=" .. tostring(c.data.completed) .. " stages=" .. table.concat(c.data.stages, ",")
                .. " talking=" .. tostring(Game.mission and Game.mission.talking)
                .. " wp=" .. tostring(Game.waypoint and Game.waypoint.pos))
        print(string.format("STORY_TIMING %s scripted=%.0fs walked=%.0fm stages=%s", chapter, c.data.now,
                            c.data.walk, table.concat(c.data.times, ",")))
    end })
    return steps
end
Plans.story_op04 = story_plan("op04", 200)
Plans.story_op05 = story_plan("op05", 260)
Plans.story_op06 = story_plan("op06", 240)
Plans.story_op07 = story_plan("op07", 220)
-- open-world chapters (scenes/tests/story_<chapter>.vscene, tools/world/chapters.py)
Plans.story_prologue = story_plan("prologue", 260)
Plans.story_op01 = story_plan("op01", 320)
Plans.story_op02 = story_plan("op02", 300)
Plans.story_op03 = story_plan("op03", 240)
Plans.story_epilogue = story_plan("epilogue", 160)

return Plans
