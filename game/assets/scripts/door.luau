-- Facility doors (tools/levels/build_facility.py). One entity per doorway; children:
--   "Leaf L" / "Leaf R"  sliding leaves (auto doors), or "Leaf" (blast door, rises)
--   "Blocker"            box collider filling the opening while the door is locked or closed shut
--
-- Auto doors open for anyone close (player, squad, contractors) once unlocked, and close again
-- behind them; the opening is walkable as soon as the leaves are mostly clear (the blocker only
-- exists while locked). Locked doors show a "Locked" prompt and refuse with a buzz.
-- Blast doors stay shut until a mission calls door:open(rate) (the crank), then stay open.
--
--   local d = Game.doors["corB_labW"]; d:unlock()     d:open(1/6)   d:amount()
local Game = require("scripts/lib/game")
local Squad = require("scripts/lib/squad")

local D = {}
D.id = ""
D.width = 2.0
D.locked = false
D.kind = "auto"        -- auto | blast
D.hint = "Locked"
D.RANGE = 3.2
D.OPEN_TIME = 0.55

local V = vector.create
local function smooth(t) t = math.clamp(t, 0, 1); return t * t * (3 - 2 * t) end

Game.doors = Game.doors or {}

function D:start()
    if self.id == "" then self.id = self.entity.name end
    Game.doors[self.id] = self
    local e = self.entity
    self.leaf_l = e:find_child("Leaf L")
    self.leaf_r = e:find_child("Leaf R")
    self.leaf = e:find_child("Leaf")
    self.blocker = e:find_child("Blocker")
    self.a = 0
    self.want = 0
    self.rate = 1 / self.OPEN_TIME
    self.forced = false
    if self.leaf_l then self.l0 = self.leaf_l.position end
    if self.leaf_r then self.r0 = self.leaf_r.position end
    if self.leaf then self.f0 = self.leaf.position end
    if self.locked or self.kind == "blast" then
        Game.register_interactable(self.entity, self.kind == "blast" and "Sealed" or self.hint, function() self:refuse() end)
        Game.set_interactable(self.entity, self.locked)
    else
        self:clear_blocker()
    end
end

function D:clear_blocker()
    local b = self.blocker
    if b and b.valid then
        if b:has("Collider") then b:remove("Collider") end
        if b:has("RigidBody") then b:remove("RigidBody") end
    end
end

function D:refuse()
    audio.play("audio/foley/card_deny.wav", { bus = "sfx", volume = 0.7, position = self.entity.world_position + V(0, 1.2, 0) })
    Game.toast(self.kind == "blast" and "The blast door is sealed" or self.hint, 1.6)
end

function D:unlock(silent)
    if not self.locked then return end
    self.locked = false
    Game.set_interactable(self.entity, false)
    if self.kind ~= "blast" then self:clear_blocker() end
    if not silent then
        audio.play("audio/foley/card_accept.wav", { bus = "sfx", volume = 0.7, position = self.entity.world_position + V(0, 1.2, 0) })
    end
    Game.emit("door_unlocked", self.id)
end

-- Forces the door open at `rate` (fraction per second); blast doors are opened this way.
function D:open(rate, instant)
    self.locked = false
    Game.set_interactable(self.entity, false)
    self.forced = true
    self.want = 1
    self.rate = rate or self.rate
    if instant then self.a = 1; self:pose() end
    if self.kind == "blast" and not instant then
        audio.play("audio/foley/blast_door.wav", { bus = "sfx", volume = 0.95, position = self.entity.world_position + V(0, 1.6, 0) })
    end
end

function D:amount() return self.a end

function D:someone_near()
    local c = self.entity.world_position
    local r2 = self.RANGE * self.RANGE
    local function close(p)
        local dx, dz = p.x - c.x, p.z - c.z
        return dx * dx + dz * dz < r2 and math.abs(p.y - c.y) < 2.5
    end
    if Game.player and Game.player.valid and close(Game.player.position) then return true end
    local hit = false
    Squad.each(function(_, op) if not hit and close(op.entity.position) then hit = true end end)
    if hit then return true end
    for _, r in Squad.state().enemies do
        if r.entity.valid and r.ctl and not r.ctl.down and close(r.entity.position) then return true end
    end
    return false
end

function D:pose()
    local k = smooth(self.a)
    if self.leaf then
        self.leaf.position = self.f0 + V(0, 3.05 * k, 0)
        if k > 0.62 then self:clear_blocker() end
    else
        local slide = self.width * 0.48 * k
        if self.leaf_l then self.leaf_l.position = self.l0 - V(slide, 0, 0) end
        if self.leaf_r then self.leaf_r.position = self.r0 + V(slide, 0, 0) end
    end
end

function D:update(dt)
    if Game.paused then return end
    if not self.forced then
        if self.locked or self.kind == "blast" then
            self.want = 0
        else
            -- poll the neighbourhood a few times a second (cheap enough for ~10 doors)
            self.poll = (self.poll or 0) - dt
            if self.poll <= 0 then
                self.poll = 0.2
                self.want = self:someone_near() and 1 or 0
            end
        end
    end
    if self.a ~= self.want then
        local was = self.a
        local step = (self.forced and self.rate or 1 / self.OPEN_TIME) * dt
        if self.want > self.a then self.a = math.min(self.want, self.a + step) else self.a = math.max(self.want, self.a - step) end
        if self.kind ~= "blast" and ((was == 0 and self.a > 0) or (was == 1 and self.a < 1)) then
            audio.play("audio/foley/door_slide.wav", { bus = "sfx", volume = 0.55, pitch = self.want == 1 and 1.0 or 0.93,
                                                      position = self.entity.world_position + V(0, 1.4, 0), max_instances = 4 })
        end
        self:pose()
    end
end

return D
