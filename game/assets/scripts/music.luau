-- Adaptive score and ambience for a scene (tools/audio/build_music.py writes the cues).
--
-- Children (built by the scene tools): "Explore" and "Tension" AudioSources on the music bus with
-- clips of equal length and tempo, started together so they stay in step; "Cue" plays one-shot
-- cues (briefing, ridge, reveal) with the layers ducked; "Bed" is the ambient room tone.
--
-- Combat intensity rises while any Greyline contractor within `radius` is alerted (enemy state
-- other than patrol) and falls back over `calm_time` seconds after the last one goes quiet or
-- down, so the tension layer does not flap on and off between shots.
--
--   Game.music_cue("audio/music/reveal.ogg", seconds)   one-shot cue (layers duck under it)
--   Game.music_mute(true|false)                          silence the layers (cutscenes that score themselves)
--   Game.set_ambience("audio/ambient/forest.wav")        swap the room tone with a crossfade
local Game = require("scripts/lib/game")
local Squad = require("scripts/lib/squad")

local Mu = {}
Mu.level = 0.55         -- explore layer volume
Mu.tension_level = 0.7
Mu.radius = 70
Mu.calm_time = 9.0
Mu.bed_level = 0.6
-- "x,z,r,clip;..." areas where the room tone changes (first match wins, else the Bed's own clip)
Mu.zones = ""

local function parse_zones(s)
    local out = {}
    for item in string.gmatch(s, "[^;]+") do
        local x, z, r, clip = string.match(item, "([%-%d%.]+),([%-%d%.]+),([%d%.]+),(.+)")
        if x then table.insert(out, { x = tonumber(x), z = tonumber(z), r = tonumber(r), clip = clip }) end
    end
    return out
end

local function src_volume(e, v)
    if not e then return end
    e:set("AudioSource", { volume = v })
end

function Mu:start()
    self.explore = self.entity:find_child("Explore")
    self.tension = self.entity:find_child("Tension")
    self.cue = self.entity:find_child("Cue")
    self.bed = self.entity:find_child("Bed")
    self.zones = parse_zones(self.zones)
    self.t = 0
    self.intensity = 0
    self.calm = 0
    self.duck = 0
    self.cue_t = 0
    self.muted = false
    self.started = false
    self.bed_clip = self.bed and self.bed:get("AudioSource").clip or ""
    self.bed_default = self.bed_clip
    self.bed_fade = 1
    self.bed_next = nil
    Game.music_cue = function(clip, seconds)
        if not self.cue then return end
        self.cue:set("AudioSource", { clip = clip, loop = false })
        self.cue:play_audio()
        self.cue_t = seconds or 12
    end
    Game.music_mute = function(on) self.muted = on end
    Game.set_ambience = function(clip) self:want_bed(clip) end
    -- switch both layers to another area's cues (restarted together so they stay in step)
    Game.music_area = function(area)
        if area == self.area then return end
        self.area = area
        if self.explore then
            self.explore:set("AudioSource", { clip = "audio/music/" .. area .. "_explore.ogg" })
            self.explore:play_audio()
        end
        if self.tension then
            self.tension:set("AudioSource", { clip = "audio/music/" .. area .. "_tension.ogg" })
            self.tension:play_audio()
        end
    end
end

function Mu:want_bed(clip)
    if clip == self.bed_clip or clip == self.bed_next then return end
    self.bed_next = clip
end

function Mu:combat_now()
    local p = Game.player and Game.player.position
    if not p then return false end
    for _, e in Squad.active_enemies() do
        if e.state ~= "patrol" and e.entity.valid then
            local d = e.entity.position - p
            if d.x * d.x + d.z * d.z < self.radius * self.radius then return true end
        end
    end
    return false
end

function Mu:update(dt)
    if not self.started then
        self.started = true
        if self.explore then self.explore:play_audio() end
        if self.tension then
            src_volume(self.tension, 0)
            self.tension:play_audio()
        end
        if self.bed then self.bed:play_audio() end
    end
    -- intensity: fast attack, slow release after a calm period
    if self:combat_now() then
        self.calm = self.calm_time
    else
        self.calm = math.max(0, self.calm - dt)
    end
    local want = self.calm > 0 and 1 or 0
    local rate = want > self.intensity and 0.8 or 0.12
    self.intensity = math.clamp(self.intensity + (want - self.intensity) * math.min(1, dt * rate * 3), 0, 1)
    Game.music_intensity = self.intensity
    -- cue ducking
    if self.cue_t > 0 then self.cue_t -= dt end
    local duck_want = (self.cue_t > 0 or self.muted) and 1 or 0
    self.duck += (duck_want - self.duck) * math.min(1, dt * 1.5)
    local base = (1 - self.duck)
    src_volume(self.explore, self.level * base * (1 - 0.45 * self.intensity))
    src_volume(self.tension, self.tension_level * base * self.intensity)
    -- ambience zones
    if #self.zones > 0 and Game.player then
        local p = Game.player.position
        local clip = self.bed_default
        for _, z in self.zones do
            local dx, dz = p.x - z.x, p.z - z.z
            if dx * dx + dz * dz < z.r * z.r then clip = z.clip; break end
        end
        self:want_bed(clip)
    end
    if self.bed then
        if self.bed_next then
            self.bed_fade = math.max(0, self.bed_fade - dt / 1.5)
            if self.bed_fade <= 0 then
                self.bed:set("AudioSource", { clip = self.bed_next, loop = true })
                self.bed:play_audio()
                self.bed_clip = self.bed_next
                self.bed_next = nil
            end
        else
            self.bed_fade = math.min(1, self.bed_fade + dt / 1.5)
        end
        src_volume(self.bed, self.bed_level * self.bed_fade)
    end
end

return Mu
