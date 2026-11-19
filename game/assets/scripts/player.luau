-- Walks the character with the "move_x"/"move_y" actions (WASD, arrows, left stick) and jumps
-- with "jump" (Space, gamepad A). The entity has a
-- CharacterController (it slides along walls, climbs steps and pushes physics bodies); the
-- child "Robot" (a Vanguard starter character) faces the direction of travel; its animation
-- controller (assets/anim/characters/vanguard_locomotion.vanim) blends Idle/Walk/Run from the
-- "speed" parameter, plays Jump, Fall and Land from the "jump" trigger and "grounded", and
-- Interact from the "interact" trigger. Its child "Dust" particle emitter puffs on jumps and
-- landings.
-- Fields below are defaults; override them per entity in the editor inspector.
local Player = {}
Player.speed = 5
Player.jump_speed = 6
Player.bounds = 9 -- stay within this distance of the origin on X and Z
Player.crate = "prefabs/crate.vprefab" -- dropped with "interact" (E, gamepad X)
Player.max_crates = 8                  -- the oldest dropped crate is removed beyond this

function Player:start()
    self.robot = self.entity:find_child("Robot")
    self.dust = self.entity:find_child("Dust")
    self.air_time = 0
    self.dropped = {}
    self.facing = vector.create(0, 0, 1)
end

-- Drops an instance of the crate prefab in front of the player.
function Player:drop_crate()
    local p = self.entity.position + self.facing * 1.4 + vector.create(0, 1.6, 0)
    local crate = scene.instantiate(self.crate, { position = p, name = "Dropped Crate" })
    table.insert(self.dropped, crate)
    if #self.dropped > self.max_crates then
        scene.destroy(table.remove(self.dropped, 1))
    end
end

-- Checkpoints (quick save): entities in the returned table are stored by id.
function Player:save_state()
    return { dropped = self.dropped, facing = self.facing }
end

function Player:load_state(state)
    self.dropped = {}
    for _, crate in state.dropped or {} do
        if crate then table.insert(self.dropped, crate) end
    end
    if state.facing then self.facing = state.facing end
end

function Player:update(dt)
    local interacted = input.action_pressed("interact")
    if interacted then self:drop_crate() end
    -- Actions work with WASD/arrows and a gamepad's left stick (partial tilt walks slower).
    local stick = input.vector("move_x", "move_y")
    local move = vector.create(stick.x, 0, -stick.y) * self.speed
    -- Stop at the play-area bounds (only the outward component).
    local p = self.entity.position
    if (p.x >= self.bounds and move.x > 0) or (p.x <= -self.bounds and move.x < 0) then
        move = vector.create(0, 0, move.z)
    end
    if (p.z >= self.bounds and move.z > 0) or (p.z <= -self.bounds and move.z < 0) then
        move = vector.create(move.x, 0, 0)
    end
    self.entity:move_character(move)
    local grounded = self.entity.grounded
    local jumped = input.action_pressed("jump") and grounded
    if jumped then
        self.entity:jump(self.jump_speed)
        if self.dust then self.dust:emit_particles(14) end
    end
    -- Landing puff: grounded again after being airborne.
    if grounded and self.was_grounded == false and self.dust then self.dust:emit_particles(10) end
    self.was_grounded = grounded
    if not self.robot then return end
    -- Face the direction actually travelled (the robot model looks down +Z) and feed the
    -- animation controller: ground speed picks the Idle/Walk/Run blend, "jump" plays the take-off.
    local v = self.entity.velocity
    local speed = vector.magnitude(vector.create(v.x, 0, v.z))
    if speed > 0.3 then
        self.facing = vector.normalize(vector.create(v.x, 0, v.z))
        self.robot.rotation = vector.create(0, math.deg(math.atan2(v.x, v.z)), 0)
    end
    -- Short hops off step edges are not falls: report airborne only after 0.15 s off the ground.
    self.air_time = grounded and 0 or self.air_time + dt
    self.robot:set_anim_param("speed", speed)
    self.robot:set_anim_param("grounded", self.air_time < 0.15)
    if jumped then self.robot:anim_trigger("jump") end
    if interacted then self.robot:anim_trigger("interact") end
end

return Player
