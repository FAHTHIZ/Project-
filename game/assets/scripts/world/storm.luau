-- Storm over Kestrel Valley (tools/world/night.py). Lightning: every `min_gap`..`max_gap`
-- seconds a flash sequence drives the "Lightning" directional light (child of this entity)
-- through two or three strokes; thunder follows after the distance delay (sound travels
-- ~340 m/s, the strike is 0.6-4 km away). The Environment's exposure is untouched, so the
-- flash reads as a real light: wet ground and trunks catch it, then the night returns.
-- Missions can call Game.storm.strike(distance_km) for a scripted beat.
local Game = require("scripts/lib/game")

local S = {}
S.min_gap = 22
S.max_gap = 70
S.peak = 5.5
S.first = 9
S.volume = 1.0   -- interiors hear the thunder through the structure (0.3-0.5)

local THUNDER = { "audio/ambient/thunder_0.wav", "audio/ambient/thunder_1.wav", "audio/ambient/thunder_2.wav" }

function S:start()
    self.light = self.entity:find_child("Lightning")
    self.t = 0
    self.next = self.first
    self.flash = nil
    self.thunder = {}
    Game.storm = { strike = function(km) self:strike(km) end, strikes = 0 }
end

function S:strike(km)
    km = km or (0.6 + math.random() * 3.4)
    -- stroke pattern: { start, length, brightness } (seconds, 0..1)
    local seq = { { 0, 0.07, 1.0 }, { 0.11, 0.05, 0.45 } }
    if math.random() < 0.6 then table.insert(seq, { 0.2 + math.random() * 0.12, 0.09, 0.8 }) end
    local scale = math.clamp(1.6 - km * 0.3, 0.35, 1.3)
    self.flash = { t = 0, seq = seq, scale = scale }
    table.insert(self.thunder, { t = km * 1000 / 340, km = km })
    Game.storm.strikes += 1
end

function S:set(i)
    local l = self.light
    if not (l and l.valid) then return end
    local c = l:get("Light")
    if c then c.intensity = i; l:set("Light", c) end
end

function S:update(dt)
    self.t += dt
    if self.t >= self.next then
        self.t = 0
        self.next = self.min_gap + math.random() * (self.max_gap - self.min_gap)
        self:strike()
    end
    local f = self.flash
    if f then
        f.t += dt
        local v, live = 0, false
        for _, s in f.seq do
            local u = (f.t - s[1]) / s[2]
            if u < 1.6 then live = true end
            if u >= 0 and u < 1.6 then
                v = math.max(v, s[3] * (u < 1 and 1 or (1.6 - u) / 0.6))
            end
        end
        self:set(v * self.peak * f.scale)
        if not live then self.flash = nil; self:set(0) end
    end
    for i = #self.thunder, 1, -1 do
        local th = self.thunder[i]
        th.t -= dt
        if th.t <= 0 then
            table.remove(self.thunder, i)
            local vol = math.clamp(1.15 - th.km * 0.2, 0.3, 1.0)
            audio.play(THUNDER[math.random(1, #THUNDER)], { bus = "ambient", volume = vol * self.volume, pitch = 0.9 + math.random() * 0.2 })
        end
    end
end

return S
