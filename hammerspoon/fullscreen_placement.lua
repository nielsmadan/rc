local RETRY_INTERVAL = 1.2
local TIMEOUT = 45
local STARTUP_DELAY = 2.5
local STARTUP_OBSERVE = 15
local STABLE_TIME = 3

local M = {}

function M.new(resolveScreen, onPlaced)
  local jobs = {}
  local placer = {}

  function placer.cancel(id)
    local job = jobs[id]
    if job and job.timer then job.timer:stop() end
    jobs[id] = nil
  end

  function placer.start(win, startup)
    local id = win:id()
    if not id then return end
    local previous = jobs[id]
    if previous and (previous.timer or startup) then return end

    local started = hs.timer.secondsSinceEpoch()
    local job = { restoreFullscreen = false }
    jobs[id] = job
    local nextAction = started + (startup and STARTUP_DELAY or 0)
    local observeUntil = started + (startup and STARTUP_OBSERVE or 0)

    local function finish(success, reason)
      job.timer:stop()
      job.timer = nil
      if success then
        onPlaced(id)
      else
        if job.restoreFullscreen and win:id() == id and win:isStandard() and not win:isFullScreen() then
          win:setFullScreen(true)
        end
        print("fullscreen placement: window " .. id .. " " .. reason)
      end
    end

    local function step()
      local now = hs.timer.secondsSinceEpoch()
      if now - started >= TIMEOUT then return finish(false, "timed out") end
      if now < nextAction then return end
      if win:id() ~= id or not win:isStandard() then
        job.stableSince = nil
        return
      end

      local screen = resolveScreen(win)
      if not screen then return finish(false, "has no available target screen") end
      local current = win:screen()
      local frame = win:frame()
      if not current or frame.w <= 0 or frame.h <= 0 then
        job.stableSince = nil
        return
      end
      local fullscreen = win:isFullScreen()
      local onTarget = current:id() == screen:id()
      if onTarget and (not job.restoreFullscreen or fullscreen) then
        if job.targetId ~= screen:id() then job.stableSince = nil end
        job.targetId = screen:id()
        job.stableSince = job.stableSince or now
        if now >= observeUntil and now - job.stableSince >= STABLE_TIME then
          finish(true)
        end
        return
      end

      job.stableSince = nil
      nextAction = now + RETRY_INTERVAL
      if not onTarget and fullscreen then
        job.restoreFullscreen = true
        win:setFullScreen(false)
      elseif not onTarget then
        local correctness = hs.window.setFrameCorrectness
        hs.window.setFrameCorrectness = false
        win:setFrame(screen:frame(), 0)
        hs.window.setFrameCorrectness = correctness
      else
        win:setFullScreen(true)
      end
    end

    job.timer = hs.timer.doEvery(RETRY_INTERVAL, step)
  end

  return placer
end

return M
