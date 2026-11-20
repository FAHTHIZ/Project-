-- Kestrel Station interiors mission director: Operation 04 (records and labs), Operation 05 (the
-- bunker), Operation 06 (the Source Vault) and Operation 07 (the review chamber). One scene per
-- chapter (tools/levels/build_facility.py); this script's `chapter` says which one.
--
-- Same shape as scripts/missions/kestrel.luau: a list of stages, each with enter/update; update
-- returns the next stage's name. Stages marked `checkpoint` save the player, inventory, downed
-- contractors and story flags; restarting resumes there. Story canon: docs/CAMPAIGN_STORY_BIBLE.md
-- (revision 2: storm night, transfer convoy at 06:00, Brick stays with Venn, Sorn stands down).
--
-- Script properties:
--   chapter   op04 | op05 | op06 | op07
local Game = require("scripts/lib/game")
local Campaign = require("scripts/lib/campaign")
local Dialogue = require("scripts/lib/dialogue")
local Squad = require("scripts/lib/squad")
local Inventory = require("scripts/lib/inventory")
local Chatter = require("scripts/lib/chatter")

local M = {}
M.chapter = "op04"

local V = vector.create

local function flat(a, b)
    local d = a - b
    return math.sqrt(d.x * d.x + d.z * d.z)
end
local function ppos() return Game.player and Game.player.position or V(0, 0, 0) end
local function near(p, r) return flat(ppos(), p) < r end
-- saved data: VICTUS turns three-number arrays back into vectors when a save is read
local function vec(t) if type(t) == "vector" then return t end return V(t[1], t[2], t[3]) end
local function tab(v) return { v.x, v.y, v.z } end
local function mark(name) return scene.find(name) end
local function mpos(name, fallback)
    local e = scene.find(name)
    return e and e.position or fallback or V(0, 0, 0)
end
local function sfx(clip, pos, vol)
    audio.play(clip, { bus = "sfx", volume = vol or 0.9, position = pos })
end
local function door(id) return Game.doors and Game.doors[id] end

-- Contractors in a named group (enemy.luau `group`).
local function group(name)
    local out = {}
    for _, r in Squad.state().enemies do
        if r.entity.valid and r.ctl and r.ctl.group == name then table.insert(out, r.ctl) end
    end
    return out
end
local function group_up(name)
    local n = 0
    for _, e in group(name) do if not e.down and not e.dormant and not e.gone then n += 1 end end
    return n
end
-- Enemies downed before the last checkpoint are removed on restore; M.cleared keeps their count
-- per group so a resumed "Clear the labs" reads 3/5 instead of 0/2 (or 0/0 with the room clear).
local cleared = {}
local function group_total(name) return #group(name) + (cleared[name] or 0) end
local function enemy(name)
    for _, r in Squad.state().enemies do
        if r.entity.valid and r.entity.name == name then return r.ctl end
    end
    return nil
end

-- Player inside an axis-aligned room rectangle (x0, z0, x1, z1).
local function in_rect(x0, z0, x1, z1)
    local p = ppos()
    return p.x > x0 and p.x < x1 and p.z > z0 and p.z < z1
end

local S = {}

-- Shared helpers --------------------------------------------------------------------------------
function M:say(ids, done)
    if type(ids) == "string" then ids = { ids } end
    self.talking = true
    Dialogue.conversation(ids, { done = function()
        self.talking = false
        if done then done() end
    end })
end

function M:objective(text, wp, label)
    Game.set_objective(text, self.op_title)
    if wp then Game.waypoint = { pos = wp, label = label or "" } else Game.waypoint = nil end
end

function M:title(chapter_id)
    local c = Campaign.get(chapter_id)
    if not c then return end
    self.op_title = c.title
    Game.present.title = c.title
    Game.present.subtitle_title = c.subtitle
    self.title_t = 5.0
end

