-- SPECIAL OPS autotest driver. Plays a scripted input timeline through Controls.virtual and
-- records checks; results are logged as "AUTOTEST ..." lines (victus simulate writes them to
-- the diagnostics log, read by tools/test/run_autotests.py).
-- The `plan` property names a plan in scripts/tests/plans.luau.
local Game = require("scripts/lib/game")
local Controls = require("scripts/lib/controls")
local Plans = require("scripts/tests/plans")

local T = {}
T.plan = "movement"

function T:start()
    Game.autotest = true
    self.t = 0
    self.i = 1
    self.ctx = { checks = {}, failed = 0, passed = 0, data = {} }
    local ctx = self.ctx
    function ctx.check(name, ok, detail)
        if ok then ctx.passed += 1 else ctx.failed += 1 end
        log.warn("AUTOTEST", ok and "PASS" or "FAIL", self.plan, name, detail or "")
    end
    self.steps = Plans[self.plan]
    if not self.steps then
        log.warn("AUTOTEST FAIL", self.plan, "unknown plan")
        self.done = true
    end
    log.warn("AUTOTEST BEGIN", self.plan)
end

function T:update(dt)
    if self.done then return end
    self.t += dt
    local v = Controls.virtual
    while self.i <= #self.steps and self.steps[self.i].at <= self.t do
        local s = self.steps[self.i]
        if s.move ~= nil then v.move = s.move or nil end
        if s.look ~= nil then v.look = s.look or nil end
        if s.press then v.down[s.press] = true end
        if s.release then v.down[s.release] = nil end
        if s.run then s.run(self.ctx) end
        self.i += 1
    end
    if self.i > #self.steps then
        self.done = true
        v.move, v.look, v.down = nil, nil, {}
        log.warn("AUTOTEST END", self.plan, "passed", self.ctx.passed, "failed", self.ctx.failed)
    end
end

return T
