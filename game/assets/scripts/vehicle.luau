-- HT-4 "Mule" squad transport: hinged doors, the rear hatch, path driving with wheel spin,
-- steering and sprung chassis motion, and engine/tyre audio. Not player-drivable: missions move it
-- along authored paths (AGENTS.md: no drivable-car system unless a mission needs one).
-- Entity contract: tools/scenes/vehicle.py.
--
--   local v = Game.vehicles["Mule"]
--   v:start_engine()  v:drive({p1, p2, ...}, { speed = 6 })  v:driving()  v:stop_engine()
--   v:set_door("rl", true)  v:door_open("rl")  v:set_hatch(true, by)  v:hatch_amount()
--   v:seat_root(seat)  -> world root position for an occupant of that seat, v:door_point(key)
local Game = require("scripts/lib/game")

local V = {}
V.running = false            -- engine running at scene start (vehicle already idling)
V.hatch_prompt = "Open hatch"
V.hatch_locked = false       -- the trunk scene unlocks the hatch when the squad is ready

V.DOOR_ANGLE = 66
V.DOOR_TIME = 0.75
V.HATCH_ANGLE = -100
V.CARGO_LAMP = 2.2           -- cargo-bay courtesy lamp intensity with the hatch up
V.HATCH_TIME = 1.35
V.WHEEL_R = 0.40
V.WHEELBASE = 3.0
V.SIT_HIP = 0.46             -- seated hip height above the occupant root (Sit clip)

Game.vehicles = Game.vehicles or {}

local DOORS = {
    fl = { sign = -1, out = -1 }, fr = { sign = 1, out = 1 },
    rl = { sign = -1, out = -1 }, rr = { sign = 1, out = 1 },
}

local function smooth(t) t = math.clamp(t, 0, 1); return t * t * (3 - 2 * t) end
local function ease_out(t) t = math.clamp(t, 0, 1); return 1 - (1 - t) * (1 - t) * (1 - t) end
local function wrap(a) return (a + 540) % 360 - 180 end

local function catmull(p0, p1, p2, p3, t)
    local t2, t3 = t * t, t * t * t
    return ((p1 * 2) + (p2 - p0) * t + (p0 * 2 - p1 * 5 + p2 * 4 - p3) * t2 + (p1 * 3 - p0 - p2 * 3 + p3) * t3) * 0.5
end

function V:start()
    local e = self.entity
    local n = e.name
    local function f(suffix) return scene.find(n .. " " .. suffix) end
    self.name = n
    self.chassis = f("Chassis")
    self.doors = {}
    for key, d in DOORS do
        self.doors[key] = { pivot = f("Door " .. string.upper(key)), sign = d.sign, out = d.out, a = 0, want = 0,
                            exit = f("Exit " .. key) }
    end
    self.hatch = { pivot = f("Hatch"), a = 0, want = 0 }
    self.cargo_lamp = f("Cargo Lamp")
    self.wheels = {}
    for _, k in { "FL", "FR", "RL", "RR" } do
        self.wheels[k] = { steer = f("Wheel " .. k), spin = f("Wheel " .. k .. " Spin") }
    end
    self.steering_model = f("Steering Model")
    self.seats = {}
    for _, s in { "driver", "front_right", "rear_left", "rear_middle", "rear_right" } do self.seats[s] = f("Seat " .. s) end
    self.tyres = f("Tyres")
    self.yaw = math.deg(math.atan2(-e.forward.x, -e.forward.z))
    self.spin = 0
    self.steer = 0
    self.speed = 0
    self.accel = 0
    self.pitch, self.pitch_v, self.roll, self.roll_v = 0, 0, 0, 0
    self.engine = self.running and "idle" or "off"
    self.engine_t = 0
    self.engine_vol = self.running and 0.5 or 0
    self.vol_set, self.pitch_set, self.tyre_set = -1, -1, -1
    self.path = nil
    Game.vehicles[n] = self
    self.started_frame = true
    if self.hatch.pivot then
        Game.register_interactable(self.hatch.pivot, self.hatch_prompt, function() self:toggle_hatch(Game.player) end)
        Game.set_interactable(self.hatch.pivot, not self.hatch_locked)
    end
end

