local directory = (debug.getinfo(1, "S").source:match("^@(.*/)") or "./")

local function screen(id, name, frame)
  return {
    id = function() return id end,
    name = function() return name end,
    frame = function() return frame end,
  }
end

local left = screen(1, "Left", { x = -1200, y = -30, w = 1200, h = 1800 })
local main = screen(2, "Main", { x = 0, y = 24, w = 1800, h = 1200 })
local right = screen(3, "Right", { x = 1800, y = 50, w = 1000, h = 1200 })
local screens = { right, main, left }
local windows, tabCounts, focused = {}, {}, nil
local arrange

local function watcher() return { start = function(self) return self end } end
local fakeHs = {
  configdir = directory,
  window = {
    orderedWindows = function() return windows end,
    focusedWindow = function() return focused end,
    filter = { new = function() return { subscribe = function() end } end },
  },
  screen = {
    allScreens = function() return screens end,
    primaryScreen = function() return screens[1] end,
    watcher = { new = watcher },
  },
  fnutils = {
    filter = function(values, keep)
      local result = {}
      for _, value in ipairs(values) do
        if keep(value) then result[#result + 1] = value end
      end
      return result
    end,
    copy = function(values) return { (table.unpack or unpack)(values) } end,
  },
  osascript = { applescript = function() return tabCounts ~= nil, tabCounts end },
  hotkey = { bind = function(modifiers, key, callback)
    if key == "i" then
      assert(table.concat(modifiers, " ") == "cmd alt ctrl shift")
      arrange = callback
    end
  end },
  caffeinate = { watcher = { new = watcher } },
  pathwatcher = { new = watcher },
  alert = { show = function() end },
  accessibilityState = function() return true end,
  timer = { doAfter = function() end },
}

local function config(h)
  return {
    main_screen = "Main",
    app_placements = { Juggler = {
      { screen = "Missing", placement = h.leftDock(480) },
      { screen = "Main", placement = h.leftDock(360) },
    } },
  }
end

local env = setmetatable({ hs = fakeHs }, { __index = _G })
env._G = env
env.loadfile = function() return function() return config end end
env.require = function(name)
  if name == "hs.ipc" then return {} end
  return dofile(directory .. name .. ".lua")
end
local init = directory .. "init.lua"
if setfenv then setfenv(assert(loadfile(init)), env)()
else assert(loadfile(init, "t", env))() end

local function window(id, display, options)
  options = options or {}
  local app = { name = function() return options.app or "iTerm2" end }
  local win = { rect = { x = 10, y = 50, w = 480, h = 640 } }
  function win:id() return id end
  function win:screen() return display end
  function win:frame() return self.rect end
  function win:application() return app end
  function win:isStandard() return not options.dialog end
  function win:isFullScreen() return options.fullscreen end
  function win:setFrame(frame)
    assert(fakeHs.window.setFrameCorrectness == false)
    self.rect = frame
    focused = self
  end
  function win:raise() focused = self end
  function win:focus() focused = self end
  return win
end

local function frame(win, x, y, w, h)
  for key, expected in pairs({ x = x, y = y, w = w, h = h }) do
    assert(win.rect[key] == expected, string.format("window %d %s: expected %s, got %s",
      win:id(), key, expected, win.rect[key]))
  end
end

local leftWins = {}
for i = 1, 5 do leftWins[i] = window(i, left) end
local small, large = window(6, main), window(7, main)
local rightTop, rightBottom = window(8, right), window(9, right)
local juggler = window(10, main, { app = "Juggler" })
local fullscreen = window(11, main, { fullscreen = true })
local dialog = window(12, main, { dialog = true })
windows = { leftWins[1], small, rightTop, leftWins[2], large, leftWins[3],
  rightBottom, leftWins[4], juggler, leftWins[5], fullscreen, dialog }
tabCounts, focused = { { 6, 1 }, { 7, 4 } }, leftWins[1]

arrange()
for i, y in ipairs({ -30, 570, 1170, -30, 570 }) do
  frame(leftWins[i], -1200, y, 1200, 600)
end
frame(rightTop, 1800, 50, 1000, 600)
frame(rightBottom, 1800, 650, 1000, 600)
frame(large, 360, 56, 1440, 1168)
frame(small, 480, 24, 1320, 1200)
for _, win in ipairs({ juggler, fullscreen, dialog }) do frame(win, 10, 50, 480, 640) end
assert(focused == leftWins[1] and fakeHs.window.setFrameCorrectness == true)
print("PASS side rows and overflow stay on their displays, with a tab-count ladder beside the dock")

screens, windows, tabCounts = { right, left }, { rightTop, rightBottom, leftWins[1] }, nil
arrange()
frame(leftWins[1], -1200, -30, 1200, 1800)
frame(rightTop, 1800, 82, 1000, 1168)
frame(rightBottom, 1920, 50, 880, 1200)
print("PASS a single side window fills its display and the primary display falls back to stacking order")

windows = {}
for i = 1, 10 do windows[i] = window(i, right) end
focused = windows[1]
arrange()
frame(windows[1], 1800, 338, 1000, 912)
frame(windows[10], 2700, 50, 100, 1200)
print("PASS edges of a crowded ladder fit its display")

return "3 iTerm2 arrangement tests passed"
