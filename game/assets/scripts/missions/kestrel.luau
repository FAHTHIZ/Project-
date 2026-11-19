-- Kestrel Valley mission director: Prologue, Operation 01 (forest), Operation 02 (perimeter) and
-- Operation 03 (service yard) are one continuous open world (scenes/world/kestrel.vscene). Each
-- chapter scene is the same world with this script's `chapter` set to where it starts; finishing
-- a chapter in the world rolls straight on into the next one (no load) and records progress so
-- the menu can continue or replay from any chapter.
--
-- The director is a list of stages. A stage sets the objective and waypoint on enter, watches the
-- world in update and returns the next stage's name when its goal is met. Stages marked
-- `checkpoint` save the player, inventory and downed contractors; restarting (pause menu, or
-- being downed) reloads the chapter scene and resumes from the last checkpoint.
--
-- Script properties:
--   chapter   prologue | op01 | op02 | op03 (where this scene starts)
local Game = require("scripts/lib/game")
local Campaign = require("scripts/lib/campaign")
local Dialogue = require("scripts/lib/dialogue")
local Squad = require("scripts/lib/squad")
local Inventory = require("scripts/lib/inventory")
local PT = require("scripts/world/kestrel_points")

local M = {}
M.chapter = "prologue"

local V = vector.create
local SEATS = { Anchor = "driver", Patch = "front_right", Echo = "rear_left", Tally = "rear_right" }
local DOORS = { driver = "fl", front_right = "fr", rear_left = "rl", rear_right = "rr" }
local CHAPTER_OF = {}

local function flat(a, b)
    local d = a - b
    return math.sqrt(d.x * d.x + d.z * d.z)
end
local function ppos() return Game.player and Game.player.position or V(0, 0, 0) end
local function near(p, r) return flat(ppos(), p) < r end
local function mule() return Game.vehicles and Game.vehicles["Mule"] end
local function vec(t) return V(t[1], t[2], t[3]) end
local function tab(v) return { v.x, v.y, v.z } end

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
    for _, e in group(name) do if not e.down then n += 1 end end
    return n
end
local function group_total(name) return #group(name) end
local function group_engaged(name)
    for _, e in group(name) do
        if not e.down and e.state ~= "patrol" then return true end
    end
    return false
end
local function send_group(name, point, delay)
    for i, e in group(name) do
        if not e.down then e:investigate(point + V((i - 2) * 2.5, 0, 0), (delay or 0) + i * 0.4) end
    end
end

-- Nearest index on a polyline of points (kestrel_points trail/road arrays).
local function nearest_index(list, p)
    local best, bi = 1e9, 1
    for i, q in list do
        local d = flat(q, p)
        if d < best then best, bi = d, i end
    end
    return bi
end

-- Stages ---------------------------------------------------------------------------------------
local S = {}

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

-- Rolls the campaign on to the next chapter without a load (the world is continuous).
function M:advance(from, to)
    local p = Game.progress()
    p.completed = p.completed or {}
    p.completed[from] = true
    p.unlocked[to] = true
    p.op = to
    p.checkpoint = nil
    Game.save_progress()
    self.chapter_now = to
    self:title(to)
    local area = ({ op02 = "perimeter", op03 = "perimeter" })[to]
    if area and Game.music_area then Game.music_area(area) end
end

-- Places the squad in a loose group behind the player (checkpoint and chapter starts).
function M:place_squad(at, yaw)
    local r = math.rad(yaw or 0)
    local fwd = V(-math.sin(r), 0, -math.cos(r))
    local right = V(math.cos(r), 0, -math.sin(r))
    local offs = { Anchor = { -1.4, -1.6 }, Patch = { 1.3, -2.2 }, Echo = { -0.4, -3.4 }, Tally = { 1.6, -3.9 } }
    Squad.each(function(who, op)
        local o = offs[who] or { 0, -2 }
        local p = at + right * o[1] + fwd * o[2]
        op:place(V(p.x, at.y + 0.3, p.z), yaw)
    end)
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