-- Doors and hatch ------------------------------------------------------------------------------
function V:set_door(key, open)
    local d = self.doors[key]
    if not d or not d.pivot then return end
    local w = open and 1 or 0
    if d.want == w then return end
    d.want = w
    if open then
        audio.play("audio/vehicle/door_open.wav", { position = d.pivot.world_position, volume = 0.8, bus = "sfx",
                                                    pitch = 0.95 + math.random() * 0.1 })
    end
    Game.emit("vehicle_door", self.name, key, open)
end
function V:door_open(key) local d = self.doors[key]; return d and d.a > 0.97 end
function V:door_closed(key) local d = self.doors[key]; return d and d.a < 0.01 and d.want == 0 end
function V:door_point(key)
    local d = self.doors[key]
    return d and d.exit and d.exit.world_position or self.entity.position
end

function V:set_hatch(open, by)
    local h = self.hatch
    local w = open and 1 or 0
    if h.want == w then return end
    h.want = w
    h.by = by
    if open then
        audio.play("audio/vehicle/hatch_open.wav", { position = h.pivot.world_position, volume = 0.85, bus = "sfx" })
    end
    Game.set_interactable(h.pivot, false)
    Game.emit("vehicle_hatch", self.name, open, by)
end
function V:toggle_hatch(by)
    if self.hatch.a > 0.02 and self.hatch.a < 0.98 then return end
    self:set_hatch(self.hatch.want == 0, by)
end
function V:hatch_amount() return self.hatch.a end
function V:hatch_is_open() return self.hatch.a > 0.98 end
function V:lock_hatch(locked)
    self.hatch_locked = locked
    if self.hatch.pivot and (self.hatch.a < 0.01 or self.hatch.a > 0.99) then
        Game.set_interactable(self.hatch.pivot, not locked, self.hatch.want == 1 and "Close hatch" or self.hatch_prompt)
    end
end

local function step_door(self, d, dt, total)
    if d.a == d.want then return false end
    local rate = dt / total
    local closing = d.want < d.a
    d.a = closing and math.max(d.want, d.a - rate) or math.min(d.want, d.a + rate)
    return closing and d.a == 0
end

-- Seats -----------------------------------------------------------------------------------------
-- World root position for an occupant of `seat` (the Sit clip keeps the hips 0.46 m above the
-- root and 0.06 m behind it).
function V:seat_root(seat)
    local m = self.seats[seat]
    if not m then return self.entity.position end
    local fwd = self.entity.forward
    return m.world_position - vector.create(0, V.SIT_HIP, 0) + vector.create(fwd.x, 0, fwd.z) * 0.06
end
-- Facing yaw (character convention: model faces +Z) of a seated occupant.
function V:seat_yaw() return self.yaw + 180 end
-- Yaw an occupant faces when swinging out through `door`.
function V:door_out_yaw(key)
    local d = self.doors[key]
    local r = self.entity.right
    local dir = vector.create(r.x, 0, r.z) * d.out
    return math.deg(math.atan2(dir.x, dir.z))
