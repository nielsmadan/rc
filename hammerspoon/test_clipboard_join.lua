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
  { "glues a path the terminal broke mid-word",
    "  sudo launchctl bootstrap gui/501 /Users/nielsmadan/Library/LaunchAgent\n" ..
    "  s/com.nielsmadan.colima-watchdog.plist",
    "sudo launchctl bootstrap gui/501 /Users/nielsmadan/Library/LaunchAgents/com.nielsmadan.colima-watchdog.plist" },
  { "glues a URL broken across three lines",
    "  open https://example.com/aaaa\n  bbbbbbbbbbbbbbbbbbbbbbbbbbbbb\n  cc",
    "open https://example.com/aaaabbbbbbbbbbbbbbbbbbbbbbbbbbbbbcc" },
  { "spaces a second path argument on the next line",
    "  ln -s /Users/nielsmadan/rc/hammerspoon/init.lua\n  /Users/nielsmadan/.hammerspoon/init.lua",
    "ln -s /Users/nielsmadan/rc/hammerspoon/init.lua /Users/nielsmadan/.hammerspoon/init.lua" },
  { "spaces a short word after a full line",
    "  git -C /Users/nielsmadan/rc/hammerspoon\n  status --short",
    "git -C /Users/nielsmadan/rc/hammerspoon status --short" },
  { "spaces word-wrapped prose",
    "  the quick brown fox jumps over\n  the lazy dog and keeps running",
    "the quick brown fox jumps over the lazy dog and keeps running" },
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