-- Registers a one-shot interaction on a mark. `fn` runs once; the prompt disappears after.
function M:interact(name, prompt, flag, fn, guard)
    local m = mark(name)
    if not m then
        self.flags[flag] = true
        return
    end
    if self.flags[flag] then Game.set_interactable(m, false); return end
    Game.register_interactable(m, prompt, function()
        if self.flags[flag] or self.talking then return end
        if guard and not guard() then return end
        self.flags[flag] = true
        Game.set_interactable(m, false)
        fn(m)
    end)
end

-- Unlocks a door and remembers it for checkpoint restores.
function M:unlock(id)
    local d = door(id)
    if d then d:unlock() end
    self.flags.doors = self.flags.doors or {}
    self.flags.doors[id] = true
end

function M:fade_out_then(fn)
    self.fade_t = 0
    self.fade_fn = fn
end

function M:place_player(pos, yaw)
    local ps = Game.player_state
    Game.player.position = pos + V(0, 0.1, 0)
    if ps then
        ps.yaw = yaw
        ps.pitch = 0
        ps.vel = V(0, 0, 0)
    end
end

function M:place_squad(at, yaw)
    local r = math.rad(yaw or 0)
    local fwd = V(-math.sin(r), 0, -math.cos(r))
    local right = V(math.cos(r), 0, -math.sin(r))
    local offs = { Anchor = { -1.2, -1.4 }, Patch = { 1.2, -1.8 }, Echo = { -0.4, -2.8 }, Tally = { 1.4, -3.2 },
                   Brick = { -0.2, -4.2 } }
    Squad.each(function(who, op)
        if self.flags.brick_stays and who == "Brick" then return end
        local o = offs[who] or { 0, -2 }
        local p = at + right * o[1] + fwd * o[2]
        op:place(V(p.x, at.y + 0.3, p.z), yaw)
    end)
end

function M:checkpoint(stage)
    local p = Game.progress()
    local downed = {}
    for _, r in Squad.state().enemies do
        if r.entity.valid and r.ctl and (r.ctl.down or r.ctl.gone) then table.insert(downed, r.entity.name) end
    end
    local ps = Game.player_state
    p.checkpoint = { op = self.chapter, stage = stage, pos = tab(ppos()), yaw = ps and ps.yaw or 0,
                     inv = Inventory.serialize(), downed = downed, flags = self.flags }
    Game.save_progress()
    Game.toast("Checkpoint", 2.0)
end

-- Wakes a dormant group at its authored spots under parley (nobody fires while they talk).
function M:arrive(name)
    for _, e in group(name) do
        if e.dormant then e:wake() end
        e.parley = true
    end
end

function M:break_parley(name, at)
    for _, e in group(name) do
        if not e.down then
            e.parley = false
            e:investigate(at or ppos(), 0.2)
        end
    end
end

-- Operation 04: The Paper War ------------------------------------------------------------------
S.op04_start = {
    enter = function(self)
        self:title("op04")
        self.wait = 1.2
        sfx("audio/scare/pa_chime_cut.wav", V(0, 2.6, 24), 0.8)
    end,
    update = function(self, dt)
        self.wait -= dt
        if self.wait > 0 then return nil end
        return "reception"
    end,
}

S.reception = {
    checkpoint = true,
    enter = function(self)
        local f = self.flags
        if not f.op4_intro then
            f.op4_intro = true
            self:say({ "op4_01", "op4_02", "op4_03", "op4_04", "op4_05", "op4_06" })
        end
        self:objective("Search the records office", mpos("Mark Records"), "RECORDS")
        self:interact("Mark Visitor Log", "Read the visitor log", "visitor_log", function(m)
            sfx("audio/foley/item_pick.wav", m.position, 0.7)
            Game.toast("Visitor log, tonight: six Greyline names. Last entry 04:02. No staff.", 5.0)
        end)
        self:interact("Mark Records", "Read the incident summaries", "records", function(m)
            sfx("audio/foley/pickup.wav", m.position, 0.8)
            self:say({ "op4_rec_01", "op4_rec_02", "op4_rec_03", "op4_rec_04",
                       "op4_rec_05", "op4_rec_06", "op4_rec_07", "op4_rec_08" })
        end)
        self:interact("Mark Venn Recorder", "Play the recorder", "venn_rec", function(m)
            sfx("audio/foley/item_pick.wav", m.position, 0.7)
            self:say({ "op4_venn_01", "op4_venn_02", "op4_venn_03" })
        end)
    end,
    update = function(self, dt)
        local f = self.flags
        if f.records and not f.rec_hint and not self.talking then
            f.rec_hint = true
            if not f.venn_rec then
                self:objective("Check the recorder on the office desk", mpos("Mark Venn Recorder"), "RECORDER")
            end
        end
        if f.records and f.venn_rec and not self.talking then return "breakers" end
        return nil
    end,
}

