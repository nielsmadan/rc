-- Fill this in once the main monitor is plugged in. The screen watcher
-- below posts an hs.alert listing connected screen names whenever the
-- screen set changes, so the exact name will appear on screen the next
-- time the monitor is connected.
local MAIN_SCREEN_NAME = "LG HDR 5K"

-- Fraction of each side left as empty margin around centered windows.
-- Window ends up 1 - 2*MARGIN_FRAC wide and tall, centered on the screen.
local MARGIN_FRAC = 0.1

-- Retries setFrame with workarounds for known macOS quirks; needed for
-- apps like Neovide that ignore the first AX position-set.
hs.window.setFrameCorrectness = true

-- Reload on save of any .lua under ~/.hammerspoon
hs.pathwatcher.new(os.getenv("HOME") .. "/.hammerspoon/", function(files)
  for _, f in ipairs(files) do
    if f:match("%.lua$") then hs.reload(); return end
  end
end):start()

local function mainScreen()
  if MAIN_SCREEN_NAME == "" then return nil end
  for _, s in ipairs(hs.screen.allScreens()) do
    if s:name() == MAIN_SCREEN_NAME then return s end
  end
  return nil
end

-- Per-app placement on the main screen. Each entry is a function that
-- takes the screen frame and returns the target window frame.
local function centeredWithMargin(sf)
  return {
    x = sf.x + sf.w * MARGIN_FRAC,
    y = sf.y + sf.h * MARGIN_FRAC,
    w = sf.w * (1 - 2 * MARGIN_FRAC),
    h = sf.h * (1 - 2 * MARGIN_FRAC),
  }
end

local function leftDock(width)
  return function(sf)
    return { x = sf.x, y = sf.y, w = width, h = sf.h }
  end
end

local APP_PLACEMENTS = {
  Neovide = centeredWithMargin,
  MacVim  = centeredWithMargin,
  Code    = centeredWithMargin,
  Juggler = leftDock(480),
}

-- Neovide (winit-based) only honors AX setFrame on the focused window —
-- macOS clamps the request otherwise. So we focus briefly, setFrame, then
-- continue. Caller is responsible for restoring prior focus if desired.
-- `done` is called after the move completes, enabling sequential chaining.
local function moveToMain(win, done)
  done = done or function() end
  if not win or not win:isStandard() then return done() end
  local target = mainScreen()
  if not target then return done() end
  local app = win:application()
  local placement = app and APP_PLACEMENTS[app:name()]
  if not placement then return done() end
  local frame = placement(target:frame())
  win:focus()
  hs.timer.doAfter(0.05, function()
    if win:isStandard() then win:setFrame(frame) end
    hs.timer.doAfter(0.05, done)
  end)
end

-- Iterate managed windows sequentially — each window's focus+setFrame must
-- complete before the next begins, otherwise concurrent `focus()` calls
-- race and only the last app's window actually moves.
local function homeAllManagedWindows()
  local windows = {}
  for appName in pairs(APP_PLACEMENTS) do
    -- exact=true so "Code" doesn't fuzzy-match "Xcode"
    local app = hs.application.get(appName, true)
    if app then
      for _, win in ipairs(app:allWindows()) do
        table.insert(windows, win)
      end
    end
  end

  local prev = hs.window.focusedWindow()
  local function step(i)
    if i > #windows then
      if prev and prev:isStandard() then prev:focus() end
      return
    end
    moveToMain(windows[i], function() step(i + 1) end)
  end
  step(1)
end

local managedAppNames = {}
for name in pairs(APP_PLACEMENTS) do
  table.insert(managedAppNames, name)
end
local managedFilter = hs.window.filter.new(managedAppNames)
managedFilter:subscribe(hs.window.filter.windowCreated, moveToMain)

hs.screen.watcher.new(function()
  local names = {}
  for _, s in ipairs(hs.screen.allScreens()) do
    table.insert(names, s:name())
  end
  local joined = table.concat(names, " | ")
  print("screens: " .. joined)
  hs.alert.show("screens: " .. joined, 3)
  homeAllManagedWindows()
end):start()

-- Defer initial pass so hs.application's registry is fully populated.
hs.timer.doAfter(0.5, homeAllManagedWindows)

hs.alert.show("Hammerspoon loaded")
