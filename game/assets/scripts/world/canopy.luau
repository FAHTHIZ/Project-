-- Canopy proxies for Kestrel Valley (tools/world/worldgen.py, docs/world/KESTREL_VALLEY.md).
-- Near blocks are one merged low-poly mesh per 64 m streaming cell; while a cell's detailed
-- trees are loaded the block is hidden, otherwise it carries that cell's forest silhouette.
-- Far blocks (outside the walkable area) are always drawn. A cell counts as loaded once its
-- trees exist and have been there for `settle` seconds (cells appear when their models are
-- ready), and as unloaded as soon as they are gone, so a gap never opens: at worst both draw
-- for the settle time.
local Game = require("scripts/lib/game")

local C = {}
C.cell_size = 64
C.interval = 0.4
C.settle = 0.6

local function set_shown(e, on)
    for _, ch in e:children() do
        if ch:has("MeshRenderer") then ch:set_visible(on) end
    end
end

function C:start()
    self.near = {}
    self.far = 0
    self.seen = {}
    self.t = 0
    self.age = 0
    for _, ch in self.entity:children() do
        local tags = ch:get("Tags")
        local s = tags and tags.tags or ""
        local i, j = string.match(s, "Cell_(%-?%d+)_(%-?%d+)")
        if i then
            self.near[i .. "_" .. j] = { entity = ch, shown = true }
        else
            self.far += 1
        end
    end
    local n = 0
    for _ in self.near do n += 1 end
    Game.world_canopy = { root = self.entity, near = self.near, near_count = n, far_count = self.far,
                          hidden = 0, blocks = n + self.far }
    self:refresh(0)
end

function C:refresh(dt)
    local loaded = {}
    local cs = self.cell_size
    for _, e in scene.tagged("Tree") do
        local p = e.world_position
        loaded[math.floor(p.x / cs) .. "_" .. math.floor(p.z / cs)] = true
    end
    local hidden = 0
    for key, b in self.near do
        if loaded[key] then
            self.seen[key] = (self.seen[key] or 0) + dt
        else
            self.seen[key] = nil
        end
        -- at scene start (a load screen covers it) loaded cells swap at once
        local settle = self.age < 2 and 0 or self.settle
        local want = not (self.seen[key] and self.seen[key] >= settle)
        if want ~= b.shown then
            set_shown(b.entity, want)
            b.shown = want
        end
        if not b.shown then hidden += 1 end
    end
    Game.world_canopy.hidden = hidden
end

function C:update(dt)
    self.t += dt
    self.age += dt
    if self.t >= self.interval or self.age < 2 then
        self:refresh(self.t)
        self.t = 0
    end
end

return C
