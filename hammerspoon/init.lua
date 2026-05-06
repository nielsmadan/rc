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

-- ─── Window-management modal system ──────────────────────────────────
-- Entry: F18 (held). Caps Lock is remapped to F18 by a launchd plist
-- running hidutil at login (see launchd/com.nielsmadan.hidutil-...).
-- On the Moonlander, assign any free key to F18 in Oryx.
--
-- Sequence: F18+W → window mode, then:
--   f         = fullscreen (fill screen)
--   v 1 / v 2 = top / bottom half (vertical = stacked rows)
--   v ⇧1/⇧2/⇧3 = top / middle / bottom third
--   b 1 / b 2 = left / right half (horizontal = side-by-side cols)
--   esc       = abort from any sub-mode
-- After F18+W the chord is released; subsequent keys are pressed plain.
-- F18 itself is consumed (apps never see it as a literal F18 keypress).

local function place(fx, fy, fw, fh)
  return function()
    local win = hs.window.focusedWindow()
    if not win or not win:isStandard() then return end
    local sf = win:screen():frame()
    local prev = hs.window.setFrameCorrectness
    hs.window.setFrameCorrectness = false
    win:setFrame({
      x = sf.x + sf.w * fx,
      y = sf.y + sf.h * fy,
      w = sf.w * fw,
      h = sf.h * fh,
    }, 0)
    hs.window.setFrameCorrectness = prev
  end
end

local hyper        = hs.hotkey.modal.new()
local windowMode   = hs.hotkey.modal.new()
local verticalMode = hs.hotkey.modal.new()
local horizMode    = hs.hotkey.modal.new()

local hint            -- current hs.alert handle (or nil)
local hyperActive    -- true while F18 is held; guards double-enter
local hyperConsumed  -- did the user transition to a submode while F18 held?

-- pcall'd close — alert handles can go stale (auto-dismiss, internal
-- close, etc.). An exception inside a hotkey callback is logged but
-- harmless; defensive anyway.
local function safeClose(h)
  if h then pcall(hs.alert.closeSpecific, h) end
end

local function showHint(text)
  safeClose(hint)
  hint = hs.alert.show(text, true)
end

local function clearHint()
  safeClose(hint)
  hint = nil
end

local function leaveAll()
  hyper:exit(); windowMode:exit(); verticalMode:exit(); horizMode:exit()
  clearHint()
  hyperActive = false
end

-- F18 down/up via hs.hotkey.bind (Carbon RegisterEventHotKey) rather
-- than hs.eventtap. CGEventTaps are silently disabled by macOS on
-- timeout / Lua exception / Secure Input latching after sleep/wake,
-- with no exposed auto-recovery; that's what was making the modal
-- "stop working" mid-session. RegisterEventHotKey doesn't have that
-- failure mode and it's the pattern the Hammerspoon community uses
-- for Caps-Lock-as-Hyper (evantravers, kalis.me).
hs.hotkey.bind({}, "f18",
  function()  -- pressed
    if hyperActive then return end
    leaveAll()  -- always start clean — clears any stale submode state
    hyperActive = true
    hyperConsumed = false
    hyper:enter()
    showHint("hyper: w=window  esc=cancel")
  end,
  function()  -- released
    if not hyperActive then return end
    hyperActive = false
    hyper:exit()
    if not hyperConsumed then clearHint() end
  end
)

-- Esc cancels from any mode.
hyper:bind({}, "escape",        leaveAll)
windowMode:bind({}, "escape",   leaveAll)
verticalMode:bind({}, "escape", leaveAll)
horizMode:bind({}, "escape",    leaveAll)

-- hyper + W → enter window mode (and exit hyper so F18-up is harmless).
hyper:bind({}, "w", function()
  hyperConsumed = true
  hyper:exit()
  windowMode:enter()
  showHint("window: f=fill  v=rows  b=cols  esc=cancel")
end)

-- window mode terminals/submodes.
windowMode:bind({}, "f", function()
  leaveAll(); place(0, 0, 1, 1)()
end)

windowMode:bind({}, "v", function()
  windowMode:exit(); verticalMode:enter()
  showHint("vertical (rows): 1=top  2=bottom  ⇧1/2/3=thirds  esc=cancel")
end)

windowMode:bind({}, "b", function()
  windowMode:exit(); horizMode:enter()
  showHint("horizontal (cols): 1=left  2=right  esc=cancel")
end)

-- Vertical (rows) — full width, fractional height.
verticalMode:bind({}, "1",        function() leaveAll(); place(0, 0,     1, 1 / 2)() end)
verticalMode:bind({}, "2",        function() leaveAll(); place(0, 1 / 2, 1, 1 / 2)() end)
verticalMode:bind({ "shift" }, "1", function() leaveAll(); place(0, 0,     1, 1 / 3)() end)
verticalMode:bind({ "shift" }, "2", function() leaveAll(); place(0, 1 / 3, 1, 1 / 3)() end)
verticalMode:bind({ "shift" }, "3", function() leaveAll(); place(0, 2 / 3, 1, 1 / 3)() end)

-- Horizontal (cols) — fractional width, full height.
horizMode:bind({}, "1", function() leaveAll(); place(0,     0, 1 / 2, 1)() end)
horizMode:bind({}, "2", function() leaveAll(); place(1 / 2, 0, 1 / 2, 1)() end)
-- ──────────────────────────────────────────────────────────────────────

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
-- Wrap so window_filter's extra (appName, event) args don't reach
-- moveToMain — it expects (win, done) where `done` is a callback, and
-- otherwise the appName string ends up bound to `done` and the early-
-- return paths crash with "attempt to call a string value".
managedFilter:subscribe(hs.window.filter.windowCreated, function(win)
  moveToMain(win)
end)

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
