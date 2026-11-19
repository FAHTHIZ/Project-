-- SPECIAL OPS player inventory: slot-limited, state-preserving, serialisable.
--
--   Game.inventory = { slots = { primary = id?, secondary = id?, tool = id?, utility = id? },
--                      state = { [id] = { ammo, reserve, charges ... } } }
--
-- Every item lives in exactly one place: a slot here, a storage container (lib/storage.luau) or
-- the world. Taking an item into an occupied slot never deletes the old one: `take` returns the
-- displaced item and its state so the caller can put it where the new one came from.
-- Supplies (kind "supply") are consumed on pickup and never occupy a slot.
-- Every change emits "inventory_changed" (weapons.luau and the HUD listen).
local Game = require("scripts/lib/game")
local Items = require("scripts/lib/items")

local Inventory = {}

Inventory.DEFAULT = { primary = "carbine", secondary = "sidearm", tool = "scanner" }

local function inv()
    if not Game.inventory then Inventory.reset() end
    return Game.inventory
end

local function copy(t)
    if type(t) ~= "table" then return t end
    local o = {}
    for k, v in t do o[k] = copy(v) end
    return o
end

-- Resets to a slot table (defaults to the standard field loadout).
function Inventory.reset(slots)
    local s = { slots = {}, state = {} }
    for slot, id in (slots or Inventory.DEFAULT) do
        if Items.get(id) then
            s.slots[slot] = id
            s.state[id] = Items.new_state(id)
        end
    end
    Game.inventory = s
    Game.emit("inventory_changed")
    return s
end

function Inventory.slots() return inv().slots end
function Inventory.in_slot(slot) return inv().slots[slot] end

function Inventory.has(id)
    for _, v in inv().slots do if v == id then return true end end
    return false
end

function Inventory.state(id)
    if not Inventory.has(id) then return nil end
    local s = inv()
    s.state[id] = s.state[id] or Items.new_state(id)
    return s.state[id]
end

-- Can the item be taken? Returns ok, reason, displaced_id.
function Inventory.can_take(id)
    local d = Items.get(id)
    if not d then return false, "unknown", nil end
    if d.kind == "supply" then
        if d.refill then
            for _, slot in Items.weapon_slots do
                local w = inv().slots[slot]
                local st = w and inv().state[w]
                if st and st.reserve < Items.get(w).max_reserve then return true, nil, nil end
            end
            return false, "full", nil
        end
        return true, nil, nil
    end
    if Inventory.has(id) then return false, "carried", nil end
    return true, nil, inv().slots[d.slot]
end

-- Takes an item (with optional existing state). Returns ok, displaced_id, displaced_state.
-- For supplies, ok means the supply was consumed.
function Inventory.take(id, state)
    local ok, reason, displaced = Inventory.can_take(id)
    if not ok then return false, reason end
    local d = Items.get(id)
    local s = inv()
    if d.kind == "supply" then
        if d.refill then
            for _, slot in Items.weapon_slots do
                local w = s.slots[slot]
                local st = w and s.state[w]
                if st then
                    local wd = Items.get(w)
                    st.reserve = math.min(wd.max_reserve, st.reserve + math.ceil(wd.max_reserve * d.refill))
                end
            end
        end
        Game.emit("inventory_changed", id, "consumed")
        return true, nil, nil
    end
    local dstate = nil
    if displaced then
        dstate = s.state[displaced]
        s.state[displaced] = nil
    end
    s.slots[d.slot] = id
    s.state[id] = state or Items.new_state(id)
    Game.emit("inventory_changed", id, "taken", displaced)
    return true, displaced, dstate
end

-- Removes a carried item. Returns its state (to hand to storage or the world), or nil.
function Inventory.drop(id)
    local s = inv()
    for slot, v in s.slots do
        if v == id then
            s.slots[slot] = nil
            local st = s.state[id]
            s.state[id] = nil
            Game.emit("inventory_changed", id, "dropped")
            return st or Items.new_state(id)
        end
    end
    return nil
end

-- Uses one charge of a utility item. Returns true if a charge was spent; an emptied item is
-- removed (the kit is used up, it is not silently kept at zero).
function Inventory.spend(id)
    local st = Inventory.state(id)
    if not st or not st.charges or st.charges <= 0 then return false end
    st.charges -= 1
    if st.charges <= 0 then Inventory.drop(id) else Game.emit("inventory_changed", id, "spent") end
    return true
end

-- Deep copies for checkpoints (so later play cannot mutate a saved snapshot).
function Inventory.serialize() return copy(inv()) end

function Inventory.restore(t)
    if type(t) ~= "table" or type(t.slots) ~= "table" then return false end
    local s = { slots = {}, state = {} }
    for slot, id in t.slots do
        if Items.get(id) then
            s.slots[slot] = id
            s.state[id] = copy((t.state or {})[id]) or Items.new_state(id)
        end
    end
    Game.inventory = s
    Game.emit("inventory_changed", nil, "restored")
    return true
end

return Inventory
