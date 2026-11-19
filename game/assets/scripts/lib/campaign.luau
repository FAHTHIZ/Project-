-- SPECIAL OPS campaign order. Each chapter is one scene; finishing it unlocks the next.
local Game = require("scripts/lib/game")

local Campaign = {}

Campaign.chapters = {
    { id = "prologue", title = "Prologue: Orders Before Dawn", subtitle = "Route 9 lay-by, 02:40", scene = "scenes/prologue.vscene" },
    { id = "op01", title = "Operation 01: Green Silence", subtitle = "Kestrel woods, 03:05", scene = "scenes/op01_forest.vscene" },
    { id = "op02", title = "Operation 02: Dead Ground", subtitle = "The perimeter, 03:40", scene = "scenes/op02_perimeter.vscene" },
    { id = "op03", title = "Operation 03: Hard Entry", subtitle = "Kestrel Station, 04:05", scene = "scenes/op03_approach.vscene" },
    { id = "op04", title = "Operation 04: The Paper War", subtitle = "Records and labs, 04:20", scene = "scenes/op04_interior.vscene" },
    { id = "op05", title = "Operation 05: Below the Line", subtitle = "The bunker, 04:45", scene = "scenes/op05_bunker.vscene" },
    { id = "op06", title = "Operation 06: The Source Vault", subtitle = "The lower archive, 05:10", scene = "scenes/op06_basement.vscene" },
    { id = "op07", title = "Operation 07: V-01", subtitle = "The review chamber, 05:30", scene = "scenes/op07_chamber.vscene" },
    { id = "epilogue", title = "Epilogue: First Light", subtitle = "Forestry lay-by, 05:52", scene = "scenes/epilogue.vscene" },
    { id = "credits", title = "Credits", subtitle = "", scene = "scenes/credits.vscene" },
}

function Campaign.index(id)
    for i, c in Campaign.chapters do if c.id == id then return i end end
    return nil
end

function Campaign.get(id)
    local i = Campaign.index(id)
    return i and Campaign.chapters[i] or nil
end

-- Loads a chapter's scene and records it as the current one.
function Campaign.start(id, fresh)
    local c = Campaign.get(id)
    if not c then return false end
    local p = Game.progress()
    p.op = id
    p.unlocked[id] = true
    if fresh then p.checkpoint = nil end
    Game.save_progress()
    Game.paused = false
    Game.cinematic = false
    scene.load(c.scene)
    return true
end

-- Marks the chapter complete, unlocks and loads the next.
function Campaign.complete(id)
    local i = Campaign.index(id)
    local p = Game.progress()
    p.completed = p.completed or {}
    p.completed[id] = true
    p.checkpoint = nil
    local nxt = i and Campaign.chapters[i + 1]
    if nxt then
        p.unlocked[nxt.id] = true
        p.op = nxt.id
        Game.save_progress()
        Campaign.start(nxt.id, true)
    else
        Game.save_progress()
        scene.load("scenes/menu.vscene")
    end
end

return Campaign
