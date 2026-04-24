-- Fill this in once the main monitor is plugged in. The screen watcher
-- below posts an hs.alert listing connected screen names whenever the
-- screen set changes, so the exact name will appear on screen the next
-- time the monitor is connected.
local MAIN_SCREEN_NAME = ""  -- e.g. "DELL U2720Q"

local EDITOR_APPS = { "Neovide", "MacVim", "Code" }

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

local function moveToMain(win)
  if not win or not win:isStandard() then return end
  local target = mainScreen()
  if not target then return end
  if win:screen():id() == target:id() then return end
  win:moveToScreen(target, true, true)
end

local editorFilter = hs.window.filter.new(EDITOR_APPS)
editorFilter:subscribe(hs.window.filter.windowCreated, moveToMain)

hs.screen.watcher.new(function()
  local names = {}
  for _, s in ipairs(hs.screen.allScreens()) do
    table.insert(names, s:name())
  end
  local joined = table.concat(names, " | ")
  print("screens: " .. joined)
  hs.alert.show("screens: " .. joined, 3)
  for _, win in ipairs(editorFilter:getWindows()) do
    moveToMain(win)
  end
end):start()

hs.alert.show("Hammerspoon loaded")