S.breakers = {
    checkpoint = true,
    enter = function(self)
        self:objective("Restore power in the switch room", mpos("Mark Breakers"), "SWITCH ROOM")
        self:interact("Mark Breakers", "Reset the breakers", "breakers", function(m)
            sfx("audio/foley/breaker.wav", m.position, 1.0)
            self.power_t = 0
        end)
    end,
    update = function(self, dt)
        local f = self.flags
        -- Corridor B: the ventilation fan clears its throat
        if not f.fan and in_rect(-24, -6, 24, -2) and not self.talking then
            f.fan = true
            sfx("audio/scare/vent_growl.wav", mpos("Fan Point"), 1.0)
            self.fan_t = 0
        end
        if self.fan_t then
            self.fan_t += dt
            if self.fan_t > 1.1 then
                self.fan_t = nil
                Squad.order("hold")
                self:say({ "op4_fan_01", "op4_fan_02", "op4_fan_03", "op4_fan_04" }, function() Squad.order("follow") end)
            end
        end
        if self.power_t then
            self.power_t += dt
            if self.power_t > 0.6 and not f.power then
                f.power = true
                self:unlock("corB_labW")
                self:unlock("corB_labE")
                self:unlock("corB_corC")
                Dialogue.clear(1)
                self:say({ "op4_07", "op4_08", "op4_sorn_01", "op4_recall_01", "op4_recall_02", "op4_recall_03" })
            end
            if f.power and not self.talking then return "labs" end
        end
        return nil
    end,
}

S.labs = {
    checkpoint = true,
    enter = function(self)
        self.n = group_total("labs")
        self:say({ "op4_09", "op4_10" })
        self:objective(string.format("Clear the labs (0/%d)", self.n), V(0, 0, -10), "LABS")
        for _, e in group("labs") do e:investigate(V(0, 0, -4), 1.0 + math.random()) end
        self.last = -1
    end,
    update = function(self, dt)
        local left = group_up("labs")
        if left ~= self.last then
            self.last = left
            Game.objective.text = string.format("Clear the labs (%d/%d)", self.n - left, self.n)
        end
        if left == 0 and not self.talking then return "lift" end
        return nil
    end,
}

S.lift = {
    checkpoint = true,
    enter = function(self)
        self:objective("Take the lift down", mpos("Mark Lift"), "LIFT")
        self:interact("Mark Lift", "Call the lift", "lift", function(m)
            local b = Squad.member("Brick")
            if b then b:set_order("move", m.position + V(-1.0, 0, 0.8)) end
            self:say({ "op4_lift_01", "op4_lift_02", "op4_11" }, function()
                sfx("audio/foley/lift_motor.wav", m.position, 0.9)
                self:fade_out_then(function() Campaign.complete("op04") end)
            end)
        end, function()
            if group_up("lift") > 0 then
                Game.toast("Clear the lift lobby first", 2.0)
                return false
            end
            return true
        end)
    end,
    update = function(self, dt) return nil end,
}

