-- Render aid for cinematic review (tools/test/cine_shots.py): holds a cutscene's playhead at `t`
-- seconds once it is playing, so a short capture shows that moment of the shot.
local Game = require("scripts/lib/game")
local P = {}
P.id = "arrival"
P.t = 0
function P:update(dt)
    local c = Game.cinematics and Game.cinematics[self.id]
    if c and c:playing() then
        c.entity:seek_sequence(self.t)
        -- seeking fires no events: lift the opening fade the timeline would have cleared
        if Game.present then Game.present.fade = 0 end
    end
end
return P
