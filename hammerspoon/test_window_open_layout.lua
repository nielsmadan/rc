local directory = (debug.getinfo(1, "S").source:match("^@(.*/)") or "./")
local events, timers, windows, focused = {}, {}, {}, nil
local app = { name = function() return "iTerm2" end, allWindows = function() return windows end }
local function screen(id, name, x)
  return {
    id = function() return id end,
    name = function() return name end,
    frame = function() return { x = x, y = 25, w = 1200, h = 1800 } end,
  }
end
local left, right = screen(1, "Left", -1200), screen(2, "Right", 1200)
local function watcher() return { start = function(self) return self end } end
local filter = {
  windowCreated = "created", windowVisible = "visible",
  windowTitleChanged = "title", windowDestroyed = "destroyed",
  new = function()
    return { subscribe = function(_, event, callback) events[event] = callback end }
  end,
}
local fakeHs = {
  configdir = directory,
  window = { filter = filter, focusedWindow = function() return focused end },
  application = { runningApplications = function() return { app } end },
  screen = { allScreens = function() return { left, right } end, watcher = { new = watcher } },
  caffeinate = { watcher = { new = watcher } },
  pathwatcher = { new = watcher },
  hotkey = { bind = function() end },
  alert = { show = function() end },
  accessibilityState = function() return true end,
  timer = { doAfter = function(_, callback) timers[#timers + 1] = callback end },
}
local function config(h)
  return { window_rules = {
    { app = "iTerm2", titlePattern = "^notes", screen = "Left", placement = h.topThird },
    { app = "iTerm2", titlePattern = "^blog", screen = "Left", placement = h.middleThird },
    { app = "iTerm2", titlePattern = "^new", screen = "Left", placement = h.bottomThird },
    { app = "iTerm2", titlePattern = "^right", screen = "Right", placement = h.topThird },
    { app = "iTerm2", titlePattern = "^custom", screen = "Left", placement = h.leftDock(480) },
  } }
end
local env = setmetatable({ hs = fakeHs }, { __index = _G })
env._G = env
local function loadInEnv(path)
  if setfenv then return setfenv(assert(loadfile(path)), env) end
  return assert(loadfile(path, "t", env))
end
env.loadfile = function(path)
  assert(path == directory .. "/local.lua")
  return function() return config end
end
env.require = function(name)
  if name == "hs.ipc" then return {} end
  return loadInEnv(directory .. name .. ".lua")()
end
loadInEnv(directory .. "init.lua")()

local function window(id, title)
  local win = { label = title, moves = 0, rect = { x = 0, y = 0, w = 800, h = 600 } }
  function win:id() return id end
  function win:title() return self.label end
  function win:application() return app end
  function win:isStandard() return true end
  function win:frame() return self.rect end
  function win:focus() focused = self end
  function win:raise() focused = self end
  function win:setFrame(frame)
    assert(fakeHs.window.setFrameCorrectness == false)
    self.rect = frame
    self.moves = self.moves + 1
    assert(self.moves < 20, "resize/title feedback loop")
    focused = self
    events.title(self)
  end
  return win
end
local function frame(win, y, height, x, width)
  local expected = { x = x or -1200, y = y, w = width or 1200, h = height }
  for key, value in pairs(expected) do
    assert(win.rect[key] == value, win.label .. " " .. key .. ": expected " .. value .. ", got " .. win.rect[key])
  end
end
local function flush()
  while #timers > 0 do table.remove(timers, 1)() end
end
local notes, remote, custom = window(1, "notes"), window(2, "right"), window(3, "custom")
windows, focused = { notes, remote, custom }, notes
flush()
frame(notes, 25, 1800)
frame(remote, 25, 1800, 1200)
frame(custom, 25, 1800, -1200, 480)
local remoteMoves, customMoves = remote.moves, custom.moves

local blog = window(4, "shell")
windows, focused = { notes, remote, custom, blog }, blog
events.created(blog)
assert(blog.moves == 0, "unmatched title must wait for a home rule")
blog.label = "blog"
events.title(blog)
frame(notes, 25, 900)
frame(blog, 925, 900)
assert(focused == blog)
assert(remote.moves == remoteMoves and custom.moves == customMoves, "opening must only move its thirds group")
print("PASS late title splits the target monitor into halves and preserves focus")

local notesMoves, blogMoves = notes.moves, blog.moves
blog.rect = { x = 20, y = 50, w = 600, h = 700 }
events.title(blog)
events.visible(blog)
frame(blog, 50, 700, 20, 600)
assert(notes.moves == notesMoves and blog.moves == blogMoves, "repeat events must preserve manual placement")
print("PASS repeated title and visibility events preserve manual placement")

local new = window(5, "new")
focused = new
events.created(new)
frame(notes, 25, 600)
frame(blog, 625, 600)
frame(new, 1225, 600)
assert(focused == new)
windows[#windows + 1] = new
print("PASS third window joins before application enumeration catches up")

env.homeWindows()
flush()
frame(notes, 25, 600)
frame(blog, 625, 600)
frame(new, 1225, 600)
print("PASS opening and explicit Home produce the same layout")

windows = { notes, remote, custom }
notesMoves = notes.moves
events.destroyed(blog)
events.destroyed(new)
frame(notes, 25, 600)
assert(notes.moves == notesMoves, "closing must not rebalance survivors")
print("PASS closing windows keeps survivor sizes")

local reopened = window(4, "blog")
windows, focused = { notes, remote, custom, reopened }, reopened
events.created(reopened)
frame(notes, 25, 900)
frame(reopened, 925, 900)
assert(focused == reopened and fakeHs.window.setFrameCorrectness == true)
print("PASS reused window IDs join the layout again")

notesMoves, blogMoves = notes.moves, reopened.moves
local anotherCustom = window(6, "custom second")
windows[#windows + 1] = anotherCustom
events.created(anotherCustom)
frame(anotherCustom, 25, 1800, -1200, 480)
assert(notes.moves == notesMoves and reopened.moves == blogMoves, "custom homes must not rebalance thirds")
print("PASS custom placement leaves thirds untouched")

return "7 window opening layout tests passed"
