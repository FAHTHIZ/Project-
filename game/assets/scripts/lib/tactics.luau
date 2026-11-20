-- Tactical position search for Greyline contractors (and anyone else who needs it).
--
-- There are no authored cover nodes in Kestrel Valley. Cover is whatever actually stops a pulse:
-- terrain folds, tree trunks, rocks, logs, vehicles, walls. This samples candidate points around
-- a fighter and keeps the ones where a line from the threat's eyes to a crouched chest is blocked
-- by a real collider, preferring spots where standing up clears the obstacle (a firing position,
-- not a hole). Everything is physics.raycast against the same colliders the shots use.
--
--   Tactics.ground(p, ignore)              ground point under x,z (terrain height or a ray down)
--   Tactics.exposed(threat_eye, p, ignore) true if a crouched chest at p is in the open
--   Tactics.can_peek(threat_eye, p, ignore) true if standing at p clears the cover
--   Tactics.clear_shot(from, to, ignore, near) true if nothing solid is near the muzzle on the line
--   Tactics.find_cover(me, threat, opts)   best cover point near me against threat, or nil
--   Tactics.flank_point(me, threat, side)  a point off to one side of the threat (side = 1/-1)
--   Tactics.search_points(center, n, r)    walkable points around center for a sweep
local Tactics = {}

local UP = vector.create(0, 1, 0)
local CROUCH = 0.95     -- chest height when crouched behind cover
local STAND = 1.55      -- eye/weapon height standing (a peek)

local function flat(v) return vector.create(v.x, 0, v.z) end

function Tactics.ground(p, ignore)
    local ok, h = pcall(function() return terrain.height(p.x, p.z) end)
    local best = nil
    if ok and h then best = h end
    -- props and floors above the terrain (interiors, decks) win over the terrain under them
    local hit = physics.raycast(vector.create(p.x, (best or p.y) + 4, p.z), vector.create(0, -1, 0), 10, nil, ignore)
    if hit and hit.normal and hit.normal.y > 0.7 then
        if not best or hit.point.y > best - 0.05 then best = hit.point.y end
    end
    if not best then return nil end
    return vector.create(p.x, best, p.z)
end

-- Is something solid between the threat's eye and a point at height `above` over p?
local function blocked(eye, p, above, ignore)
    local target = p + UP * above
    local d = target - eye
    local dist = vector.magnitude(d)
    if dist < 0.5 then return false end
    local dir = d / dist
    local from, left = eye, dist - 0.35
    -- people are not cover: step through capsules (the threat's own, a colleague's) up to twice
    for _ = 1, 3 do
        local hit = physics.raycast(from, dir, left, nil, ignore)
        if not hit then return false end
        if not (hit.entity and hit.entity.valid and hit.entity:has("CharacterController")) then return true end
        local step = hit.distance + 0.7
        from += dir * step
        left -= step
        if left <= 0 then return false end
    end
    return false
end

function Tactics.exposed(eye, p, ignore)
    return not blocked(eye, p, CROUCH, ignore)
end

-- Can someone standing at p see (and so shoot) the threat over whatever covers them?
function Tactics.can_peek(eye, p, ignore)
    return not blocked(eye, p, STAND, ignore)
end

-- Is the straight line from a muzzle to an aim point clear of world geometry?
-- near: only count obstacles within this many metres of the muzzle (your own rock, not the cover
-- the target is hiding behind).
function Tactics.clear_shot(from, to, ignore, near)
    local d = to - from
    local dist = vector.magnitude(d)
    if dist < 1 then return true end
    local hit = physics.raycast(from, d / dist, math.min(dist - 0.6, near or math.huge), nil, ignore)
    if not hit then return true end
    return hit.entity and hit.entity.valid and hit.entity:has("CharacterController") or false
end

local function snap(p, ignore)
    local g = Tactics.ground(p, ignore)
    if not g then return nil end
    if nav.available() then
        local n = nav.nearest(g, vector.create(1.5, 3, 1.5))
        if n then
            if vector.magnitude(flat(n - g)) > 1.4 then return nil end
            g = n
        end
    end
    return g
end

-- opts: radius (max move, default 9), min_threat (keep at least this far from the threat, 6),
-- max_threat (do not end up further than this, 40), samples (18), ignore (entity), avoid (list of
-- points other fighters already claimed), bias (vector: prefer moving this way, e.g. a flank).
function Tactics.find_cover(me, threat, opts)
    opts = opts or {}
    local radius = opts.radius or 9
    local samples = opts.samples or 18
    local eye = threat + UP * STAND
    local ignore = opts.ignore
    local to_t = flat(threat - me)
    local dt = vector.magnitude(to_t)
    if dt < 0.1 then return nil end
    local fwd = to_t / dt
    local best, best_score = nil, -1e9
    local base = math.random() * math.pi * 2
    for i = 1, samples do
        local ang = base + (i / samples) * math.pi * 2
        local r = radius * (0.35 + 0.65 * ((i * 0.618) % 1))
        local c = me + vector.create(math.cos(ang) * r, 0, math.sin(ang) * r)
        local p = snap(c, ignore)
        if p then
            local dthreat = vector.magnitude(flat(threat - p))
            if dthreat >= (opts.min_threat or 6) and dthreat <= (opts.max_threat or 40)
                and blocked(eye, p, CROUCH, ignore) then
                local score = 10
                -- a peek spot: standing clears the obstacle, so they can fight from it
                if not blocked(eye, p, STAND, ignore) then score += 6 end
                -- shorter dashes are safer; running toward the threat is worse than sideways
                local move = flat(p - me)
                local ml = vector.magnitude(move)
                score -= ml * 0.6
                if ml > 0.1 then
                    local toward = vector.dot(move / ml, fwd)
                    score -= math.max(0, toward) * 2.5
                    if opts.bias then score += vector.dot(move / ml, opts.bias) * 5 end
                end
                -- the run itself should not be a long walk across open ground
                local mid = (me + p) * 0.5
                if not blocked(eye, mid, CROUCH, ignore) then score -= 1.5 end
                for _, q in opts.avoid or {} do
                    if vector.magnitude(flat(q - p)) < 2.5 then score -= 8 end
                end
                if score > best_score then best, best_score = p, score end
            end
        end
    end
    return best, best_score
end

-- A point beside the threat, roughly perpendicular to the current line of fire.
function Tactics.flank_point(me, threat, side, dist)
    local to_me = flat(me - threat)
    local l = vector.magnitude(to_me)
    if l < 0.1 then return nil end
    to_me = to_me / l
    local a = math.rad(70) * (side or 1)
    local dir = vector.create(to_me.x * math.cos(a) - to_me.z * math.sin(a), 0, to_me.x * math.sin(a) + to_me.z * math.cos(a))
    return snap(threat + dir * (dist or math.clamp(l * 0.8, 10, 18)), nil)
end

function Tactics.search_points(center, n, r)
    local pts = {}
    local base = math.random() * math.pi * 2
    for i = 1, n do
        local a = base + i * (math.pi * 2 / n) + (math.random() - 0.5) * 0.6
        local rr = (r or 8) * (0.6 + math.random() * 0.4)
        local p = snap(center + vector.create(math.cos(a) * rr, 0, math.sin(a) * rr), nil)
        if p then table.insert(pts, p) end
    end
    return pts
end

return Tactics
