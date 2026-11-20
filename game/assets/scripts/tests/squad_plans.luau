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

-- Contractor tactics (lib/tactics.luau): two alerted contractors in the open take real cover
-- (the range's blocks), fight from it crouching between bursts, one flanks, and when the player
-- breaks line of sight they suppress the last known position and then sweep it. The player is
-- made unhittable here so the fight lasts.
P.enemy_tactics = {
    { at = 0.3, run = function(c)
        c.data.hurt = Game.hurt_player
        Game.hurt_player = function() return false end
        c.data.cover, c.data.flank, c.data.crouched, c.data.shots_after = {}, {}, {}, 0
        Game.on("enemy_in_cover", function(e, kind) table.insert(c.data.cover, { id = e.id, kind = kind, pos = e.position }) end)
        Game.on("enemy_flanking", function(e) table.insert(c.data.flank, { id = e.id, pos = e.position }) end)
        c.data.sweeps = 0
        Game.on("enemy_sweep", function(e, n) if n > 0 then c.data.sweeps += 1 end end)
        c.data.bounds, c.data.both_moving, c.data.sweep_cover = {}, 0, 0
        Game.on("enemy_bound", function(e, kind, i) table.insert(c.data.bounds, { kind = kind, dur = i.dur, cov = i.by ~= nil }) end)
        Game.on("enemy_sweep_cover", function() c.data.sweep_cover += 1 end)
        Combat.on_noise(function(pos, r, src)
            if c.data.hidden_t and src and src.valid and Squad.state().enemies[src.id] and r >= 20 then
                if time.now() - c.data.hidden_t < 3.0 then c.data.shots_after += 1 end
            end
        end)
        c.check("enemies_registered", #Squad.active_enemies() == 2, "enemies " .. #Squad.active_enemies())
        local Tactics = require("scripts/lib/tactics")
        -- a crouched chest behind the left block is covered from the player; one in the open is not
        local eye = Game.player.position + V(0, 1.55, 0)
        c.check("cover_geometry", (not Tactics.exposed(eye, V(-6, 0, -15.2), Game.player))
            and Tactics.exposed(eye, V(-7, 0, -9), Game.player), "")
    end },
    { at = 16.0, run = function(c)
        local covered = 0
        local seen = {}
        for _, ev in c.data.cover do
            if ev.kind == "cover" and not seen[ev.id] then seen[ev.id] = true; covered += 1 end
        end
        c.check("took_cover", covered >= 1, string.format("%d contractors reached cover (%d arrivals)", covered, #c.data.cover))
        -- sampled 10-20 s (the plan below): the moment of a snapshot shifts with any small change in the fight
        local why = {}
        for _, r in Squad.state().enemies do
            table.insert(why, string.format("[%s %s cover %s tac %s]", r.entity.name, tostring(r.ctl.state),
                tostring(r.ctl.in_cover ~= nil), tostring(r.ctl.tac_kind)))
        end
        c.check("cover_is_cover", (c.data.hidden_best or 0) >= 1, string.format(
            "%d holding positions hidden from the player (best sample 10-20 s; %d samples with one) %s",
            c.data.hidden_best or 0, c.data.hidden_samples or 0, table.concat(why, " ")))
        local nc = 0
        for _ in c.data.crouched do nc += 1 end
        c.check("ducks_in_cover", nc >= 1, string.format("%d crouched in cover", nc))
        c.check("one_flanks", #c.data.flank == 1, string.format("%d flank moves", #c.data.flank))
        local log = Dialogue.state().log
        local barks = {}
        for _, l in log do
            for _, k in { "cover", "flank", "contact" } do
                if string.find(l.id, "grey_" .. k) then barks[k] = true end
            end
        end
        -- bounding overwatch: short rushes, covered by a mate, one man up at a time
        local longest, covered_n, rushes = 0, 0, 0
        for _, b in c.data.bounds do
            if b.kind ~= "sidestep" then
                rushes += 1
                longest = math.max(longest, b.dur)
                if b.cov then covered_n += 1 end
            end
        end
        c.check("short_rushes", rushes >= 1 and longest <= 5.3, string.format("%d rushes, longest %.1f s", rushes, longest))
        c.check("rush_overwatched", covered_n >= 1, string.format("%d of %d rushes covered by a mate", covered_n, rushes))
        c.check("one_up_at_a_time", c.data.both_moving <= 2, string.format("%d samples with both rushing", c.data.both_moving))
        local pair = {}
        for _, l in log do
            for _, k in { "moving", "covering", "set" } do
                if string.find(l.id, "grey_" .. k .. "_") then pair[k] = true end
            end
        end
        c.check("bound_callouts", pair.moving and (pair.covering or pair.set),
            string.format("moving %s covering %s set %s", tostring(pair.moving), tostring(pair.covering), tostring(pair.set)))
        c.check("tactical_barks", barks.contact and (barks.cover or barks.flank),
            string.format("contact %s cover %s flank %s", tostring(barks.contact), tostring(barks.cover), tostring(barks.flank)))
        -- now break line of sight: behind the north wall
        Game.player.position = V(0, 0.05, -33)
        c.data.hidden_t = time.now()
    end },
    { at = 19.5, run = function(c)
        c.check("suppress_last_known", c.data.shots_after >= 1, string.format("%d shots at the last known position", c.data.shots_after))
        local searching = 0
        for _, r in Squad.state().enemies do
            if r.ctl.state == "alert" and r.ctl.noise_pos then searching += 1 end
        end
        c.check("lost_then_search", searching == 2, string.format("%d searching", searching))
        -- the walk round the range walls to the hiding place is long; check the sweep on a nearby
        -- noise instead: reaching the spot starts a multi-point sweep
        -- both search the same spot near the first one, so they can cover each other's moves
        c.data.sweeps = 0
        local spot
        for _, r in Squad.state().enemies do
            spot = spot or (r.entity.position + V(2.5, 0, 2.5))
            r.ctl:investigate(spot, 0)
        end
    end },
    { at = 34.0, run = function(c)
        c.check("search_sweep", c.data.sweeps >= 1, string.format("%d sweeps started", c.data.sweeps))
        local st = ""
        for _, r in Squad.state().enemies do
            st ..= string.format(" [%s sweep %s i %s at %.0f,%.0f]", r.ctl.state, tostring(r.ctl.sweep ~= nil), tostring(r.ctl.sweep_i), r.entity.position.x, r.entity.position.z)
        end
        c.check("search_in_pairs", c.data.sweep_cover >= 1, string.format("%d holds covering a searching mate%s", c.data.sweep_cover, st))
        Game.hurt_player = c.data.hurt
    end },
}

-- Noticing takes time: a contractor 18 m away does not see a crouched, still player with the light
-- off (at most a "huh"), but stands, light on, is recognised within seconds, after a suspicious
-- pause first. The player is unhittable.
P.stealth = {
    { at = 0.2, run = function(c)
        c.data.hurt = Game.hurt_player
        Game.hurt_player = function() return false end
        c.data.sus_t, c.data.max_aware = nil, 0
        Game.on("enemy_suspicious", function() c.data.sus_t = c.data.sus_t or time.now() end)
        c.check("setup", #Squad.active_enemies() == 1, "enemies " .. #Squad.active_enemies())
    end },
    { at = 0.3, press = "crouch" }, { at = 0.4, release = "crouch" },
    { at = 0.5, press = "light" }, { at = 0.6, release = "light" },
    { at = 6.5, run = function(c)
        local r = Squad.active_enemies()[1]
        local ctl = r and (r.ctl or r)
        local ps = Game.player_state
        c.check("hidden_low_dark", ctl and ctl.state ~= "engage" and ps.crouched and not ps.torch_on,
            string.format("state %s aware %.2f crouched %s torch %s", ctl and ctl.state or "?", ctl and ctl.aware or -1,
                tostring(ps.crouched), tostring(ps.torch_on)))
    end },
    { at = 6.6, press = "crouch" }, { at = 6.7, release = "crouch" },
    { at = 6.8, press = "light" }, { at = 6.9, release = "light" },
    { at = 7.0, run = function(c) c.data.stand_t = time.now() end },
    { at = 16.0, run = function(c)
        local r = Squad.active_enemies()[1]
        local ctl = r and (r.ctl or r)
        c.check("seen_standing_lit", ctl and ctl.state == "engage", string.format("state %s aware %.2f", ctl and ctl.state or "?", ctl and ctl.aware or -1))
        c.check("suspicious_first", c.data.sus_t ~= nil and c.data.engage_t ~= nil and c.data.sus_t <= c.data.engage_t
            and c.data.engage_t - c.data.stand_t > 0.8,
            string.format("stood %.1f suspicious %s engaged %s", c.data.stand_t or -1, tostring(c.data.sus_t), tostring(c.data.engage_t)))
        local huh = false
        for _, l in Dialogue.state().log do if string.find(l.id, "grey_huh_") then huh = true end end
        c.check("huh_bark", huh, "")
        Game.hurt_player = c.data.hurt
    end },
}
for i = 0, 70 do
    table.insert(P.stealth, { at = 0.5 + i * 0.2, run = function(c)
        local r = Squad.active_enemies()[1]
        local ctl = r and (r.ctl or r)
        if ctl and c.data.engage_t == nil and ctl.state == "engage" then c.data.engage_t = time.now() end
    end })
end
table.sort(P.stealth, function(a, b) return a.at < b.at end)

-- The squad in a firefight next to the player: operators find real cover (the crates) against the
-- contractor they fight, duck there, still put both contractors down, and someone warns when one
-- of them flanks. The player is unhittable and stands still.
P.squad_cover = {
    { at = 0.3, run = function(c)
        Game.on("npc_reload", function(i) if i.tactical then c.data.topoffs = (c.data.topoffs or 0) + 1 end end)
        c.data.hurt = Game.hurt_player
        Game.hurt_player = function() return false end
        c.data.covered, c.data.hidden, c.data.flanks = {}, 0, 0
        c.data.downs0 = Combat.stats.downs
        local Tactics = require("scripts/lib/tactics")
        Game.on("squad_in_cover", function(who)
            c.data.covered[who] = true
            local m = Squad.member(who)
            local t = m and m.last_target
            if t and t.valid and not Tactics.exposed(t.position + V(0, 1.55, 0), m.entity.position, m.entity) then
                c.data.hidden += 1
            end
        end)
        Game.on("enemy_flanking", function() c.data.flanks += 1 end)
        c.data.bounds, c.data.covered_bounds, c.data.both_up = 0, 0, 0
        Game.on("squad_bound", function(b)
            c.data.bounds += 1
            if b.by then c.data.covered_bounds += 1 end
        end)
        c.check("setup", Squad.count() == 4 and #Squad.active_enemies() == 2,
            string.format("squad %d enemies %d", Squad.count(), #Squad.active_enemies()))
    end },
    { at = 45.0, run = function(c)
        local n = 0
        for _ in c.data.covered do n += 1 end
        c.check("squad_takes_cover", n >= 2, string.format("%d operators reached cover", n))
        c.check("cover_hides_them", c.data.hidden >= 1, string.format("%d arrivals hidden from their target", c.data.hidden))
        c.data.down45 = Combat.stats.downs - c.data.downs0
        local warned = false
        for _, l in Dialogue.state().log do
            if string.find(l.id, "react_eflank") then warned = true end
        end
        c.check("flank_warning", c.data.flanks == 0 or warned,
            string.format("%d flanks, warned %s", c.data.flanks, tostring(warned)))
        Game.hurt_player = c.data.hurt
    end },
}

for i = 0, 20 do
    table.insert(P.enemy_tactics, { at = 10.05 + i * 0.5, run = function(c)
        local Tactics = require("scripts/lib/tactics")
        local eye = Game.player.position + V(0, 1.55, 0)
        local blocked = 0
        for _, r in Squad.state().enemies do
            if r.ctl.in_cover and not Tactics.exposed(eye, r.ctl.in_cover, r.entity) then blocked += 1 end
        end
        if blocked >= 1 then c.data.hidden_samples = (c.data.hidden_samples or 0) + 1 end
        c.data.hidden_best = math.max(c.data.hidden_best or 0, blocked)
    end })
end
-- stand still in the open and watch them for a while (sampled every 0.25 s)
for i = 0, 62 do
    table.insert(P.enemy_tactics, 2 + i, { at = 0.4 + i * 0.25, run = function(c)
        for _, r in Squad.state().enemies do
            if r.ctl.in_cover and r.ctl.crouching then c.data.crouched[r.entity.id] = true end
        end
        local up = 0
        for _, r in Squad.state().enemies do if r.ctl.tac_goal and r.ctl.tac_kind ~= "sidestep" then up += 1 end end
        if up >= 2 then c.data.both_moving += 1 end
    end })
end
table.sort(P.enemy_tactics, function(a, b) return a.at < b.at end)

for i = 0, 160 do
    table.insert(P.squad_cover, 2 + i, { at = 1 + i * 0.25, run = function(c)
        c.data.ducked = c.data.ducked or {}
        Squad.each(function(k, m) if m.in_cover and m.crouching then c.data.ducked[k] = true end end)
    end })
end
for i = 0, 170 do
    table.insert(P.squad_cover, { at = 1.1 + i * 0.25, run = function(c)
        local up = 0
        Squad.each(function(_, m) if m.cover_goal then up += 1 end end)
        if up >= 2 then c.data.both_up += 1 end
    end })
end
for i = 0, 226 do
    table.insert(P.squad_cover, { at = 1.15 + i * 0.25, run = function(c)
        Squad.each(function(_, m)
            local a = m.actor
            if a and a.carry and a.carry.valid and m.crouching and a.chest_dy < -0.25 and a.reload_w < 0.05 then
                -- height relative to where the standing pose would hold it (low ready 1.14 .. aim 1.42)
                local h = a.carry.world_position.y - m.entity.position.y - (1.14 + 0.28 * a.aim)
                c.data.kneel_carry = math.max(c.data.kneel_carry or -9, h)
                c.data.kneel_samples = (c.data.kneel_samples or 0) + 1
            end
            if a and a.face and a.face.active then
                c.data.brow_max = math.max(c.data.brow_max or 0, a.face.cur.BrowDown or 0)
                c.data.flinches = math.max(c.data.flinches or 0, a.face.flinches)
            end
            if a and a:reloading() and a.reload_w > 0.8 and a.carry and a.carry.valid then
                c.data.reload_seen = (c.data.reload_seen or 0) + 1
                if a.carry.rotation.z < -20 then c.data.reload_canted = true end
                if (a.hand_w or 1) < 0.2 then c.data.reload_hand_off = true end
            end
        end)
    end })
end
table.insert(P.squad_cover, { at = 45.1, run = function(c)
    local n = 0
    for _ in c.data.ducked or {} do n += 1 end
    c.check("ducks_in_cover", n >= 1, string.format("%d operators crouched in cover", n))
    local heard = { moving = false, covering = false }
    for _, l in Dialogue.state().log do
        if string.find(l.id, "bark_moving_") then heard.moving = true end
        if string.find(l.id, "bark_covering_") then heard.covering = true end
    end
    c.check("bounding_overwatch", c.data.bounds >= 2 and c.data.covered_bounds >= 1,
        string.format("%d moves, %d covered by a mate", c.data.bounds, c.data.covered_bounds))
    c.check("one_man_up", c.data.both_up <= 2, string.format("%d samples with two operators rushing", c.data.both_up))
    c.check("moving_covering_calls", heard.moving and heard.covering,
        string.format("moving %s covering %s", tostring(heard.moving), tostring(heard.covering)))
end })
table.sort(P.squad_cover, function(a, b) return a.at < b.at end)
table.insert(P.squad_cover, { at = 59.9, run = function(c)
    local reloads = 0
    local shots = {}
    Squad.each(function(k, m) if m.actor then reloads += m.actor.reloads end; table.insert(shots, tostring(k) .. "=" .. tostring(m.shots)) end)
    c.check("operators_change_cells", reloads >= 1 and (c.data.reload_seen or 0) >= 2
        and c.data.reload_canted == true and c.data.reload_hand_off == true,
        string.format("%d reloads (%d tactical), %d samples, canted %s, hand off %s, shots %s", reloads, c.data.topoffs or 0, c.data.reload_seen or 0,
                      tostring(c.data.reload_canted), tostring(c.data.reload_hand_off), table.concat(shots, " ")))
end })
table.insert(P.squad_cover, { at = 59.95, run = function(c)
    c.check("kneeling_rifle_low", (c.data.kneel_samples or 0) >= 3 and (c.data.kneel_carry or 9) < -0.15,
        string.format("%d kneeling samples, rifle at most %.2f m vs the standing pose", c.data.kneel_samples or 0, c.data.kneel_carry or 9))
    local called, answers = false, 0
    for _, l in Dialogue.state().log do
        if string.find(l.id, "con_call_") then called = true end
        if string.find(l.id, "con_up_") or string.find(l.id, "con_hurt_") then answers += 1 end
    end
    c.check("sound_off", called and answers >= 2, string.format("call %s, %d answers", tostring(called), answers))
    local kinds = {}
    for k, n in Squad.state().impact_surfaces or {} do table.insert(kinds, k .. "=" .. n) end
    table.sort(kinds)
    c.check("impact_surfaces", #kinds >= 1, table.concat(kinds, " "))
    c.check("npc_impacts", (Squad.state().npc_impacts or 0) >= 5,
        string.format("%d NPC shot impacts shown near the camera", Squad.state().npc_impacts or 0))
    c.check("faces_show_the_fight", (c.data.brow_max or 0) > 0.45 and (c.data.flinches or 0) >= 1,
        string.format("max brow-down %.2f, most flinches %d", c.data.brow_max or 0, c.data.flinches or 0))
end })
table.insert(P.squad_cover, { at = 60.0, run = function(c)
    local down = Combat.stats.downs - c.data.downs0
    c.check("still_wins", down == 2, string.format("downs %d (by 45 s: %d)", down, c.data.down45))
end })

-- Screenshot setup: the squad holds facing the player, frozen mid cell change (support hand off the gun).
-- Screenshot setup: the squad holds and takes a knee with the player (quiet move).
P.squad_kneel_look = {
    { at = 0.02, run = function() Squad.order("hold"); Game.face_player(V(0, 1.6, 9.5)) end },
    { at = 0.1, press = "crouch" },
    { at = 0.15, release = "crouch" },
    { at = 0.2, run = function() Game.face_player(V(0, 1.2, 9.5)) end },
    { at = 25 },
}

-- Screenshot setup: the player gets low and the squad walks toward him in the crouched gait.
P.squad_crouch_look = {
    { at = 0.02, run = function() Squad.order("hold"); Game.face_player(V(0, 1.2, 9.5)) end },
    { at = 0.05, press = "crouch" },
    { at = 0.1, release = "crouch" },
    { at = 0.15, run = function()
        Squad.order("move", { Anchor = V(2.3, 0, 8.0), Patch = V(5.6, 0, 8.6), Echo = V(1.0, 0, 9.6), Tally = V(6.6, 0, 10.4) })
    end },
    { at = 0.9, run = function(c)
        local low, n = 0, 0
        Squad.each(function(_, m)
            n += 1
            if m.actor.body and m.actor.body:anim_state() == "Crouch" then low += 1 end
        end)
        c.check("moves_low", low >= 3, string.format("%d of %d operators in the crouched gait", low, n))
    end },
    { at = 5.0, run = function(c)
        local knelt = 0
        Squad.each(function(_, m) if m.actor.body and m.actor.body:anim_state() == "Kneel" then knelt += 1 end end)
        c.check("kneels_on_arrival", knelt >= 3, string.format("%d kneeling", knelt))
    end },
    { at = 25 },
}

-- Screenshot setup: faces under fire (strain blended in, one fresh startle).
P.squad_face_look = {
    { at = 0.02, run = function()
        Squad.order("hold"); Game.face_player(V(0, 1.6, 9.5))
        Squad.each(function(_, m) m.actor.under_fire = 99; m.actor.stress = 1 end)
    end },
    { at = 0.5, run = function() Squad.each(function(k, m) if k == "Patch" then m.actor:startle(1) end end) end },
    { at = 25 },
}

P.squad_reload_look = {
    { at = 0.02, run = function()
        Squad.order("hold"); Game.face_player(V(0, 1.6, 9.5))
        Squad.each(function(_, m)
            m.actor:reload(100, {})
            m.actor.reload_t = 60; m.actor.reload_w = 1; m.actor.hand_w = 0
        end)
    end },
    { at = 25 },
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

-- Idle chatter (lib/chatter.luau): only on quiet walk stages, only while moving, never repeats,
-- outdoor-only lines are skipped indoors, and it stays silent with an awake contractor nearby.
P.chatter = {
    { at = 0.5, run = function(c)
        local Chatter = require("scripts/lib/chatter")
        c.data.C = Chatter
        Game.chatter_used = {}
        Chatter.gap = 1.0
        Chatter.reset()
        c.data.started = {}
        Game.on("squad_chatter", function(i) table.insert(c.data.started, i) end)
    end },
}
-- drive the player forward and tick Chatter from the plan (no mission script in this scene)
for k = 0, 250 do
    local t = 0.6 + k * 0.1
    table.insert(P.chatter, { at = t, run = function(c)
        local C = c.data.C
        local stage = t < 4 and "ambush" or "trail"
        local outdoors = t >= 9
        -- pace back and forth on open ground (1 m/s)
        if Game.player then Game.player.position = Game.player.position + V(0, 0, (k % 60 < 30) and -0.1 or 0.1) end
        C.update(0.1, stage, outdoors, false)
    end })
end
table.insert(P.chatter, { at = 3.9, run = function(c)
    c.check("silent_off_walk_stages", #c.data.started == 0, tostring(#c.data.started))
end })
table.insert(P.chatter, { at = 8.9, run = function(c)
    local first = c.data.started[1]
    c.check("starts_on_walk", first ~= nil, tostring(first))
    c.check("indoor_skips_outdoor_lines", first ~= nil and not c.data.C.GROUPS[first].outdoor, tostring(first))
    c.check("lines_queued", Dialogue.busy(), "dialogue busy")
end })
table.insert(P.chatter, { at = 26.5, run = function(c)
    local seen, dup = {}, false
    for _, i in c.data.started do if seen[i] then dup = true end; seen[i] = true end
    c.check("no_repeats", not dup and #c.data.started >= 2, table.concat(c.data.started, ","))
end })
table.sort(P.chatter, function(a, b) return a.at < b.at end)

-- Squad reactions (lib/reactions.luau): muzzle on a teammate, friendly fire, staring up close,
-- jumping about and firing at nothing each get the right person talking, once.
local function look_at_point(pt)
    local s = ps()
    local o = s:aim_ray()
    local d = pt - o
    s.yaw = math.deg(math.atan2(-d.x, -d.z))
    s.pitch = math.deg(math.atan2(d.y, math.sqrt(d.x * d.x + d.z * d.z)))
end
P.reactions = {
    { at = 0.5, run = function(c)
        c.data.said, c.data.lines = {}, {}
        Game.on("squad_reaction", function(kind, who) table.insert(c.data.said, kind .. ":" .. tostring(who)) end)
        Game.on("dialogue_line", function(id, spk) table.insert(c.data.lines, id .. ":" .. spk) end)
        c.check("squad_registered", Squad.count() == 5, "members " .. Squad.count())
        c.check("awareness_quiet", Game.awareness == nil and (Game.awareness_level or 0) == 0, tostring(Game.awareness))
        Game.player.position = V(0, 0.05, -2)
    end },
}
local function has(list, s) for _, v in list do if v == s then return true end end return false end
-- hold the muzzle on Anchor's chest for ~2.5 s (hip aim counts slower than down sights)
for k = 0, 50 do
    table.insert(P.reactions, { at = 1.0 + k * 0.05, run = function()
        local m = Squad.member("Anchor")
        look_at_point(m.entity.world_position + V(0, 1.25, 0))
    end })
end
table.insert(P.reactions, { at = 4.0, run = function(c)
    c.check("aimed_anchor", has(c.data.said, "aimed:anchor"), table.concat(c.data.said, ","))
    local ok = false
    for _, l in c.data.lines do if l:find("^react_aimed_") and l:find(":anchor$") then ok = true end end
    c.check("aimed_line_played", ok, table.concat(c.data.lines, ","))
    -- friendly fire on Patch through the real combat handler
    local m = Squad.member("Patch")
    local h = Combat.handler_of(m.entity)
    c.check("patch_has_handler", h ~= nil, "")
    if h then h.fn({ amount = 2, point = m.entity.world_position, source = Game.player, zone = "body" }) end
    ps().pitch = -30
end })
table.insert(P.reactions, { at = 7.0, run = function(c)
    c.check("ff_patch", has(c.data.said, "ff:patch"), table.concat(c.data.said, ","))
    -- stand close to Echo and look at her face
    local e = Squad.member("Echo").entity
    Game.player.position = e.world_position + V(0, 0, -2.2)
end })
for k = 0, 80 do
    table.insert(P.reactions, { at = 7.2 + k * 0.05, run = function()
        local e = Squad.member("Echo").entity
        look_at_point(e.world_position + V(0, 1.62, 0))
    end })
end
table.insert(P.reactions, { at = 12.0, run = function(c)
    c.check("stare_echo", has(c.data.said, "stare:echo"), table.concat(c.data.said, ","))
    ps().pitch = -30
    for _ = 1, 4 do Game.emit("player_jumped") end
end })
table.insert(P.reactions, { at = 15.0, run = function(c)
    c.check("jump_remark", has(c.data.said, "jump:nil"), table.concat(c.data.said, ","))
    for _ = 1, 10 do Game.emit("player_fired", "carbine") end
end })
table.insert(P.reactions, { at = 18.0, run = function(c)
    c.check("waste_remark", has(c.data.said, "waste:nil"), table.concat(c.data.said, ","))
    local n = 0
    for _, v in c.data.said do if v == "aimed:anchor" then n += 1 end end
    c.check("no_repeat_spam", n == 1, tostring(n))
end })
table.insert(P.reactions, { at = 19 })

-- Screenshot setup for HUD v2: objective, waypoint on the compass, squad roster, a searching
-- contractor (awareness), a hit from the right (wedge + vignette + health trail), a takedown feed
-- line and a subtitle.
P.hud_look = {
    { at = 0.05, run = function()
        Game.set_objective("Reach the ranger station past the old fence line", "OPERATION 01  ·  GREENLINE")
        Game.waypoint = { pos = V(18, 0, -40), label = "RANGER STATION" }
        Game.face_player(V(-6, 1.4, -20))
        local e = scene.find("Greyline 1")
        Game.hurt_player(38, e)
        Game.emit("hit_confirm", "head")
        Game.emit("enemy_down", e, Game.player)
        Game.show_subtitle("Anchor", "Contact east. Rook, get low and stay on me.", 60)
    end },
    { at = 0.3, run = function(c)
        c.check("hud_look_ready", Game.awareness ~= nil, tostring(Game.awareness))
    end },
}
-- keep the hit feedback fresh for the capture without changing health further
for k = 1, 110 do
    table.insert(P.hud_look, { at = 0.05 + k * 0.25, run = function()
        Game.emit("player_hurt", 4, scene.find("Greyline 1"))
        if k % 2 == 0 then Game.emit("hit_confirm", "head") end
    end })
end
table.insert(P.hud_look, { at = 29 })

return P
