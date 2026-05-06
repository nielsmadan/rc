-- Per-machine config (monitor names, app placements, window rules) is
-- loaded from ~/.hammerspoon/local.lua — see local.lua.example in this
-- directory for the API. That file is gitignored so each machine has
-- its own. Without it, no auto-placement happens; the F18 modal still
-- works fine. The screen watcher below posts an hs.alert listing
-- connected screen names on every screen-config change, so the right
-- name to put in local.lua appears on screen when monitors are plugged.

-- Fraction of each side left as empty margin around centered windows
-- (used by the centeredWithMargin helper passed to local.lua).
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

-- Forward-declared so the F18+W+H binding below can call it; the actual
-- definition lives further down with the rest of the placement code.
local homeAllManagedWindows

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
  showHint("window: f=fill  v=rows  b=cols  h=home  esc=cancel")
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

-- Manual re-home: re-runs the placement pass over all managed windows.
-- Same code path that fires on screen-config change / system wake.
windowMode:bind({}, "h", function()
  leaveAll(); homeAllManagedWindows()
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

local function findScreen(name)
  if not name or name == "" then return nil end
  for _, s in ipairs(hs.screen.allScreens()) do
    if s:name() == name then return s end
  end
  return nil
end

-- Placement helpers — each takes a screen frame and returns the target
-- window frame. Project convention: "vertical" = stacked rows, "horizontal"
-- = side-by-side cols.
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

local function bottomThird(sf)
  return { x = sf.x, y = sf.y + sf.h * 2 / 3, w = sf.w, h = sf.h / 3 }
end

-- Load ~/.hammerspoon/local.lua for per-machine MAIN_SCREEN_NAME,
-- APP_PLACEMENTS and WINDOW_RULES. Missing file = empty config, no
-- auto-placement (modal still works). See local.lua.example for the API.
local function loadLocalConfig(helpers)
  local chunk = loadfile(hs.configdir .. "/local.lua")
  if not chunk then return {} end
  local ok, fn = pcall(chunk)
  if not ok or type(fn) ~= "function" then
    hs.alert.show("local.lua: expected function(helpers) → cfg, got " .. tostring(fn), 5)
    return {}
  end
  local ok2, cfg = pcall(fn, helpers)
  if not ok2 then
    hs.alert.show("local.lua threw: " .. tostring(cfg), 5)
    return {}
  end
  return cfg or {}
end

local localCfg = loadLocalConfig({
  centeredWithMargin = centeredWithMargin,
  leftDock           = leftDock,
  bottomThird        = bottomThird,
})

local MAIN_SCREEN_NAME = localCfg.main_screen     or ""
local APP_PLACEMENTS   = localCfg.app_placements  or {}
local WINDOW_RULES     = localCfg.window_rules    or {}

local function ruleMatches(rule, win)
  local app = win:application()
  if not app or app:name() ~= rule.app then return false end
  if rule.titlePattern and not (win:title() or ""):match(rule.titlePattern) then
    return false
  end
  return true
end

-- Neovide (winit-based) only honors AX setFrame on the focused window —
-- macOS clamps the request otherwise. So we focus briefly, setFrame, then
-- continue. The same dance is harmless for other apps.
local function applyPlacement(win, screen, placement, done)
  if not screen or not placement then return done() end
  local frame = placement(screen:frame())
  win:focus()
  hs.timer.doAfter(0.05, function()
    if win:isStandard() then win:setFrame(frame) end
    hs.timer.doAfter(0.05, done)
  end)
end

-- Resolve which (screen, placement) to use for a given window — first
-- matching WINDOW_RULES wins; otherwise fall back to APP_PLACEMENTS on
-- MAIN_SCREEN_NAME. Returns nil if nothing matches.
local function resolvePlacement(win)
  for _, rule in ipairs(WINDOW_RULES) do
    if ruleMatches(rule, win) then
      return findScreen(rule.screen), rule.placement
    end
  end
  local app = win:application()
  local placement = app and APP_PLACEMENTS[app:name()]
  if placement then return findScreen(MAIN_SCREEN_NAME), placement end
  return nil, nil
end

local function moveToMain(win, done)
  done = done or function() end
  if not win or not win:isStandard() then return done() end
  local screen, placement = resolvePlacement(win)
  if not screen or not placement then return done() end
  applyPlacement(win, screen, placement, done)
end

-- Union of APP_PLACEMENTS keys and WINDOW_RULES app names. Both the
-- window filter (event subscription) and homeAllManagedWindows (initial /
-- screen-change pass) iterate this list.
local managedAppNames = {}
do
  local seen = {}
  for name in pairs(APP_PLACEMENTS) do
    if not seen[name] then table.insert(managedAppNames, name); seen[name] = true end
  end
  for _, rule in ipairs(WINDOW_RULES) do
    if not seen[rule.app] then table.insert(managedAppNames, rule.app); seen[rule.app] = true end
  end
end

-- Iterate managed windows sequentially — each window's focus+setFrame must
-- complete before the next begins, otherwise concurrent `focus()` calls
-- race and only the last app's window actually moves.
function homeAllManagedWindows()
  -- Build a name → true set for O(1) exact matching. We can't use
  -- hs.application.get(name) here: it only takes one arg (the second,
  -- "exact", is silently dropped) and dispatches a substring search,
  -- so "Code" would also match "Xcode", and the empty-result/window-
  -- fallback path can return non-application objects that lack
  -- :allWindows (which crashed line 271).
  local wanted = {}
  for _, name in ipairs(managedAppNames) do wanted[name] = true end

  local windows = {}
  for _, app in ipairs(hs.application.runningApplications()) do
    local name = app:name()
    if name and wanted[name] then
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

-- Placement runs only on three triggers — we deliberately do NOT
-- subscribe to per-window events:
--   1. The 0.5s post-load timer below (initial pass after Hammerspoon
--      starts).
--   2. screen.watcher (monitor connected/disconnected/reconfigured).
--   3. caffeinate.watcher systemDidWake (after sleep).
-- Subscribing to windowCreated/windowTitleChanged caused a feedback loop
-- with iTerm2: setFrame → iTerm2 snaps to char grid → prompt redraws →
-- OSC title escape → windowTitleChanged → setFrame → ... ad infinitum.
hs.caffeinate.watcher.new(function(event)
  if event == hs.caffeinate.watcher.systemDidWake then
    homeAllManagedWindows()
  end
end):start()

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