-- Operation 05: Below the Line -----------------------------------------------------------------
S.op05_start = {
    enter = function(self)
        self:title("op05")
        sfx("audio/foley/lift_motor.wav", V(0, 1.5, 34), 0.7)
        self:say({ "op5_01", "op5_02" })
        self.wait = 2.0
    end,
    update = function(self, dt)
        self.wait -= dt
        return (self.wait <= 0 and not self.talking) and "blast" or nil
    end,
}

S.blast = {
    checkpoint = true,
    enter = function(self)
        local f = self.flags
        self:objective("Work the blast-door crank", mpos("Mark Crank"), "CRANK")
        if not f.blast_talk then
            f.blast_talk = true
            self:say({ "op5_03", "op5_04" })
        end
        self:interact("Mark Crank", "Work the crank", "crank", function(m)
            local b = Squad.member("Brick")
            if b then b:set_order("move", m.position + V(-1.2, 0, 0.4)) end
            sfx("audio/foley/crank.wav", m.position, 0.9)
            self.crank_t = 0
            local d = door("blast")
            if d then d:open(1 / 7) end
            self:say("op5_crank_01")
        end)
    end,
    update = function(self, dt)
        local f = self.flags
        if not self.crank_t then return nil end
        self.crank_t += dt
        if self.crank_t > 3.5 and not f.groan then
            f.groan = true
            sfx("audio/scare/pressure_groan.wav", V(0, 2.0, 14), 1.0)
            Squad.order("hold")
            Dialogue.clear(1)
            self:say({ "op5_door_01", "op5_door_02", "op5_door_03", "op5_door_04" }, function() Squad.order("follow") end)
        end
        local d = door("blast")
        if (not d or d:amount() > 0.95) and f.groan and not self.talking then
            f.blast_open = true
            self:say({ "op5_05", "op5_06" })
            return "hall"
        end
        return nil
    end,
}

S.hall = {
    enter = function(self)
        self.n = group_total("hall")
        self:objective(string.format("Clear the holding wing (0/%d)", self.n), V(0, 0, 0), "HOLDING WING")
        self.last = -1
    end,
    update = function(self, dt)
        local left = group_up("hall")
        if left ~= self.last then
            self.last = left
            Game.objective.text = string.format("Clear the holding wing (%d/%d)", self.n - left, self.n)
        end
        if left == 0 and not self.talking then
            self.quiet_t = (self.quiet_t or 0) + dt
            if self.quiet_t > 2.0 then return "pipes" end
        end
        return nil
    end,
}

S.pipes = {
    enter = function(self)
        sfx("audio/scare/pipe_knock.wav", mpos("Pipe Point"), 1.0)
        self.wait = 0.9
    end,
    update = function(self, dt)
        self.wait -= dt
        if self.wait <= 0 and not self.said then
            self.said = true
            self:say({ "op5_pipe_01", "op5_pipe_02", "op5_pipe_03" })
        end
        if self.said and not self.talking then return "venn" end
        return nil
    end,
}

S.venn = {
    checkpoint = true,
    enter = function(self)
        local venn = Game.npcs and Game.npcs["Venn"]
        self:objective("Find Major Venn", venn and venn.entity.position or V(-26, 0, 2), "VENN")
        if venn then
            self:interact_entity(venn.entity, "Talk to Venn", "venn_talk", function()
                local p = Squad.member("Patch")
                if p then p:set_order("move", venn.entity.position + V(1.2, 0, 0.6)) end
                self:say({ "op5_venn_01", "op5_venn_02", "op5_venn_03", "op5_venn_04", "op5_venn_05", "op5_venn_06",
                           "op5_venn_06b", "op5_venn_06c", "op5_venn_07", "op5_venn_08", "op5_venn_09",
                           "op5_venn_09b", "op5_venn_09c", "op5_venn_09d", "op5_venn_10" }, function()
                    self.flags.venn_done = true
                end)
            end)
        else
            self.flags.venn_done = true
        end
    end,
    update = function(self, dt)
        if self.flags.venn_done and not self.talking then return "escort" end
        return nil
    end,
}

