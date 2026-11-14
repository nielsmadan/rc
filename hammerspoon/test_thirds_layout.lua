local directory = (debug.getinfo(1, "S").source:match("^@(.*/)") or "./")
local layout = dofile(directory .. "thirds_layout.lua").frames
local sf = { x = -1200, y = 25, w = 1200, h = 1800 }

local function item(third, screenId, screenFrame)
  local f = screenFrame or sf
  return {
    third = third, screenId = screenId or 1, screenFrame = f,
    frame = { x = f.x, y = f.y + (third - 1) * f.h / 3, w = f.w, h = f.h / 3 },
  }
end

local function equalFrame(got, want)
  for _, key in ipairs({ "x", "y", "w", "h" }) do
    assert(math.abs(got[key] - want[key]) < 0.000001,
      key .. ": expected " .. want[key] .. ", got " .. got[key])
  end
end

local cases = {
  { "empty side", {}, {} },
  { "single top fills", { 1 }, { 1 } },
  { "single middle fills", { 2 }, { 1 } },
  { "single bottom fills", { 3 }, { 1 } },
  { "two separated windows take halves", { 1, 3 }, { 1, 2 } },
  { "two overlapping windows take halves", { 2, 2 }, { 1, 2 } },
  { "halves preserve vertical order", { 3, 1 }, { 2, 1 } },
  { "occupied thirds stay put", { 3, 1, 2 }, { 3, 1, 2 } },
  { "overlap moves into empty top", { 2, 2, 3 }, { 2, 1, 3 } },
  { "overlap moves into empty middle", { 1, 3, 3 }, { 1, 3, 2 } },
  { "overlap moves into empty bottom", { 1, 2, 2 }, { 1, 2, 3 } },
  { "two empty thirds filled", { 2, 2, 2 }, { 2, 3, 1 } },
  { "extra windows still fill every third", { 1, 1, 1, 1 }, { 1, 1, 3, 2 } },
  { "full thirds retain extra overlaps", { 1, 2, 2, 3 }, { 1, 2, 2, 3 } },
}

for _, case in ipairs(cases) do
  local items = {}
  for _, third in ipairs(case[2]) do items[#items + 1] = item(third) end
  local frames = layout(items)
  assert(#frames == #items, case[1])
  for i, row in ipairs(case[3]) do
    local rows = math.min(#items, 3)
    equalFrame(frames[i], { x = sf.x, y = sf.y + (row - 1) * sf.h / rows, w = sf.w, h = sf.h / rows })
    equalFrame(items[i].frame, item(case[2][i]).frame)
    assert(items[i].third == case[2][i])
  end
  print("PASS " .. case[1])
end

local other = { x = 2000, y = -500, w = 900, h = 1500 }
local ladder = { x = 480, y = 32, w = 1500, h = 1000 }
local frames = layout({ item(3), item(1, 2, other), item(2, 2, other), { frame = ladder, screenId = 1 } })
equalFrame(frames[1], sf)
equalFrame(frames[2], { x = 2000, y = -500, w = 900, h = 750 })
equalFrame(frames[3], { x = 2000, y = 250, w = 900, h = 750 })
equalFrame(frames[4], ladder)
print("PASS screens are independent and custom placements are preserved")

return (#cases + 1) .. " thirds layout tests passed"
