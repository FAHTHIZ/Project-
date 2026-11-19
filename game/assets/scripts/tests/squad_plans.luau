-- Autotest plans for the Halyard Team, the dialogue scheduler, faces and Greyline contractors.
local Game = require("scripts/lib/game")
local Squad = require("scripts/lib/squad")
local Dialogue = require("scripts/lib/dialogue")
local Combat = require("scripts/lib/combat")

local V = vector.create
local P = {}

local function ps() return Game.player_state end
local function flat(a, b) local d = a - b; return math.sqrt(d.x * d.x + d.z * d.z) end

-- Formation follow, hold order, dialogue scheduling, subtitles, lip sync and eye-lines.
P.squad = {
    { at = 1.0, run = function(c)
        c.check("squad_registered", Squad.count() == 4, "members " .. Squad.count())
        local faces, voices = 0, 0
        Squad.each(function(_, m)
            if m.actor.face and m.actor.face.mesh then faces += 1 end
            if m.actor.voice then voices += 1 end
        end)
        c.check("faces_found", faces == 4, "faces " .. faces)
        c.check("voices_found", voices == 4, "voices " .. voices)
        c.check("hollis_speaker", Dialogue.actor("hollis") ~= nil, "")
        c.check("radio_voice", Dialogue.state().radio ~= nil, "")
        local Face = require("scripts/lib/face")
        local a = Squad.member("Anchor").actor
        local gl = a.carry:find_child("Grip L")
        local gr = a.carry:find_child("Grip R")
        local dl = vector.magnitude(a.hand_l.world_position - gl.world_position)
        local dr = vector.magnitude(Face.find_named(a.body, "Hand.R").world_position - gr.world_position)
        c.check("carry_ik", dl < 0.06 and dr < 0.06, string.format("left %.3f m right %.3f m", dl, dr))
    end },
    -- walk forward 6 s; the squad follows into formation
    { at = 1.1, move = V(0, 1, 0) },
    { at = 5.0, move = false },
    { at = 9.0, run = function(c)
        local worst, who = 0, ""
        Squad.each(function(k, m)
            local d = flat(m.entity.position, Squad.slot_point(k))
            if d > worst then worst, who = d, k end
        end)
        c.check("formation_follow", worst < 2.5, string.format("worst %s %.2f m from slot", who, worst))
        local fd = flat(Squad.member("Anchor").entity.position, Game.player.position)
        c.check("lead_close", fd < 4.5, string.format("anchor %.2f m", fd))
        -- hold order
        Squad.order("hold")
        c.data.hold = Squad.member("Echo").entity.position
    end },
    { at = 9.1, move = V(0, -1, 0) },
    { at = 11.5, move = false, run = function(c)
        local moved = flat(Squad.member("Echo").entity.position, c.data.hold)
        c.check("hold_order", moved < 0.6, string.format("echo moved %.2f m", moved))
        Squad.order("follow")
    end },
    { at = 16.0, run = function(c)
        local d = flat(Squad.member("Echo").entity.position, Squad.slot_point("Echo"))
        c.check("follow_resumed", d < 2.5, string.format("echo %.2f m from slot", d))
        -- dialogue: a squad conversation, then a bark that must wait its turn
        c.data.log0 = #Dialogue.state().log
        Dialogue.conversation({ "chat_01a", "chat_01b" }, { done = function() c.data.conv_done = true end })
        Dialogue.bark("follow", {})
    end },
    { at = 16.6, run = function(c)
        c.check("subtitle_shown", Game.subtitle ~= nil and Game.subtitle.speaker ~= nil,
                Game.subtitle and tostring(Game.subtitle.speaker) or "none")
        local cur = Dialogue.current()
        local spk = cur and Dialogue.actor(cur.line.s)
        local jaw = 0
        if spk and spk.face then jaw = spk.face.cur.JawOpen + spk.face.cur.MouthO end
        c.data.jaw = jaw
    end },
    { at = 16.9, run = function(c)
        local cur = Dialogue.current()
        local spk = cur and Dialogue.actor(cur.line.s)
        local jaw = 0
        if spk and spk.face then jaw = spk.face.cur.JawOpen + spk.face.cur.MouthO end
        c.check("lip_sync_moves", math.abs(jaw - (c.data.jaw or 0)) > 0.01 or jaw > 0.05,
                string.format("jaw %.2f -> %.2f", c.data.jaw or 0, jaw))
        -- a listener looks at the speaker
        local looking = 0
        Squad.each(function(k, m) if m.actor.look_t > 0 then looking += 1 end end)
        c.check("listeners_look", looking >= 2, "looking " .. looking)
    end },
    { at = 34.0, run = function(c)
        local log = Dialogue.state().log
        local overlap, n = false, 0
        for i = c.data.log0 + 1, #log do
            n += 1
            local prev = log[i - 1]
            if i > c.data.log0 + 1 and prev and prev.stop and log[i].start < prev.stop - 1e-3 then overlap = true end
        end
        c.check("no_overlap", not overlap and n >= 2, "lines " .. n)
        c.check("conversation_done", c.data.conv_done == true, "")
        local order_ok = log[c.data.log0 + 1] and log[c.data.log0 + 1].id == "chat_01a"
        c.check("priority_order", order_ok, log[c.data.log0 + 1] and log[c.data.log0 + 1].id or "none")
        -- repeating the same line inside its cooldown is refused
        c.check("cooldown", Dialogue.say("chat_01a", { priority = 1 }) == false, "")
    end },
}

