local M = {}

-- A line starting with one of these begins a new argument (a flag, an
-- absolute or home path, a variable, a quote, an operator), never the tail
-- of a broken word.
local NEW_ARGUMENT = "^[-/~$'\"|&;<>()#]"

local function trim(s)
  return (s:gsub("^%s+", ""):gsub("%s+$", ""))
end

local function width(s)
  return select(2, s:gsub("[^\128-\191]", ""))
end

-- An odd run of trailing backslashes is a shell line continuation; an even
-- run is escaped backslashes and stays.
local function parse(raw)
  local text = trim(raw)
  local slashes = text:match("\\+$")
  local continued = slashes ~= nil and #slashes % 2 == 1
  return {
    text = continued and trim(text:sub(1, -2)) or text,
    width = width((raw:gsub("%s+$", ""))),
    continued = continued,
    blank = text == "",
  }
end

-- The terminal only breaks inside a word that is longer than the whole line,
-- and then fills the line to the edge first. So a mid-word break needs the
-- previous line at the widest width seen and a joined word wider than that.
local function brokenMidWord(joinedSoFar, prev, line, maxWidth)
  if prev.continued or prev.width ~= maxWidth then return false end
  local head = line.text:match("^%S+")
  local tail = joinedSoFar:match("%S+$")
  return not head:find(NEW_ARGUMENT) and width(tail) + width(head) > maxWidth
end

function M.join(text)
  local lines = {}
  for raw in (text:gsub("\r\n?", "\n") .. "\n"):gmatch("(.-)\n") do
    lines[#lines + 1] = parse(raw)
  end
  local maxWidth = 0
  for _, line in ipairs(lines) do maxWidth = math.max(maxWidth, line.width) end

  local paragraphs, current, prev = {}, "", nil
  local function flush()
    if current ~= "" then paragraphs[#paragraphs + 1] = current end
    current, prev = "", nil
  end
  for _, line in ipairs(lines) do
    if line.blank then
      flush()
    elseif line.text ~= "" then
      if prev then
        current = current .. (brokenMidWord(current, prev, line, maxWidth) and "" or " ")
      end
      current = current .. line.text
      prev = line
    end
  end
  flush()
  return table.concat(paragraphs, "\n\n")
end

return M