function M:checkpoint(stage)
    local p = Game.progress()
    local downed = {}
    for _, r in Squad.state().enemies do
        if r.entity.valid and r.ctl and r.ctl.down then table.insert(downed, r.entity.name) end
    end
    local ps = Game.player_state
    p.checkpoint = { op = self.chapter_now, stage = stage, pos = tab(ppos()), yaw = ps and ps.yaw or 0,
                     inv = Inventory.serialize(), downed = downed, flags = self.flags }
    Game.save_progress()
    Game.toast("Checkpoint", 2.0)
end

-- Prologue -------------------------------------------------------------------------------------
-- Staging camp at dawn: briefing at the table, board the Mule, ride the ranger road to the trailhead.
S.brief = {
    enter = function(self)
        self:title("prologue")
        self:objective("Join the briefing at the camp table", PT.camp_table, "BRIEFING")
        self.wait = 2.5
    end,
    update = function(self, dt)
        if self.started_brief then return self.brief_done and "board" or nil end
        self.wait -= dt
        if self.wait <= 0 and near(PT.camp_table, 7) then
            self.started_brief = true
            self:say({ "pro_01", "pro_02", "pro_03", "pro_04", "pro_05", "pro_06", "pro_07", "pro_08",
                       "pro_09", "pro_10", "pro_11", "pro_12" }, function() self.brief_done = true end)
        end
        return nil
    end,
}

S.board = {
    enter = function(self)
        local v = mule()
        self:objective("Board the Mule", v and v:door_point("rl"), "MULE")
        -- the squad walks to their doors
        local pts = {}
        for who, seat in SEATS do pts[who] = v:door_point(DOORS[seat]) end
        Squad.order("move", pts)
        local mark = scene.find("Mark Board")
        if mark then
            mark.position = v:door_point("rl")
            Game.register_interactable(mark, "Board the Mule", function()
                if self.boarding then return end
                self.boarding = 0
                Game.set_interactable(mark, false)
            end)
        end
    end,
    update = function(self, dt)
        if not self.boarding then return nil end
        -- a short fade covers climbing in (the cabin is too tight to walk through)
        self.boarding += dt
        Game.present.fade = math.clamp(self.boarding / 0.5, 0, 1)
        if self.boarding >= 0.6 and not self.seated then
            self.seated = true
            local v = mule()
            Squad.each(function(who, op) op:board(v, SEATS[who]) end)
            Game.player_state:ride(v, "rear_middle")
            for _, d in { "fl", "fr", "rl", "rr" } do v:set_door(d, false) end
        end
        if self.seated then
            Game.present.fade = math.clamp(1 - (self.boarding - 0.9) / 0.6, 0, 1)
            if self.boarding > 1.6 then return "ride" end
        end
        return nil
    end,
}

