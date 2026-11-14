local directory = (debug.getinfo(1, "S").source:match("^@(.*/)") or "./")
local run = dofile(directory .. "home_shortcut.lua").run
local frame = { x = 0, y = 25, w = 1512, h = 920 }

local function fixture(names)
  local f = { moved = {}, homes = 0, focus = 0 }
  local function window(standard)
    return {
      isStandard = function() return standard end,
      focus = function() f.focus = f.focus + 1 end,
    }
  end
  f.first, f.second, f.dialog, f.other = window(true), window(true), window(false), window(true)
  local screens = {}
  for _, name in ipairs(names) do
    screens[#screens + 1] = { name = function() return name end, frame = function() return frame end }
  end
  f.hs = {
    screen = { allScreens = function() return screens end },
    window = { focusedWindow = function() return f.first end, setFrameCorrectness = true },
    application = { runningApplications = function() return {
      { name = function() return "iTerm2" end, allWindows = function() return { f.first, f.second, f.dialog } end },
      { name = function() return "Other" end, allWindows = function() return { f.other } end },
    } end },
  }
  function f.run()
    run(f.hs, function(win, target)
      assert(f.hs.window.setFrameCorrectness == false)
      f.moved[#f.moved + 1] = { win = win, frame = target }
    end, function() f.homes = f.homes + 1 end)
  end
  return f
end

for _, name in ipairs({ "Built-in Retina Display", "Built-in Display", "Color LCD" }) do
  local f = fixture({ name })
  f.run()
  assert(#f.moved == 2)
  assert(f.moved[1].win == f.first and f.moved[2].win == f.second)
  for _, move in ipairs(f.moved) do
    for key, value in pairs(frame) do assert(move.frame[key] == value) end
  end
  assert(f.homes == 0, "laptop shortcut must not invoke configured home rules")
  assert(f.hs.window.setFrameCorrectness == true and f.focus == 1)
  print("PASS fills every standard iTerm2 window on " .. name)
end

for _, names in ipairs({ { "Built-in Retina Display", "LG HDR 4K" }, { "LG HDR 4K" }, {} }) do
  local f = fixture(names)
  f.run()
  assert(f.homes == 1)
  assert(#f.moved == 0, "normal home must not also fill iTerm2 windows")
  assert(f.hs.window.setFrameCorrectness == true)
  print("PASS normal home with " .. #names .. " displays: " .. table.concat(names, ", "))
end

return "6 home shortcut tests passed"