-- Venn limps to the stores comms room with Brick; Patch walks with them and the player covers.
S.escort = {
    enter = function(self)
        local f = self.flags
        local post = mpos("Venn Post", V(24, 0, -2))
        local venn = Game.npcs and Game.npcs["Venn"]
        f.brick_stays = true
        self:objective("See Venn to the stores comms room", post, "STORES")
        if venn then
            venn:walk({ V(-16, 0.05, 0), V(0, 0.05, -2), V(14, 0.05, -2), post }, function() f.venn_post = true end)
        else
            f.venn_post = true
        end
        local b = Squad.member("Brick")
        if b then b:set_order("move", post + V(1.4, 0, 1.2)); b.pinned = true end
        self.t = 0
    end,
    update = function(self, dt)
        local f = self.flags
        self.t += dt
        if self.t > 4 and not f.snd then
            f.snd = true
            self:say({ "op5_snd_01", "op5_snd_02", "op5_snd_03" })
        end
        if (f.venn_post or self.t > 40) and not self.talking then
            local p = Squad.member("Patch")
            if p then p:set_order("follow") end
            self:unlock("hall_stairs")
            self:say("op5_07")
            return "stairs"
        end
        return nil
    end,
}

S.stairs = {
    checkpoint = true,
    enter = function(self)
        self:objective("Take the stairwell down to the Source Vault", mpos("Mark Stairs"), "STAIRS")
        self:interact("Mark Stairs", "Go down", "stairs", function()
            self:say("op5_08", function()
                self:fade_out_then(function() Campaign.complete("op05") end)
            end)
        end)
    end,
    update = function(self, dt) return nil end,
}

-- Operation 06: The Source Vault ---------------------------------------------------------------
S.op06_start = {
    enter = function(self)
        self:title("op06")
        self:say({ "op6_01", "op6_02", "op6_03" })
    end,
    update = function(self, dt) return not self.talking and "archive" or nil end,
}

-- One environmental false alarm: a sound at `point`, a beat of silence, the squad stops and talks.
function M:scare(flag, point, radius, clip, ids)
    local f = self.flags
    if f[flag] or self.talking or not near(point, radius) then return end
    f[flag] = true
    sfx(clip, point, 1.0)
    self.scare_q = { t = 1.0, ids = ids }
end

function M:update_scare(dt)
    local q = self.scare_q
    if not q then return end
    q.t -= dt
    if q.t > 0 then return end
    self.scare_q = nil
    Squad.order("hold")
    self:say(q.ids, function() Squad.order("follow") end)
end

S.archive = {
    checkpoint = true,
    enter = function(self)
        self:objective("Find the vault code in the pump room", mpos("Mark Plaque"), "PUMP ROOM")
        self:interact("Mark Plaque", "Read the commissioning plaque", "plaque", function(m)
            sfx("audio/foley/item_pick.wav", m.position, 0.6)
            self:say("op6_plaque_01")
        end)
    end,
    update = function(self, dt)
        self:scare("fan6", mpos("Fan Point"), 12, "audio/scare/fan_breath.wav",
                   { "op6_fan_01", "op6_fan_02", "op6_fan_03", "op6_fan_04", "op6_fan_05" })
        self:scare("tag6", mpos("Tag Point"), 9, "audio/scare/tag_tap.wav", { "op6_tag_01", "op6_tag_02", "op6_tag_03" })
        self:scare("spk6", mpos("Speaker Point"), 10, "audio/scare/speaker_fragment.wav",
                   { "op6_spk_01", "op6_spk_02", "op6_spk_03" })
        if self.flags.plaque and not self.talking then return "vault" end
        return nil
    end,
}

