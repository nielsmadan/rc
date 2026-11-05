local directory = (debug.getinfo(1, "S").source:match("^@(.*/)") or "./")
local join = dofile(directory .. "clipboard_join.lua").join

local cases = {
  { "joins wrapped lines with one space",
    "  docker run --rm -it\n  -v \"$PWD:/src\"\n    alpine sh",
    "docker run --rm -it -v \"$PWD:/src\" alpine sh" },
  { "drops backslash continuations",
    "brew install \\\n  ripgrep \\\n  fd",
    "brew install ripgrep fd" },
  { "mixes continuations with plain wraps",
    "curl -s \\\n  -H 'Accept: json'\n  https://example.com \\\n  | jq .",
    "curl -s -H 'Accept: json' https://example.com | jq ." },
  { "spaces a continuation with no space before it",
    "echo a\\\nb",
    "echo a b" },
  { "keeps an escaped trailing backslash",
    "printf '%s' \\\\\n  done",
    "printf '%s' \\\\ done" },
  { "keeps inner spacing",
    "echo 'a   b'\n  next",
    "echo 'a   b' next" },
  { "handles CRLF and trailing whitespace",
    "git log  \r\n  --oneline\t\r\n",
    "git log --oneline" },
  { "handles bare CR line endings",
    "ls\r  -la",
    "ls -la" },
  { "keeps blank-line-separated blocks apart",
    "cd /tmp\n\n\n  ls\n  -la",
    "cd /tmp\n\nls -la" },
  { "leaves a single line trimmed",
    "   make test   ",
    "make test" },
  { "skips a bare continuation line",
    "a \\\n\\\nb",
    "a b" },
}

local failures = {}
for _, case in ipairs(cases) do
  local got = join(case[2])
  local ok = got == case[3]
  print((ok and "PASS " or "FAIL ") .. case[1])
  if not ok then
    failures[#failures + 1] = string.format("%s: expected %q, got %q", case[1], case[3], got)
  end
end
assert(#failures == 0, table.concat(failures, "\n"))
return #cases .. " clipboard join tests passed"