end
-- World point at the door sill (where an occupant's hips are before they stand).
function V:sill_root(seat, key)
    local d = self.doors[key]
    local r = self.entity.right
    return self:seat_root(seat) + vector.create(r.x, 0, r.z) * (d.out * 0.32)
end

-- Engine ----------------------------------------------------------------------------------------
function V:start_engine()
    if self.engine ~= "off" then return end
    self.engine = "starting"
    self.engine_t = 0
    audio.play("audio/vehicle/engine_start.wav", { position = self.entity.position, volume = 0.9, bus = "sfx" })
    Game.emit("vehicle_engine", self.name, "start")
end
function V:stop_engine()
    if self.engine == "off" then return end
    self.engine = "off"
    self.path = nil
    audio.play("audio/vehicle/engine_stop.wav", { position = self.entity.position, volume = 0.85, bus = "sfx" })
    Game.emit("vehicle_engine", self.name, "stop")
end
function V:engine_on() return self.engine == "idle" end

-- Path driving ----------------------------------------------------------------------------------
-- points: world positions on the ground (the vehicle root follows them); the current position is
-- prepended. opts: speed (m/s), accel, decel.
function V:drive(points, opts)
    opts = opts or {}
    local pts = { self.entity.position }
    for _, p in points do table.insert(pts, p) end
    local samples = { pts[1] }
    local n = #pts
    for i = 1, n - 1 do
        local p0 = pts[math.max(1, i - 1)]
        local p1, p2 = pts[i], pts[i + 1]
        local p3 = pts[math.min(n, i + 2)]
        local seg = vector.magnitude(p2 - p1)
        local steps = math.max(4, math.ceil(seg / 0.5))
        for s = 1, steps do table.insert(samples, catmull(p0, p1, p2, p3, s / steps)) end
    end
    local cum = { 0 }
    for i = 2, #samples do cum[i] = cum[i - 1] + vector.magnitude(samples[i] - samples[i - 1]) end
    self.path = { pts = samples, cum = cum, len = cum[#cum], s = 0, vmax = opts.speed or 6,
                  accel = opts.accel or 1.8, decel = opts.decel or 1.5 }
    self.speed = 0
end
function V:driving() return self.path ~= nil end

local function sample(path, s)
    local cum, pts = path.cum, path.pts
    s = math.clamp(s, 0, path.len)
    local lo, hi = 1, #cum
    while hi - lo > 1 do
        local mid = (lo + hi) // 2
        if cum[mid] <= s then lo = mid else hi = mid end
    end
    local span = cum[hi] - cum[lo]
    local t = span > 1e-6 and (s - cum[lo]) / span or 0
    return pts[lo] + (pts[hi] - pts[lo]) * t
end

function V:step_drive(dt)
    local p = self.path
    local remaining = p.len - p.s
    local v_cap = math.min(p.vmax, math.sqrt(2 * p.decel * math.max(0, remaining)))
    local v0 = self.speed
    if self.speed < v_cap then self.speed = math.min(v_cap, self.speed + p.accel * dt)
    else self.speed = math.max(v_cap, self.speed - p.decel * 1.5 * dt) end
    if remaining > 0.03 and self.speed < 0.18 then self.speed = 0.18 end
    self.accel = (self.speed - v0) / math.max(dt, 1e-4)
    local ds = self.speed * dt
    p.s = math.min(p.len, p.s + ds)
    local pos = sample(p, p.s)
    local ahead = sample(p, p.s + 1.4)
    local behind = sample(p, p.s - 1.4)
    local d = ahead - behind
    local yaw = self.yaw
    if d.x * d.x + d.z * d.z > 1e-4 then yaw = math.deg(math.atan2(-d.x, -d.z)) end
    local dyaw = wrap(yaw - self.yaw)
    -- steering from path curvature (bicycle model), smoothed
    local curv = ds > 1e-4 and math.rad(dyaw) / ds or 0
    local want_steer = math.clamp(math.deg(math.atan(V.WHEELBASE * curv)), -32, 32)
    if ds > 1e-4 then self.steer = Game.damp(self.steer, want_steer, 6, dt) end
    self.lat = self.speed * self.speed * curv
    self.yaw = yaw
    local flat = math.sqrt(d.x * d.x + d.z * d.z)
    self.grade = flat > 1e-3 and math.deg(math.atan2(d.y, flat)) or 0
    self.entity.position = pos
    self.entity.rotation = vector.create(self.grade, self.yaw, 0)
    self.spin = (self.spin - math.deg(ds / V.WHEEL_R)) % 360
    if p.s >= p.len - 1e-3 then
        self.path = nil
        self.speed = 0
        self.accel = -2.5 -- the last bit of braking: the body pitches forward and settles
        Game.emit("vehicle_parked", self.name)
    end
end

function V:update(dt)
    if Game.paused then return end
    if self.path then self:step_drive(dt) else self.accel = Game.damp(self.accel, 0, 10, dt); self.lat = 0 end
    -- wheels and steering wheel
    for k, w in self.wheels do
        if w.spin then w.spin.rotation = vector.create(self.spin, 0, 0) end
        if w.steer and (k == "FL" or k == "FR") then w.steer.rotation = vector.create(0, self.steer, 0) end
    end
    if self.steering_model then self.steering_model.rotation = vector.create(0, 0, -self.steer * 9) end
    -- sprung chassis: squat/dive with longitudinal acceleration, roll in turns
    local tp = math.clamp(self.accel * 0.55, -2.2, 1.6)
    local tr = math.clamp(-(self.lat or 0) * 0.45, -2.0, 2.0)
    self.pitch_v += ((tp - self.pitch) * 70 - self.pitch_v * 7) * dt
    self.pitch += self.pitch_v * dt
    self.roll_v += ((tr - self.roll) * 60 - self.roll_v * 7) * dt
    self.roll += self.roll_v * dt
    local idle_shake = (self.engine == "idle" or self.engine == "starting") and math.sin(time.now() * 58) * 0.035 or 0
    if self.chassis then self.chassis.rotation = vector.create(self.pitch + idle_shake, 0, self.roll) end
    -- doors and hatch
    for key, d in self.doors do
        if d.pivot and step_door(self, d, dt, V.DOOR_TIME) then
            audio.play("audio/vehicle/door_close.wav", { position = d.pivot.world_position, volume = 0.9, bus = "sfx",
                                                         pitch = 0.95 + math.random() * 0.1 })
        end
        if d.pivot then
            local s = d.want == 1 and ease_out(d.a) or smooth(d.a)
            d.pivot.rotation = vector.create(0, d.sign * V.DOOR_ANGLE * s, 0)
        end
    end
    local h = self.hatch
    if h.pivot then
        local before = h.a
        local closed = step_door(self, h, dt, V.HATCH_TIME)
        -- gas struts: quick first lift, slow finish; closing is a pull then a drop
        local s = h.want == 1 and ease_out(h.a) or smooth(h.a)
        h.pivot.rotation = vector.create(V.HATCH_ANGLE * s, 0, 0)
        -- cargo lamp: switched by the hatch, warms up over the first part of the lift
        if self.cargo_lamp then
            local li = V.CARGO_LAMP * math.clamp(h.a * 3, 0, 1)
            if li ~= self.lamp_i then
                local l = self.cargo_lamp:get("Light")
                if l then l.intensity = li; self.cargo_lamp:set("Light", l) end
                self.lamp_i = li
            end
        end
        if closed then
            audio.play("audio/vehicle/hatch_close.wav", { position = h.pivot.world_position, volume = 0.9, bus = "sfx" })
        end
        if before ~= h.a and (h.a == 1 or h.a == 0) then
            Game.set_interactable(h.pivot, not self.hatch_locked, h.a == 1 and "Close hatch" or self.hatch_prompt)
            Game.emit(h.a == 1 and "vehicle_hatch_opened" or "vehicle_hatch_closed", self.name, h.by)
        end
    end
    -- engine
    self.engine_t += dt
    if self.engine == "starting" and self.engine_t > 0.95 then self.engine = "idle" end
    local throttle = math.clamp(self.accel / 2, 0, 1)
    local want_vol = 0
    if self.engine == "idle" then want_vol = 0.48 + throttle * 0.22 + math.min(self.speed, 8) * 0.02 end
    if self.engine == "starting" then want_vol = self.engine_t > 0.6 and 0.4 or 0 end
    self.engine_vol = Game.damp(self.engine_vol, want_vol, self.engine == "off" and 9 or 4, dt)
    local want_pitch = 0.9 + math.min(self.speed, 9) * 0.045 + throttle * 0.08
    if math.abs(self.engine_vol - self.vol_set) > 0.01 or math.abs(want_pitch - self.pitch_set) > 0.01 then
        self.vol_set, self.pitch_set = self.engine_vol, want_pitch
        self.entity:set("AudioSource", { volume = self.engine_vol, pitch = want_pitch })
    end
    if self.tyres then
        local tv = math.clamp(self.speed / 6, 0, 1) * 0.55
        if math.abs(tv - self.tyre_set) > 0.01 then
            self.tyre_set = tv
            self.tyres:set("AudioSource", { volume = tv, pitch = 0.85 + math.min(self.speed, 9) * 0.04 })
        end
    end
end

function V:save_state()
    return { hatch = self.hatch.want, engine = self.engine == "off" and "off" or "idle",
             doors = { fl = self.doors.fl.want, fr = self.doors.fr.want, rl = self.doors.rl.want, rr = self.doors.rr.want } }
end
function V:load_state(s)
    if not s then return end
    self.hatch.want = s.hatch or 0; self.hatch.a = self.hatch.want
    for k, w in (s.doors or {}) do if self.doors[k] then self.doors[k].want = w; self.doors[k].a = w end end
    self.engine = s.engine or "off"
end

return V