S.ride = {
    enter = function(self)
        local v = mule()
        self:objective("Ride to the trailhead", PT.poi_trailhead, "TRAILHEAD")
        v:start_engine()
        local road = PT.road_in
        local k = nearest_index(road, v.entity.position)
        local pts = {}
        for i = math.min(#road, k + 1), #road do table.insert(pts, road[i]) end
        -- pull into the turnout beside the trail sign
        table.insert(pts, PT.mule_park)
        self.drive_wait = 2.0
        self.pts = pts
        self.ride_t = 0
    end,
    update = function(self, dt)
        local v = mule()
        if self.drive_wait then
            self.drive_wait -= dt
            if self.drive_wait <= 0 then
                self.drive_wait = nil
                v:drive(self.pts, { speed = 8.5, accel = 1.6, decel = 1.4 })
            end
            return nil
        end
        self.ride_t += dt
        if self.ride_t > 3 and not self.ride_lines then
            self.ride_lines = true
            self:say({ "ride_01", "ride_02", "ride_03", "ride_04", "ride_05", "ride_06", "ride_07", "ride_08" })
        end
        if not v:driving() then return "arrive" end
        return nil
    end,
}

S.arrive = {
    enter = function(self)
        local v = mule()
        v:stop_engine()
        self.arrive_t = 0
        self:say("ride_09")
        local delays = { Anchor = 0.6, Patch = 1.0, Echo = 1.8, Tally = 2.3 }
        local regroup = {
            Anchor = PT.trail_start + V(-1.5, 0, -1.0), Patch = PT.trail_start + V(1.4, 0, 0.6),
            Echo = PT.trail_start + V(-0.6, 0, -3.0), Tally = PT.trail_start + V(2.4, 0, 1.6),
        }
        Squad.each(function(who, op)
            op:exit_vehicle(DOORS[op.seat], { delay = delays[who], regroup = regroup[who], face = PT.trail_start })
        end)
    end,
    update = function(self, dt)
        self.arrive_t += dt
        -- Rook slides out of the middle seat through the rear left door once Echo is clear
        if self.arrive_t > 4.2 and not self.dismounting then
            self.dismounting = true
            Game.player_state:dismount("rl", PT.trail_start)
        end
        if self.dismounting and not Game.player_state:in_vehicle() and not self.exchange then
            self.exchange = true
            Squad.order("follow")
            self:advance("prologue", "op01")
            self:say({ "op1_arrive_01", "op1_arrive_02", "op1_arrive_03", "op1_arrive_04" },
                     function() self.arrived = true end)
        end
        if self.arrived then return "trail" end
        return nil
    end,
}

-- Operation 01: Greenline --------------------------------------------------------------------------
S.op01_start = {
    -- chapter start from the menu: the squad is already out of the Mule at the trailhead
    enter = function(self)
        self:title("op01")
        self.op_title = Campaign.get("op01").title
        self.wait = 1.5
    end,
    update = function(self, dt)
        self.wait -= dt
        if self.wait > 0 then return nil end
        if not self.started then
            self.started = true
            self:say({ "op1_arrive_01", "op1_arrive_02", "op1_arrive_03", "op1_arrive_04" },
                     function() self.go = true end)
        end
        return self.go and "trail" or nil
    end,
}

S.trail = {
    checkpoint = true,
    enter = function(self)
        self:objective("Follow the forest trail", PT.trail_marker, "TRAIL")
        self.trail_from = ppos()
    end,
    update = function(self, dt)
        if not self.flags.trail_01 and flat(ppos(), self.trail_from) > 45 then
            self.flags.trail_01 = true
            self:say("op1_trail_01")
        end
        if not self.flags.trail_02 and near(PT.trail_marker, 30) then
            self.flags.trail_02 = true
            self:say("op1_trail_02")
        end
        if near(PT.trail_marker, 6) and not self.talking then
            self:say({ "op1_marker_01", "op1_marker_02" })
            return "cabin"
        end
        return nil
    end,
}

S.cabin = {
    checkpoint = true,
    enter = function(self)
        self:objective("Check the ranger cabin", PT.cabin_porch, "CABIN")
    end,
    update = function(self, dt)
        if not self.cabin_talk and near(PT.cabin_porch, 13) then
            self.cabin_talk = true
            Squad.order("hold")
            Dialogue.clear(2)
            self:say({ "op1_cabin_01", "op1_cabin_02", "op1_cabin_03", "op1_cabin_04", "op1_cabin_05",
                       "op1_cabin_06", "op1_cabin_07" }, function() self.cabin_done = true end)
        end
        if self.cabin_done then
            Squad.order("follow")
            return "relay_path"
        end
        return nil
    end,
}

S.relay_path = {
    checkpoint = true,
    enter = function(self)
        self:objective("Find the Greyline relay on the north ridge", PT.relay_stand, "RELAY")
    end,
    update = function(self, dt)
        -- the patrol by the fallen pines: Echo spots them first, Rook decides when to engage
        if not self.flags.patrol_seen and group_up("patrol") > 0 and self:spotted("patrol", 42) then
            self.flags.patrol_seen = true
            self:say({ "op1_patrol_01", "op1_patrol_02" })
        end
        if self.flags.patrol_seen and not self.flags.patrol_done and group_up("patrol") == 0 then
            self.flags.patrol_done = true
            self:say("op1_patrol_03")
        end
        if near(PT.relay_stand, 24) then return "relay" end
        return nil
    end,
}

S.relay = {
    checkpoint = true,
    enter = function(self)
        if not self.flags.relay_01 then
            self.flags.relay_01 = true
            self:say("op1_relay_01")
        end
        self:objective("Scan the relay with the field scanner", PT.relay_stand, "RELAY")
        self.cell = scene.find("Mark Relay Cell")
        if self.cell then
            Game.register_interactable(self.cell, "Pull the power cell", function()
                if not self.flags.scanned then
                    Game.toast("Scan the relay first", 2.0)
                    return
                end
                self.flags.cell = true
                Game.set_interactable(self.cell, false)
                audio.play("audio/foley/cell_out.wav", { bus = "sfx", volume = 0.9, position = PT.relay_bay })
            end)
            Game.set_interactable(self.cell, false)
        end
    end,
    update = function(self, dt)
        if self.flags.scanned and not self.cell_prompt then
            self.cell_prompt = true
            if self.cell then Game.set_interactable(self.cell, true) end
            self:objective("Pull the relay's power cell", PT.relay_bay, "POWER CELL")
        end
        if self.flags.cell then
            self:say({ "op1_relay_02", "op1_relay_03" })
            -- Greyline notice the relay going dark and send a team to the ravine clearing
            send_group("ambush", PT.poi_ravine, 6.0)
            return "ambush"
        end
        return nil
    end,
}

S.ambush = {
    checkpoint = true,
    enter = function(self)
        self:objective("Push through the ravine clearing", PT.poi_ravine, "CLEARING")
    end,
    update = function(self, dt)
        if not self.flags.ambush_01 and (near(PT.poi_ravine, 40) or group_engaged("ambush")) then
            self.flags.ambush_01 = true
            Dialogue.clear(2)
            self:say({ "op1_ambush_01", "op1_ambush_02" })
        end
        if self.flags.ambush_01 and group_up("ambush") == 0 and group_up("patrol") == 0 then
            self:say("op1_ambush_03")
            return "ridge"
        end
        return nil
    end,
}

S.ridge = {
    checkpoint = true,
    enter = function(self)
        self:objective("Climb to the ridge saddle", PT.poi_saddle, "SADDLE")
    end,
    update = function(self, dt)
        if not self.ridge_talk and near(PT.poi_saddle, 10) then
            self.ridge_talk = true
            Squad.order("hold")
            self:say({ "op1_ridge_01", "op1_ridge_02", "op1_ridge_03", "op1_ridge_04", "op1_ridge_05", "op1_ridge_06" },
                     function() self.ridge_done = true end)
        end
        if self.ridge_done then
            Squad.order("follow")
            self:advance("op01", "op02")
            return "fence"
        end
        return nil
    end,
}

-- Operation 02: Fenceline ----------------------------------------------------------------------------
S.op02_start = {
    enter = function(self) self:title("op02"); self.wait = 1.0 end,
    update = function(self, dt) self.wait -= dt; return self.wait <= 0 and "fence" or nil end,
}

S.fence = {
    checkpoint = true,
    enter = function(self)
        self:objective("Reach the perimeter fence", PT.fence_approach, "FENCE")
    end,
    update = function(self, dt)
        if near(PT.fence_approach, 30) or group_engaged("towers") then
            self:say({ "op2_01", "op2_02", "op2_03", "op2_04" })
            return "towers"
        end
        return nil
    end,
}

S.towers = {
    enter = function(self)
        self.n_towers = group_total("towers")
        self:objective(string.format("Clear the watchtower guards (0/%d)", self.n_towers), PT.gate, "GATE")
        self.last_left = -1
    end,
    update = function(self, dt)
        local left = group_up("towers") + group_up("gate")
        local total = self.n_towers + group_total("gate")
        if left ~= self.last_left then
            self.last_left = left
            if left > 0 then
                Game.objective.text = string.format("Clear the watchtower guards (%d/%d)", total - left, total)
            end
        end
        if left == 0 then
            self:say({ "op2_05", "op2_06" })
            return "booth"
        end
        return nil
    end,
}

S.booth = {
    checkpoint = true,
    enter = function(self)
        self:objective("Get Tally to the gate booth panel", PT.booth_panel, "BOOTH")
        self.panel = scene.find("Mark Booth Panel")
        if self.panel then
            Game.register_interactable(self.panel, "Hook Tally into the panel", function()
                self.flags.panel = true
                Game.set_interactable(self.panel, false)
            end)
        end
    end,
    update = function(self, dt)
        if self.flags.panel then
            local tally = Squad.member("Tally")
            if tally then tally:set_order("move", PT.booth_panel + V(0.8, 0, 0.8)) end
            self:say({ "op2_07", "op2_08" })
            return "hold_gate"
        end
        return nil
    end,
}

S.hold_gate = {
    enter = function(self)
        self.hack_t = 0
        self.hack_len = 32
        self:objective("Cover Tally while the gate opens", PT.gate, "GATE")
        send_group("reinf", PT.gate + V(0, 0, -12), 4.0)
    end,
    update = function(self, dt)
        if Game.playing() then self.hack_t += dt end
        if not self.flags.voss_1 and self.hack_t > 4 then
            self.flags.voss_1 = true
            self:say({ "op2_09", "op2_10" })
        end
        local pct = math.floor(math.clamp(self.hack_t / self.hack_len, 0, 1) * 100)
        Game.objective.text = string.format("Cover Tally while the gate opens (%d%%)", pct)
        if self.hack_t >= self.hack_len and group_up("reinf") == 0 then
            self:say({ "op2_11", "op2_12" })
            self:open_gate()
            local tally = Squad.member("Tally")
            if tally then tally:set_order("follow") end
            return "gate_open"
        end
        return nil
    end,
}

S.gate_open = {
    enter = function(self) self.wait = 3.0 end,
    update = function(self, dt)
        self.wait -= dt
        if self.wait <= 0 and not self.talking then
            self:advance("op02", "op03")
            return "yard"
        end
        return nil
    end,
}

-- Operation 03: Service Yard -----------------------------------------------------------------------
S.op03_start = {
    enter = function(self)
        self:title("op03")
        self:open_gate(true)
        self.wait = 1.0
    end,
    update = function(self, dt) self.wait -= dt; return self.wait <= 0 and "yard" or nil end,
}

S.yard = {
    checkpoint = true,
    enter = function(self)
        if not self.flags.yard_talk then
            self.flags.yard_talk = true
            self:say({ "op3_01", "op3_02", "op3_03" })
        end
        self:objective("Clear the service yard", PT.poi_compound, "YARD")
    end,
    update = function(self, dt)
        if group_up("yard") == 0 then
            self:say("op3_04")
            return "office"
        end
        return nil
    end,
}

S.office = {
    checkpoint = true,
    enter = function(self)
        self:objective("Search the site office for an access card", PT.office_desk, "OFFICE")
        self.desk = scene.find("Mark Office Desk")
        if self.desk then
            Game.register_interactable(self.desk, "Take the access card", function()
                self.flags.card = true
                Game.set_interactable(self.desk, false)
                audio.play("audio/foley/pickup.wav", { bus = "sfx", volume = 0.8, position = PT.office_desk })
            end)
        end
    end,
    update = function(self, dt)
        if self.flags.card then
            self:say({ "op3_05", "op3_06" })
            return "entrance"
        end
        return nil
    end,
}

S.entrance = {
    checkpoint = true,
    enter = function(self)
        self:objective("Open the facility entrance", PT.facility_panel, "ENTRANCE")
        self.panel = scene.find("Mark Facility Panel")
        if self.panel then
            Game.register_interactable(self.panel, "Use the access card", function()
                if self.talking then return end
                self.flags.entered = true
                Game.set_interactable(self.panel, false)
            end)
        end
    end,
    update = function(self, dt)
        if not self.flags.voss_2 and near(PT.facility_front, 35) then
            self.flags.voss_2 = true
            self:say({ "op3_07", "op3_08", "op3_09", "op3_10" })
        end
        if self.flags.entered then return "enter_facility" end
        return nil
    end,
}

S.enter_facility = {
    enter = function(self) self.fade_t = 0 end,
    update = function(self, dt)
        self.fade_t += dt
        Game.present.fade = math.clamp(self.fade_t / 1.2, 0, 1)
        if self.fade_t > 1.5 and not self.loaded then
            self.loaded = true
            Campaign.complete("op03")
        end
        return nil
    end,
}

-- Helpers used by stages ---------------------------------------------------------------------------
-- True when a live member of `name` is within `r` metres of the player or any operator can see one.
function M:spotted(name, r)
    for _, e in group(name) do
        if not e.down and flat(e.entity.position, ppos()) < r then return true end
    end
    return false
end

function M:open_gate(instant)
    self.gate = { t = instant and 1 or 0, leaves = {} }
    for _, nm in { "Gate Leaf West", "Gate Leaf East" } do
        local e = scene.find(nm)
        if e then table.insert(self.gate.leaves, { e = e, p0 = e.position, s = nm == "Gate Leaf East" and 1 or -1 }) end
    end
    if not instant then
        audio.play("audio/foley/gate_motor.wav", { bus = "sfx", volume = 0.9, position = PT.gate })
    end
end

function M:update_gate(dt)
    local g = self.gate
    if not g then return end
    g.t = math.min(1, g.t + dt / 6.0)
    local k = g.t * g.t * (3 - 2 * g.t)
    for _, l in g.leaves do
        if l.e.valid then l.e.position = l.p0 + V(l.s * 4.2 * k, 0, 0) end
    end
end

-- Lifecycle ------------------------------------------------------------------------------------------
local FIRST = { prologue = "brief", op01 = "op01_start", op02 = "op02_start", op03 = "op03_start" }

function M:start()
    self.flags = {}
    self.chapter_now = self.chapter
    self.op_title = (Campaign.get(self.chapter) or {}).title or ""
    Game.mission = self
    Game.waypoint = nil
    Game.open_world = true
    local p = Game.progress()
    local cp = p.checkpoint
    self.first = FIRST[self.chapter] or "brief"
    self.resume = nil
    if type(cp) == "table" and cp.op == self.chapter and S[cp.stage] then self.resume = cp end
    Game.on("scanned", function(e)
        if e and e.valid and (e.name == "Relay Mast" or e.name == "Mark Relay Cell") then self.flags.scanned = true end
    end)
    Game.on("player_downed", function() self.downed_t = self.downed_t or 0 end)
    Game.on("restart_checkpoint", function() self:reload() end)
    self.boot = 0
end

function M:reload()
    -- the latest checkpoint belongs to the chapter being played, which may be later than the one
    -- this scene started at
    local c = Campaign.get(self.chapter_now)
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
    for _, nm in cp.downed or {} do
        local e = scene.find(nm)
        if e then scene.destroy(e) end
    end
    local pos = vec(cp.pos)
    self:place_player(pos, cp.yaw or 0)
    self:place_squad(pos, cp.yaw or 0)
    if self.chapter == "op03" then self:open_gate(true) end
    self:title(self.chapter_now)
    self:enter(cp.stage)
    self.restoring = false
end

function M:update(dt)
    if not Game.player or not Game.player_state then return end
    -- first frame after load: actors have registered by now
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
    self:update_gate(dt)
    -- downed: Patch can't patch everything; fade and restart from the last checkpoint
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
    local nxt = self.stage and self.stage.update(self, dt)
    if nxt then self:enter(nxt) end
end

-- Mark which chapter each stage belongs to (for menus and checkpoints).
for _, k in { "brief", "board", "ride", "arrive" } do CHAPTER_OF[k] = "prologue" end
for _, k in { "op01_start", "trail", "cabin", "relay_path", "relay", "ambush", "ridge" } do CHAPTER_OF[k] = "op01" end
for _, k in { "op02_start", "fence", "towers", "booth", "hold_gate", "gate_open" } do CHAPTER_OF[k] = "op02" end
for _, k in { "op03_start", "yard", "office", "entrance", "enter_facility" } do CHAPTER_OF[k] = "op03" end
M.stages = S
M.chapter_of = CHAPTER_OF

return M
