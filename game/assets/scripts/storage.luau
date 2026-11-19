-- Item storage container (the Mule's cargo bay; also usable for crates and lockers).
-- Every item is a real, pre-placed world model (tools/scenes/vehicle.py add_storage_pool): items in
-- the container sit on its slot anchors, everything else is parked out of sight. Looking at an
-- item shows its name and description; interacting takes it into the inventory. An item that
-- displaces a carried one swaps: the carried item is put back in the slot the new one came from,
-- so nothing is ever deleted. Contents persist across scene reloads (Game.storage_state) and are
-- saved with checkpoints (Storage.serialize_all / restore_all).
--
-- Entity: "<owner> Cargo" with "<...> Slot L1|L2|S1.." anchors and "<...> Item <id> <n>" pool children.
-- Properties: id (save key), contents ("id,id,..." initial), owner (vehicle name gating access by
-- its hatch; empty = derived from the name, "none" = always open).
local Game = require("scripts/lib/game")
local Items = require("scripts/lib/items")
local Inventory = require("scripts/lib/inventory")

local S = {}
S.id = "storage"
S.contents = ""
S.owner = ""

Game.storages = Game.storages or {}
Game.storage_state = Game.storage_state or {}

local PARK = vector.create(0, -20, 0)

local function copy(t)
    if type(t) ~= "table" then return t end
    local o = {}
    for k, v in t do o[k] = copy(v) end
    return o
end

local function is_long(id)
    local d = Items.get(id)
    return d and d.kind == "weapon" and d.slot == "primary"
end

function S:start()
    local e = self.entity
    local n = e.name
    if self.owner == "" then
        local i = string.find(n, " Cargo", 1, true)
        if i then self.owner = string.sub(n, 1, i - 1) end
    end
    if self.owner == "none" then self.owner = "" end  -- free-standing case or locker, always open
    self.slots = {}
    for _, key in { "L1", "L2", "L3", "L4", "S1", "S2", "S3", "S4" } do
        local a = scene.find(n .. " Slot " .. key)
        if a then table.insert(self.slots, { key = key, anchor = a, long = string.sub(key, 1, 1) == "L" }) end
    end
    self.pool = {}  -- id -> { entity, ... }
    for id in Items.defs do
        for k = 1, 6 do
            local p = scene.find(n .. " Item " .. id .. " " .. k)
            if not p then break end
            self.pool[id] = self.pool[id] or {}
            table.insert(self.pool[id], { entity = p, used = false, anim = nil })
        end
    end
    -- contents: persisted state wins over the scene's initial list
    local saved = Game.storage_state[self.id]
    if saved then
        self.items = saved
    else
        self.items = {}
        for id in string.gmatch(self.contents, "[^,%s]+") do
            if Items.get(id) then table.insert(self.items, { id = id, state = Items.new_state(id) }) end
        end
        Game.storage_state[self.id] = self.items
    end
    self.open = self.owner == ""
    Game.storages[self.id] = self
    self:layout()
end

-- Slot assignment: rifles across the long slots, everything else along the small ones; an item
-- keeps its slot while it stays in the container.
function S:assign()
    local taken = {}
    for _, it in self.items do if it.slot then taken[it.slot] = true end end
    for _, it in self.items do
        if not it.slot then
            local want_long = is_long(it.id)
            for pass = 1, 2 do
                for _, s in self.slots do
                    if not taken[s.key] and (pass == 2 or s.long == want_long) then
                        it.slot = s.key; taken[s.key] = true; break
                    end
                end
                if it.slot then break end
            end
        end
    end
end

function S:slot(key)
    for _, s in self.slots do if s.key == key then return s end end
    return nil
end

function S:layout()
    self:assign()
    for _, list in self.pool do for _, p in list do p.used = false end end
    for i, it in self.items do
        local list = self.pool[it.id]
        local p = nil
        if list then for _, c in list do if not c.used then p = c; break end end end
        it.view = p
        local s = it.slot and self:slot(it.slot)
        if p and s then
            p.used = true
            if not p.anim then
                p.entity.position = s.anchor.position
                p.entity.rotation = s.anchor.rotation
            end
            p.index = i
            Game.register_interactable(p.entity, "", function() self:take_view(p) end)
            self:refresh_prompt(it)
        end
    end
    for _, list in self.pool do
        for _, p in list do
            if not p.used then
                if not p.anim then p.entity.position = PARK end
                Game.set_interactable(p.entity, false)
            end
        end
    end
end

function S:prompt_for(it)
    local d = Items.get(it.id)
    local ok, reason, displaced = Inventory.can_take(it.id)
    local detail = d.desc
    if d.kind == "weapon" then detail = string.format("%s  Cells %d / %d", d.desc, it.state.ammo or 0, it.state.reserve or 0) end
    if d.charges then detail = string.format("%s  Uses %d", d.desc, it.state.charges or 0) end
    if not ok and reason == "carried" then return "Already carrying " .. d.label, detail end
    if not ok and reason == "full" then return d.label .. " (cells full)", detail end
    if displaced then return "Swap " .. Items.get(displaced).label .. " for " .. d.label, detail end
    return "Take " .. d.label, detail
end

function S:refresh_prompt(it)
    local p = it.view
    if not p then return end
    local prompt, detail = self:prompt_for(it)
    Game.set_interactable(p.entity, self.open, prompt)
    local r = Game.interactables[p.entity.id]
    if r then r.detail = detail end
end

function S:find(id)
    for i, it in self.items do if it.id == id then return i, it end end
    return nil
end

-- Takes item index i into the inventory. Returns ok, reason.
function S:take(i)
    local it = self.items[i]
    if not it then return false, "missing" end
    if not self.open then return false, "closed" end
    local d = Items.get(it.id)
    local ok, displaced, dstate = Inventory.take(it.id, it.state)
    if not ok then
        local reason = displaced
        if Game.toast then
            Game.toast(reason == "full" and "Cells already full" or reason == "carried" and ("Already carrying " .. d.label)
                or "Can't take that", 1.6)
        end
        Game.emit("storage_refused", self.id, it.id, reason)
        return false, reason
    end
    local view = it.view
    local slot = it.slot
    table.remove(self.items, i)
    if displaced then
        -- the carried item goes back where the new one was
        table.insert(self.items, { id = displaced, state = dstate or Items.new_state(displaced), slot = slot, arriving = true })
    end
    if view then
        view.anim = { t = 0, dur = 0.28, kind = "out", from = view.entity.position }
    end
    audio.play("audio/foley/item_pick.wav", { volume = 0.8, bus = "sfx",
                                             position = view and view.entity.world_position or self.entity.world_position })
    self:layout()
    for _, it2 in self.items do
        if it2.arriving then
            it2.arriving = nil
            if it2.view then
                local s = self:slot(it2.slot)
                it2.view.anim = { t = 0, dur = 0.42, kind = "in", to = s.anchor.position, rot = s.anchor.rotation, delay = 0.35 }
                it2.view.entity.position = PARK
            end
        end
    end
    if Game.toast then
        Game.toast(displaced and (d.label .. " taken. " .. Items.get(displaced).label .. " stowed") or (d.label .. " taken"), 2.2)
    end
    Game.emit("storage_taken", self.id, d.id, displaced)
    for _, x in self.items do self:refresh_prompt(x) end
    return true
end

function S:take_view(p)
    for i, it in self.items do
        if it.view == p then return self:take(i) end
    end
    return false
end

-- Puts an item (carried or from the world) into the container. Returns ok.
function S:put(id, state)
    if #self.items >= #self.slots then return false end
    table.insert(self.items, { id = id, state = state or Items.new_state(id) })
    self:layout()
    audio.play("audio/foley/item_place.wav", { volume = 0.7, bus = "sfx", position = self.entity.world_position })
    Game.emit("storage_put", self.id, id)
    return true
end

-- Ids currently inside, in slot order (tests and dialogue).
function S:list()
    local out = {}
    for _, it in self.items do table.insert(out, it.id) end
    return out
end

function S:update(dt)
    if Game.paused then return end
    if self.owner ~= "" then
        local v = Game.vehicles and Game.vehicles[self.owner]
        local open = v ~= nil and v:hatch_is_open()
        if open ~= self.open then
            self.open = open
            for _, it in self.items do self:refresh_prompt(it) end
        end
    end
    -- item motion: taken items rise toward the player's hands and park; returned items set down
    for _, list in self.pool do
        for _, p in list do
            local a = p.anim
            if a then
                if a.delay and a.delay > 0 then a.delay -= dt
                else
                    a.t += dt
                    local k = math.clamp(a.t / a.dur, 0, 1)
                    local s = k * k * (3 - 2 * k)
                    if a.kind == "out" then
                        p.entity.position = a.from + vector.create(0, 0.35 * s, 0.35 * s)
                        if k >= 1 then p.entity.position = PARK; p.anim = nil end
                    else
                        local from = a.to + vector.create(0, 0.32, 0.3)
                        p.entity.position = from + (a.to - from) * s
                        p.entity.rotation = a.rot
                        if k >= 1 then
                            p.anim = nil
                            audio.play("audio/foley/item_place.wav", { volume = 0.6, bus = "sfx", position = p.entity.world_position })
                        end
                    end
                end
            end
        end
    end
    -- prompts follow the inventory (e.g. cells become "full" after a top-up)
    self.prompt_t = (self.prompt_t or 0) - dt
    if self.prompt_t <= 0 and self.open then
        self.prompt_t = 0.25
        for _, it in self.items do self:refresh_prompt(it) end
    end
end

-- Checkpoint support ---------------------------------------------------------------------------
local Storage = {}
function Storage.serialize_all()
    local out = {}
    for id, items in Game.storage_state do
        out[id] = {}
        for _, it in items do table.insert(out[id], { id = it.id, state = copy(it.state), slot = it.slot }) end
    end
    return out
end
function Storage.restore_all(t)
    Game.storage_state = {}
    for id, items in (t or {}) do
        local list = {}
        for _, it in items do table.insert(list, { id = it.id, state = copy(it.state), slot = it.slot }) end
        Game.storage_state[id] = list
        local live = Game.storages[id]
        if live and live.entity.valid then live.items = list; live:layout() end
    end
end
function Storage.reset_all() Game.storage_state = {} end
Game.Storage = Storage

return S
