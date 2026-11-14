local M = {}

function M.frames(items)
  local frames, screens = {}, {}
  for i, item in ipairs(items) do
    frames[i] = item.frame
    if item.third then
      local group = screens[item.screenId]
      if not group then
        group = { slots = { {}, {}, {} }, count = 0, frame = item.screenFrame }
        screens[item.screenId] = group
      end
      table.insert(group.slots[item.third], i)
      group.count = group.count + 1
    end
  end

  for _, group in pairs(screens) do
    local slots, sf = group.slots, group.frame
    if group.count >= 3 then
      for _, slot in ipairs(slots) do
        if #slot == 0 then
          for _, donor in ipairs(slots) do
            if #donor > 1 then
              slot[1] = table.remove(donor)
              break
            end
          end
        end
      end
    end

    local rank = 0
    local rows = math.min(group.count, 3)
    for third, slot in ipairs(slots) do
      for _, index in ipairs(slot) do
        rank = rank + 1
        local row = group.count < 3 and rank or third
        frames[index] = {
          x = sf.x, y = sf.y + sf.h * (row - 1) / rows,
          w = sf.w, h = sf.h / rows,
        }
      end
    end
  end
  return frames
end

return M