S.vault = {
    checkpoint = true,
    enter = function(self)
        self:objective("Open the Source Vault", mpos("Mark Vault Keypad"), "SOURCE VAULT")
        self:interact("Mark Vault Keypad", "Enter the code 0311", "keypad", function(m)
            sfx("audio/foley/panel_keys.wav", m.position, 0.8)
            self:unlock("arch_mgr")
            sfx("audio/foley/card_accept.wav", m.position, 0.8)
        end)
        self:interact("Mark Evidence", "Bag the original records", "evidence", function(m)
            sfx("audio/foley/pickup.wav", m.position, 0.9)
            self:say({ "op6_vault_01", "op6_vault_02", "op6_vault_03", "op6_vault_04", "op6_vault_05",
                       "op6_vault_06", "op6_vault_07" })
        end, function() return self.flags.keypad == true end)
    end,
    update = function(self, dt)
        local f = self.flags
        if f.keypad and not f.ev_hint then
            f.ev_hint = true
            self:objective("Recover the original records", mpos("Mark Evidence"), "ORIGINALS")
        end
        if f.evidence and not self.talking then return "sorn6" end
        return nil
    end,
}

S.sorn6 = {
    enter = function(self)
        self:arrive("sorn")
        self:objective("Captain Sorn", nil)
        self:say({ "op6_sorn_01", "op6_sorn_02", "op6_sorn_03" }, function()
            self:break_parley("sorn")
            self.fight = true
        end)
        self.n = group_total("sorn")
        Game.on("parley_broken", function()
            if self.stage_name == "sorn6" and not self.fight then
                Dialogue.clear(1)
                self.fight = true
                self:break_parley("sorn")
                self.talking = false
            end
        end)
    end,
    update = function(self, dt)
        if not self.fight then return nil end
        if not self.obj then
            self.obj = true
            self:objective("Hold the vault against Sorn's team", nil)
        end
        local sorn = enemy("Sorn")
        local escorts_up = 0
        for _, e in group("sorn") do
            if e.entity.name ~= "Sorn" and not e.down then escorts_up += 1 end
        end
        local hurt = sorn and (sorn.pool < sorn.stun * 0.55)
        if sorn and not sorn.down and not sorn.retreating and (hurt or escorts_up == 0) then
            -- Sorn will not be taken here: he falls back toward the chamber
            sorn:retreat({ V(30, 0.05, 16), V(18, 0.05, 2), V(0, 0.05, -6), V(0, 0.05, -22) })
            self:say("op6_sorn_04")
        end
        if escorts_up == 0 and (not sorn or sorn.down or sorn.retreating) and not self.talking then
            return "north"
        end
        return nil
    end,
}

S.north = {
    checkpoint = true,
    enter = function(self)
        local f = self.flags
        f.sorn_gone = true
        local sorn = enemy("Sorn")
        if sorn and not sorn.down then
            sorn.gone = true
            sorn.entity.position = V(0, -400, 0)
            sorn.entity:set("Perceptible", { enabled = false })
        end
        self:unlock("north_ante")
        if not f.north_talk then
            f.north_talk = true
            self:say({ "op6_07", "op6_08" })
        end
        self.n = group_total("last")
        self:objective(string.format("Clear the chamber antechamber (0/%d)", self.n), V(0, 0, -36), "ANTECHAMBER")
        self.last = -1
    end,
    update = function(self, dt)
        local left = group_up("last")
        if left ~= self.last then
            self.last = left
            Game.objective.text = string.format("Clear the chamber antechamber (%d/%d)", self.n - left, self.n)
        end
        if left == 0 and not self.talking then
            self:say({ "op6_end_01", "op6_end_02", "op6_end_03", "op6_end_04" })
            return "chamber_door"
        end
        return nil
    end,
}

S.chamber_door = {
    checkpoint = true,
    enter = function(self)
        self:objective("Open the review chamber", mpos("Mark Chamber Door"), "CHAMBER")
        self:interact("Mark Chamber Door", "Open the chamber doors", "chamber", function(m)
            sfx("audio/foley/door_slide.wav", m.position, 0.9)
            self:fade_out_then(function() Campaign.complete("op06") end)
        end)
    end,
    update = function(self, dt) return nil end,
}

