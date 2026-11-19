-- Dialogue scheduler: one voice at a time, priorities, cooldowns, subtitles with speaker names,
-- spatial voices from the speaker's head (radio lines and absent speakers play flat on the voice
-- bus), lip sync and listener eye-lines.
--
--   Dialogue.register(key, actor)   actor = { entity, voice (entity with AudioSource), face,
--                                             look_at = fn(point|nil), talk = fn(bool) }
--   Dialogue.say(id, opts)          queue one line. opts.priority: 0 bark, 1 chatter, 2 story,
--                                   3 cinematic; opts.to = listener key; opts.ttl (s) to give up;
--                                   opts.interrupt = true cuts a lower-priority line
--   Dialogue.conversation(ids, opts) queue lines in order with natural gaps; opts.done callback
--   Dialogue.bark(kind, opts)       picks a rotating variant of bark_<kind>_N from present speakers
--   Dialogue.busy(), Dialogue.current(), Dialogue.clear(min_priority)
--   Dialogue.update(dt)             advanced by scripts/dialogue_runner.luau (stops while paused)
local Game = require("scripts/lib/game")
local V = require("scripts/lib/voice_data")

local Dialogue = {}
Dialogue.lines = V

local st = nil
local function state()
    local cur = scene.current()
    if not st or st.scene ~= cur then
        st = { scene = cur, actors = {}, queue = {}, cur = nil, clock = 0, gap = 0, last_said = {},
               last_kind = {}, log = {}, seq = 0, radio = nil }
        st.radio = scene.find("Radio Voice")
        Dialogue.log = st.log
    end
    return st
end
Dialogue.state = state

function Dialogue.register(key, actor)
    state().actors[key] = actor
end
function Dialogue.unregister(key)
    state().actors[key] = nil
end
function Dialogue.actor(key) return state().actors[key] end

local function push(item)
    local s = state()
    s.seq += 1
    item.seq = s.seq
    item.queued = s.clock
    table.insert(s.queue, item)
    table.sort(s.queue, function(a, b)
        if a.priority ~= b.priority then return a.priority > b.priority end
        return a.seq < b.seq
    end)
    if item.interrupt and s.cur and s.cur.priority < item.priority then Dialogue.stop_current() end
end

function Dialogue.say(id, opts)
    opts = opts or {}
    local line = V[id]
    if not line then
        print("dialogue: unknown line " .. tostring(id))
        return false
    end
    local s = state()
    local cooldown = opts.cooldown or (opts.priority or 1) < 2 and 30 or 0
    local last = s.last_said[id]
    if last and s.clock - last < cooldown then return false end
    push({ id = id, line = line, priority = opts.priority or 1, to = opts.to, ttl = opts.ttl,
           interrupt = opts.interrupt, gap = opts.gap or 0.3, done = opts.done, group = opts.group })
    return true
end

function Dialogue.conversation(ids, opts)
    opts = opts or {}
    local s = state()
    s.seq += 1
    local group = "conv" .. s.seq
    -- drop lines missing from voice_data (a stale render) so `done` still fires on the last one
    local known = {}
    for _, entry in ids do
        local id = type(entry) == "table" and entry[1] or entry
        if V[id] then table.insert(known, entry) else print("dialogue: unknown line " .. tostring(id)) end
    end
    ids = known
    local n = #ids
    if n == 0 then
        if opts.done then opts.done() end
        return group
    end
    for i, entry in ids do
        local id, to = entry, nil
        if type(entry) == "table" then id, to = entry[1], entry.to end
        Dialogue.say(id, { priority = opts.priority or 2, to = to, gap = opts.gap or 0.35, group = group,
                           cooldown = 0, done = (i == n) and opts.done or nil, interrupt = (i == 1) and opts.interrupt })
    end
    return group
end

-- Barks: variants rotate and a kind is not repeated within its cooldown.
function Dialogue.bark(kind, opts)
    opts = opts or {}
    local s = state()
    local kc = opts.cooldown or 6
    if s.last_kind[kind] and s.clock - s.last_kind[kind] < kc then return false end
    if s.cur and s.cur.priority >= 2 then return false end
    local best, best_t = nil, math.huge
    for i = 1, 9 do
        local id = (opts.prefix or "bark_") .. kind .. "_" .. i
        local l = V[id]
        if not l then break end
        local a = s.actors[l.s]
        local present = l.r or (a and a.entity and a.entity.valid and (not a.can_speak or a.can_speak()))
        if present and (not opts.speaker or opts.speaker == l.s) then
            local t = s.last_said[id] or -1000
            if t < best_t then best, best_t = id, t end
        end
    end
    if not best then return false end
    s.last_kind[kind] = s.clock
    return Dialogue.say(best, { priority = 0, ttl = opts.ttl or 1.5, cooldown = 0, to = opts.to })