-- The squad engages two alerted contractors; both end up stunned and surrendering.
P.squad_combat = {
    { at = 1.0, run = function(c)
        c.check("enemies_registered", #Squad.active_enemies() == 2, "enemies " .. #Squad.active_enemies())
        c.data.downs0 = Combat.stats.downs
    end },
    { at = 40.0, run = function(c)
        local down = Combat.stats.downs - c.data.downs0
        c.check("squad_stuns_enemies", down == 2, "downs " .. down)
        local surrender = 0
        for _, r in Squad.state().enemies do
            if r.ctl.down and r.ctl.actor.body then surrender += 1 end
        end
        c.check("surrender_state", surrender == 2, "surrendered " .. surrender)
        local contact = false
        for _, l in Dialogue.state().log do
            if string.find(l.id, "contact") then contact = true end
        end
        c.check("contact_bark", contact, "")
        c.check("player_alive", ps().health > 0, string.format("health %.0f", ps().health))
    end },
}

-- A lone contractor reacts to the player, fires, hurts them, and is stunned by the player's carbine.
P.enemy_fire = {
    { at = 0.5, run = function(c) c.data.h0 = ps().health end },
    { at = 0.4, press = "aim" },
    { at = 6.0, run = function(c)
        c.check("enemy_hurts_player", ps().health < c.data.h0, string.format("health %.0f", ps().health))
        Game.face_player(V(3, 1.25, -3))
        c.data.downs0 = Combat.stats.downs
    end },
    { at = 6.1, press = "fire" },
    { at = 9.0, release = "fire", run = function(c)
        c.check("player_stuns_enemy", Combat.stats.downs > c.data.downs0, "downs " .. (Combat.stats.downs - c.data.downs0))
        local h = ps().health
        c.data.h1 = h
    end },
    { at = 12.0, run = function(c)
        c.check("stunned_enemy_silent", ps().health >= c.data.h1, string.format("health %.0f", ps().health))
    end },
}

-- Screenshot setup: the squad faces the player.
P.squad_look = {
    { at = 0.05, run = function() Squad.order("hold"); Game.face_player(V(0, 1.6, 9.5)) end },
    { at = 0.3, run = function() Game.face_player(V(0, 1.6, 9.5)) end },
    { at = 0.8, run = function(c)
        Squad.each(function(k, m)
            local a = m.actor
            local f = a.carry.forward
            local mz = a:muzzle_ray()
            local cp = a.carry.world_position
            c.check("pose_" .. k, true, string.format("yaw %.1f carry fwd %.2f %.2f %.2f muzzle-carry %.2f %.2f %.2f",
                a.yaw, f.x, f.y, f.z, mz.x - cp.x, mz.y - cp.y, mz.z - cp.z))
        end)
    end },
    { at = 25 },
}

return P