-- Operation 07: V-01 -------------------------------------------------------------------------------
S.op07_start = {
    enter = function(self)
        self:title("op07")
        -- the quietest room in the campaign: a few seconds of nothing before anyone speaks
        if Game.music_mute then Game.music_mute(true) end
        self.wait = 3.0
    end,
    update = function(self, dt)
        self.wait -= dt
        return self.wait <= 0 and "reveal" or nil
    end,
}

S.reveal = {
    checkpoint = true,
    enter = function(self)
        self:objective("Search the review chamber", V(0, 0, -2), "")
    end,
    update = function(self, dt)
        if near(V(0, 0, -4), 7) and not self.talking and not self.flags.v01 then
            self.flags.v01 = true
            Squad.order("hold")
            self:say({ "op7_01", "op7_02", "op7_03", "op7_04", "op7_05", "op7_06", "op7_07", "op7_08", "op7_09" },
                     function() Squad.order("follow") end)
        end
        if self.flags.v01 and not self.talking then return "terminal" end
        return nil
    end,
}

S.terminal = {
    checkpoint = true,
    enter = function(self)
        self:objective("Play the review record", mpos("Mark Review Terminal"), "TERMINAL")
        self:interact("Mark Review Terminal", "Play the review record", "terminal", function(m)
            sfx("audio/foley/panel_keys.wav", m.position, 0.7)
            self:say({ "op7_kade_01", "op7_kade_02", "op7_10" })
        end)
    end,
    update = function(self, dt)
        if self.flags.terminal and not self.talking then return "sorn7" end
        return nil
    end,
}

S.sorn7 = {
    enter = function(self)
        if Game.music_mute then Game.music_mute(false) end
        self:arrive("sorn")
        self:objective("Captain Sorn", nil)
        self:say({ "op7_sorn_01", "op7_sorn_02", "op7_sorn_03" }, function()
            self:break_parley("sorn")
            self.fight = true
        end)
        Game.on("parley_broken", function()
            if self.stage_name == "sorn7" and not self.fight then
                Dialogue.clear(1)
                self.fight = true
                self:break_parley("sorn")
                self.talking = false
            end
        end)
    end,
    update = function(self, dt)
        if not self.fight then return nil end
        if not self.obj then
            self.obj = true
            self:objective("Stop Sorn without hurting him", nil)
        end
        local sorn = enemy("Sorn")
        if not sorn then return "transmit" end
        if not sorn.down and sorn.pool < sorn.stun * 0.35 then sorn:surrender() end
        if sorn.down then
            sorn.surrendered = true
            for _, e in group("sorn") do
                if not e.down then e:surrender() end
            end
            return "stand_down"
        end
        return nil
    end,
}

S.stand_down = {
    enter = function(self)
        self:objective("Captain Sorn", nil)
        self:say({ "op7_sorn_04", "op7_sorn_05", "op7_sorn_06", "op7_sorn_07", "op7_sorn_08" })
    end,
    update = function(self, dt) return not self.talking and "transmit" or nil end,
}

S.transmit = {
    checkpoint = true,
    enter = function(self)
        self:objective("Transmit the evidence", nil)
        self:say({ "op7_11", "op7_12", "op7_13", "op7_14", "op7_15" }, function()
            self:fade_out_then(function() Campaign.complete("op07") end)
        end)
    end,
    update = function(self, dt) return nil end,
}

-- Interaction on an arbitrary entity (Venn).
function M:interact_entity(e, prompt, flag, fn)
    if self.flags[flag] then Game.set_interactable(e, false); return end
    Game.register_interactable(e, prompt, function()
        if self.flags[flag] or self.talking then return end
        self.flags[flag] = true
        Game.set_interactable(e, false)
        fn()
    end)
end

-- Lifecycle --------------------------------------------------------------------------------------
local FIRST = { op04 = "op04_start", op05 = "op05_start", op06 = "op06_start", op07 = "op07_start" }

