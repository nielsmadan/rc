local M = {}

local function trim(s)
  return (s:gsub("^%s+", ""):gsub("%s+$", ""))
end

-- An odd run of trailing backslashes is a shell line continuation; an even
-- run is escaped backslashes and stays.
local function dropContinuation(line)
  local slashes = line:match("\\+$")
  if slashes and #slashes % 2 == 1 then
    return trim(line:sub(1, -2))
  end
  return line
end

function M.join(text)
  local paragraphs, current = {}, {}
  local function flush()
    if #current > 0 then paragraphs[#paragraphs + 1] = table.concat(current, " ") end
    current = {}
  end
  for raw in (text:gsub("\r\n?", "\n") .. "\n"):gmatch("(.-)\n") do
    local line = trim(raw)
    if line == "" then
      flush()
    else
      line = dropContinuation(line)
      if line ~= "" then current[#current + 1] = line end
    end
  end
  flush()
  return table.concat(paragraphs, "\n\n")
end

return M
