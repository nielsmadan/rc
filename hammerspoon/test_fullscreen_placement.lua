local directory = debug.getinfo(1, "S").source:match("^@(.*/)")

local function fixture(options)
  options = options or {}
  local f = { now = 0, timers = {}, actions = {}, completed = {}, messages = {}, pending = {} }
  local side = { id = function() return 1 end, frame = function() return { w = 1080, h = 1920, screenId = 1 } end }
  local main = { id = function() return 2 end, frame = function() return { w = 3440, h = 1440, screenId = 2 } end }
  f.main, f.side, f.target = main, side, main
  f.win = { screenValue = options.onTarget and main or side, fullscreen = options.fullscreen ~= false, windowId = 42 }
  function f.win:id() return self.windowId end
  function f.win:isStandard() return f.now >= (options.readyAt or 0) end
  function f.win:screen() return self.screenValue end
  function f.win:frame() return self.screenValue:frame() end
  function f.win:isFullScreen() return self.fullscreen end
  function f.win:setFullScreen(value)
    table.insert(f.actions, { kind = "fullscreen", value = value, time = f.now })
    if f.now < (options.acceptAt or 0) or self.transition then return end
    if options.transitionTime then
      self.transition = true
      table.insert(f.pending, { at = f.now + options.transitionTime, run = function()
        self.fullscreen, self.transition = value, false
      end })
    else
      self.fullscreen = value
    end
  end
  function f.win:setFrame(frame)
    assert(not self.fullscreen, "attempted to move a fullscreen window")
    table.insert(f.actions, { kind = "move", time = f.now })
    if options.stuck or self.transition or f.now < (options.acceptAt or 0) then return end
    self.screenValue = frame.screenId == 2 and main or side
  end

  local fakeHs = { window = { setFrameCorrectness = true }, timer = {} }
  function fakeHs.timer.secondsSinceEpoch() return f.now end
  function fakeHs.timer.doEvery(interval, callback)
    local timer = { active = true, next = f.now + interval, interval = interval, callback = callback }
    function timer:stop() self.active = false end
    table.insert(f.timers, timer)
    return timer
  end
  local env = setmetatable({ hs = fakeHs, print = function(message) table.insert(f.messages, message) end }, { __index = _G })
  local module = assert(loadfile(directory .. "fullscreen_placement.lua", "t", env))()
  f.placer = module.new(function() return f.target end, function(id) table.insert(f.completed, id) end)
  function f.advance(seconds)
    local untilTime = f.now + seconds
    while f.now < untilTime - 0.001 do
      f.now = math.min(untilTime, f.now + 0.1)
      for i = #f.pending, 1, -1 do
        if f.pending[i].at <= f.now then
          local action = table.remove(f.pending, i)
          action.run()
        end
      end
      for _, timer in ipairs(f.timers) do
        if timer.active and timer.next <= f.now then
          timer.next = f.now + timer.interval
          timer.callback()
        end
      end
    end
    assert(fakeHs.window.setFrameCorrectness, "setFrameCorrectness was left disabled")
  end
  function f.assertPlaced()
    assert(f.win:screen() == main, "window did not reach the main screen")
    assert(f.win:isFullScreen(), "fullscreen was not restored")
    assert(#f.completed == 1 and f.completed[1] == 42, "placement was not confirmed exactly once")
  end
  return f
end

local tests = {
  { "waits for Accessibility to recover during startup", function()
    local f = fixture({ readyAt = 10 })
    f.placer.start(f.win, true)
    f.advance(8)
    assert(#f.actions == 0 and #f.completed == 0, "unresponsive window was treated as ready")
    f.advance(15)
    f.assertPlaced()
  end },
  { "retries requests ignored while the game loads", function()
    local f = fixture({ acceptAt = 10 })
    f.placer.start(f.win, true)
    f.advance(25)
    f.assertPlaced()
    assert(#f.actions > 3, "ignored fullscreen requests were not retried")
  end },
  { "waits for slow fullscreen transitions", function()
    local f = fixture({ transitionTime = 4 })
    f.placer.start(f.win, true)
    f.advance(30)
    f.assertPlaced()
  end },
  { "corrects a late startup switch to a side monitor", function()
    local f = fixture({ onTarget = true, fullscreen = false })
    f.placer.start(f.win, true)
    f.advance(10)
    assert(#f.completed == 0, "startup observation ended too early")
    f.win.screenValue, f.win.fullscreen = f.side, true
    f.advance(15)
    f.assertPlaced()
  end },
  { "leaves an already placed fullscreen window alone", function()
    local f = fixture({ onTarget = true })
    f.placer.start(f.win, true)
    f.advance(20)
    f.assertPlaced()
    assert(#f.actions == 0, "correct placement caused a fullscreen cycle")
  end },
  { "preserves windowed mode", function()
    local f = fixture({ fullscreen = false })
    f.placer.start(f.win, true)
    f.advance(20)
    assert(f.win:screen() == f.main and not f.win:isFullScreen(), "windowed mode was changed")
    assert(#f.completed == 1 and #f.actions == 1 and f.actions[1].kind == "move")
  end },
  { "times out and restores fullscreen when movement fails", function()
    local f = fixture({ stuck = true })
    f.placer.start(f.win, true)
    f.advance(50)
    assert(f.win:screen() == f.side and f.win:isFullScreen(), "timeout did not restore fullscreen")
    assert(#f.completed == 0 and #f.messages == 1 and f.messages[1]:match("timed out"))
    local count = #f.actions
    f.placer.start(f.win, true)
    f.advance(50)
    assert(#f.actions == count, "a title event restarted an exhausted placement")
    f.placer.start(f.win, false)
    f.advance(5)
    assert(#f.actions > count, "explicit re-home could not retry an exhausted placement")
  end },
  { "shares one retry sequence across overlapping events", function()
    local f = fixture({ acceptAt = 10 })
    f.placer.start(f.win, true)
    f.advance(4)
    f.placer.start(f.win, true)
    f.placer.start(f.win, false)
    assert(#f.timers == 1, "overlapping placement timers were started")
    f.advance(25)
    f.assertPlaced()
  end },
  { "cancels closed windows and allows their IDs to be reused", function()
    local f = fixture()
    f.placer.start(f.win, true)
    f.placer.cancel(42)
    f.advance(50)
    assert(#f.actions == 0 and #f.completed == 0, "closed window received delayed actions")
    f.placer.start(f.win, true)
    f.advance(20)
    f.assertPlaced()
  end },
  { "restores fullscreen when the target monitor disappears", function()
    local f = fixture()
    f.placer.start(f.win, true)
    f.advance(4)
    assert(not f.win:isFullScreen(), "test did not reach the fullscreen transition")
    f.target = nil
    f.advance(5)
    assert(f.win:isFullScreen() and #f.completed == 0 and #f.messages == 1)
    assert(f.messages[1]:match("no available target screen"))
  end },
}

local failures = {}
for _, test in ipairs(tests) do
  local ok, err = pcall(test[2])
  print((ok and "PASS " or "FAIL ") .. test[1])
  if not ok then table.insert(failures, test[1] .. ": " .. tostring(err)) end
end
assert(#failures == 0, table.concat(failures, "\n"))
return #tests .. " fullscreen placement tests passed"