function M:start()
    self.flags = {}
    self.op_title = (Campaign.get(self.chapter) or {}).title or ""
    Game.mission = self
    Game.waypoint = nil
    Game.open_world = false
    local p = Game.progress()
    local cp = p.checkpoint
    self.first = FIRST[self.chapter] or "op04_start"
    self.resume = nil
    if type(cp) == "table" and cp.op == self.chapter and S[cp.stage] then self.resume = cp end
    Game.on("player_downed", function() self.downed_t = self.downed_t or 0 end)
    Game.on("restart_checkpoint", function() self:reload() end)
    Game.on("enemy_retreated", function(e)
        if e and e.valid and e.name == "Sorn" then
            local s = enemy("Sorn")
            if s then s.gone = true end
            e.position = V(0, -400, 0)
            e:set("Perceptible", { enabled = false })
        end
    end)
    self.boot = 0
end

function M:reload()
    local c = Campaign.get(self.chapter)
    Game.paused = false
    Game.cinematic = false
    Game.present.fade = 1
    scene.load(c and c.scene or "scenes/menu.vscene")
end

function M:enter(name)
    self.stage_name = name
    self.stage = S[name]
    Game.emit("mission_stage", name)
    if self.stage.enter then self.stage.enter(self) end
    if self.stage.checkpoint and not self.restoring then self:checkpoint(name) end
end

function M:restore(cp)
    self.restoring = true
    self.flags = cp.flags or {}
    if cp.inv then Inventory.restore(cp.inv) end
    table.clear(cleared)
    for _, nm in cp.downed or {} do
        local e = scene.find(nm)
        if e then
            for _, r in Squad.state().enemies do
                if r.entity.valid and r.entity.name == nm and r.ctl and r.ctl.group then cleared[r.ctl.group] = (cleared[r.ctl.group] or 0) + 1 end
            end
            scene.destroy(e)
        end
    end
    for id in self.flags.doors or {} do
        local d = door(id)
        if d then d:unlock(true) end
    end
    if self.flags.blast_open then
        local d = door("blast")
        if d then d:open(1, true) end
    end
    local pos = vec(cp.pos)
    self:place_player(pos, cp.yaw or 0)
    self:place_squad(pos, cp.yaw or 0)
    if self.flags.brick_stays then
        local post = mpos("Venn Post", V(24, 0, -2))
        local venn = Game.npcs and Game.npcs["Venn"]
        if venn then venn.actor:place(post, -90); venn:hold() end
        local b = Squad.member("Brick")
        if b then b:place(post + V(1.4, 0.3, 1.2), -90); b:set_order("hold"); b.pinned = true end
    end
    self:title(self.chapter)
    self:enter(cp.stage)
    self.restoring = false
end

function M:update(dt)
    if not Game.player or not Game.player_state then return end
    if self.boot ~= nil then
        self.boot += dt
        if self.boot < 0.15 then return end
        self.boot = nil
        if self.resume then self:restore(self.resume) else self:enter(self.first) end
    end
    if self.title_t then
        self.title_t -= dt
        if self.title_t <= 0 then
            self.title_t = nil
            Game.present.title = nil
            Game.present.subtitle_title = nil
        end
    end
    if self.fade_t then
        self.fade_t += dt
        Game.present.fade = math.clamp(self.fade_t / 1.2, 0, 1)
        if self.fade_t > 1.5 and self.fade_fn then
            local fn = self.fade_fn
            self.fade_fn = nil
            fn()
        end
        return
    end
    if self.downed_t then
        self.downed_t += dt
        Game.present.fade = math.clamp(self.downed_t / 1.5, 0, 1)
        if self.downed_t > 2.0 then
            self.downed_t = nil
            self:reload()
        end
        return
    end
    if Game.paused then return end
    Chatter.update(dt, self.stage_name, false, self.talking)
    self:update_scare(dt)
    local nxt = self.stage and self.stage.update(self, dt)
    if nxt then self:enter(nxt) end
end

M.stages = S
return M