end

function Dialogue.busy()
    local s = state()
    return s.cur ~= nil or #s.queue > 0
end
function Dialogue.current() return state().cur end

function Dialogue.clear(min_priority)
    local s = state()
    local keep = {}
    for _, q in s.queue do
        if q.priority >= (min_priority or 99) then table.insert(keep, q) end
    end
    s.queue = keep
end

local function source_for(s, line)
    local a = s.actors[line.s]
    if not line.r and a and a.voice and a.voice.valid and a.entity.valid then
        local cam = Game.camera
        if not cam or vector.magnitude(a.entity.world_position - cam.world_position) < 45 then
            return a.voice, a
        end
    end
    return s.radio, a
end

function Dialogue.stop_current()
    local s = state()
    local c = s.cur
    if not c then return end
    if c.src and c.src.valid then c.src:stop_audio() end
    if c.actor then
        if c.actor.face then c.actor.face:speak(nil) end
        if c.actor.talk then c.actor.talk(false) end
    end
    c.log.stop = s.clock
    c.log.cut = true
    s.cur = nil
    Game.clear_subtitle()
end

local function start(s, item)
    local line = item.line
    local src, actor = source_for(s, line)
    item.src = src
    item.actor = actor
    item.t = 0
    s.last_said[item.id] = s.clock
    if src then
        src:set("AudioSource", { clip = "audio/voice/" .. item.id .. ".ogg" })
        src:play_audio()
    else
        audio.play("audio/voice/" .. item.id .. ".ogg", { bus = "voice", priority = 200 })
    end
    if Game.settings.subtitles then Game.show_subtitle(line.n, line.t, line.d + 0.25) end
    if actor then
        if actor.face then actor.face:speak(line) end
        if actor.talk and line.d > 2.2 and item.priority >= 1 then actor.talk(true) end
    end
    item.log = { id = item.id, speaker = line.s, start = s.clock, stop = nil, priority = item.priority }
    table.insert(s.log, item.log)
    s.cur = item
    Game.emit("dialogue_line", item.id, line.s)
end

-- Eye-lines: the speaker looks at the listener (or the player), others nearby look at the speaker.
local function eyelines(s, item)
    local line = item.line
    local spk = s.actors[line.s]
    local spk_pos = spk and spk.entity.valid and (spk.entity.world_position + vector.create(0, 1.6, 0))
    local to = item.to and s.actors[item.to]
    local listen_pos
    if to and to.entity.valid then
        listen_pos = to.entity.world_position + vector.create(0, 1.6, 0)
    elseif Game.camera then
        listen_pos = Game.camera.world_position
    end
    if spk and spk.look_at and listen_pos then spk.look_at(listen_pos) end
    if spk_pos then
        for key, a in s.actors do
            if key ~= line.s and a.look_at and a.entity.valid then
                if vector.magnitude(a.entity.world_position - spk.entity.world_position) < 14 then
                    a.look_at(spk_pos)
                end
            end
        end
    end
end

function Dialogue.update(dt)
    local s = state()
    local paused = Game.paused
    if s.cur and s.cur.src and s.cur.src.valid then
        if paused and not s.cur.paused then s.cur.src:pause_audio(true); s.cur.paused = true end
        if not paused and s.cur.paused then s.cur.src:pause_audio(false); s.cur.paused = false end
    end
    if paused then return end
    s.clock += dt
    local c = s.cur
    if c then
        c.t += dt
        eyelines(s, c)
        if c.t >= c.line.d then
            if c.actor then
                if c.actor.talk then c.actor.talk(false) end
            end
            c.log.stop = s.clock
            s.cur = nil
            s.gap = c.gap
            if c.done then c.done() end
            Game.emit("dialogue_done", c.id)
        end
        return
    end
    if s.gap > 0 then
        s.gap -= dt
        return
    end
    -- next line: drop stale barks, start the most important
    while #s.queue > 0 do
        local item = table.remove(s.queue, 1)
        if not item.ttl or s.clock - item.queued <= item.ttl then
            start(s, item)
            return
        end
    end
end

return Dialogue
