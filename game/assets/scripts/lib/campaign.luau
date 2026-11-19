-- SPECIAL OPS campaign order. Each chapter is one scene; finishing it unlocks the next.
local Game = require("scripts/lib/game")

local Campaign = {}

Campaign.chapters = {
    { id = "prologue", title = "Prologue: Lantern", subtitle = "Briefing and deployment", scene = "scenes/prologue.vscene" },
    { id = "op01", title = "Operation 01: Greenline", subtitle = "Forest approach", scene = "scenes/op01_forest.vscene" },
    { id = "op02", title = "Operation 02: Fenceline", subtitle = "The perimeter", scene = "scenes/op02_perimeter.vscene" },
    { id = "op03", title = "Operation 03: Service Yard", subtitle = "Facility approach", scene = "scenes/op03_approach.vscene" },
    { id = "op04", title = "Operation 04: Quiet Rooms", subtitle = "Facility interior", scene = "scenes/op04_interior.vscene" },
    { id = "op05", title = "Operation 05: Deep Store", subtitle = "The bunker", scene = "scenes/op05_bunker.vscene" },
    { id = "op06", title = "Operation 06: Undercroft", subtitle = "The lower basement", scene = "scenes/op06_basement.vscene" },
    { id = "op07", title = "Operation 07: The Chair", subtitle = "VICTUS chamber", scene = "scenes/op07_chamber.vscene" },
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
