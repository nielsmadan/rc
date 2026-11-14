local M = {}

function M.run(hs, setFrame, homeWindows)
  local screens = hs.screen.allScreens()
  local name = #screens == 1 and screens[1]:name() or ""
  if not (name and (name:match("^Built%-in") or name == "Color LCD")) then
    homeWindows()
    return
  end

  local focused = hs.window.focusedWindow()
  local frame = screens[1]:frame()
  local correctness = hs.window.setFrameCorrectness
  hs.window.setFrameCorrectness = false
  for _, app in ipairs(hs.application.runningApplications()) do
    if app:name() == "iTerm2" then
      for _, win in ipairs(app:allWindows()) do
        if win:isStandard() then setFrame(win, frame) end
      end
    end
  end
  hs.window.setFrameCorrectness = correctness
  if focused and focused:isStandard() then focused:focus() end
end

return M
