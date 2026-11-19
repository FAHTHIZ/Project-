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

return Plans
