# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository purpose

Personal dotfiles for macOS. `install.sh` symlinks files from this repo into `$HOME` (and a few other places like `~/.config/nvim`, `~/.config/kitty`, iTerm2's scripts dir). Editing a file here = editing the live config. Re-running `install.sh` is idempotent.

Each app's config lives in its **own subdir** (`hammerspoon/`, `iterm2/`, `nvim/`, `kitty/`, `wezterm/`, …); `install.sh` maps each to its target. After moving a config into a subdir, re-run `install.sh` so the symlink follows — the old symlink otherwise still points at the pre-move path.

## Commit messages

**This repo overrides the global `feat`/`fix`/`chore` commit policy** (from `~/.claude/CLAUDE.md`) — that policy does **not** apply here. Instead, commits use a `scope: subject` style where the scope is the area or tool touched, and the subject is a lowercase, imperative one-liner:

```
hammerspoon: add fullscreen toggle
zsh: gate setup by OS
mise: add vault
iterm2: clone repo to new tab
```

Common scopes in use: `zsh`, `mise`, `iterm2`, `hammerspoon`, `git`, `sops`, `vim`, `nvim`, `kitty`. Pick the scope matching the files changed; use a new one when none fits. Keep changes to a single scope per commit where practical.

## Per-machine install skip list (`install.local`)

Every `link` call in `install.sh` carries a short **alias** as its first argument (`gitignore`, `zshrc`, `nvim`, …). `install.local` (repo root, **gitignored**, one alias per line) is a per-machine opt-out: an uncommented alias means `install.sh` skips that target — it won't re-link it, and if the destination is currently a symlink into this repo it's **detached** into a real machine-local copy (`cp -R`) so it can be edited without affecting the repo. Re-comment the line to hand the target back to the repo symlink on the next run.

`install.sh` generates `install.local` on first run (at the end, after every `link` call) with all aliases listed but commented out, so the default file skips nothing. The alias list is single-sourced: `link()` appends each alias to a `SEEN_KEYS` array, and the stub is built from that — no separate hardcoded list to keep in sync. **When adding or removing a `link` call, just give it an alias; the stub updates itself.**

## Two editor configs coexist

This repo maintains **both** a legacy Vim config and a modern Neovim config in parallel — they are not migrating from one to the other.

- **Vim** — single-file `.vimrc`, plugins via `vim-plug`, completion via `coc.nvim`, linting/fixing via `ALE`, fuzzy finding via `fzf.vim`.
- **Neovim** — Lua config under `nvim/`, plugins via `lazy.nvim`, completion via `blink.cmp` + `nvim-lspconfig` + `mason`, fuzzy finding via `snacks.nvim` picker, AI via `codecompanion.nvim`. `nvim/init.lua` also `:source`s `nvim/vimrc.vim` for shared baseline mappings (leader, `jj`→Esc, window nav, system clipboard, etc.).

Leader is `,` in both. Both define the same diff-mode mappings (arrows for hunk nav/pull/push, `<M-1/2/3>` for `:diffget N`, `<M-p>N` for `:diffput N`).

## Keybinding docs — keep them in sync

`VIM_KEYBINDINGS.md` and `NVIM_KEYBINDINGS.md` are hand-curated tables of *custom* mappings. **Whenever you add, remove, or change a mapping in `.vimrc`, `nvim/vimrc.vim`, or any `nvim/lua/**` file, update the matching keybindings doc in the same change.**

## Neovim layout

Plugins live in `nvim/lua/plugins/` (auto-imported by lazy.nvim — drop a new spec into any `*.lua` file there). Settings and ad-hoc commands live in `nvim/lua/config/` and only run if `require`d explicitly from `lazy.lua`.

The `harlequin` colorscheme is a separate local repo at `~/wrksp/harlequin` referenced by both `.vimrc` (`Plug '~/wrksp/harlequin'`) and `nvim/lua/plugins/colorscheme.lua` (`dir = "~/wrksp/harlequin"`). Don't try to install it from a remote.

## Vim quirks worth knowing

- `<leader>f` is bound twice in `.vimrc`: CoC's `coc-format-selected` is later overridden in normal mode by ALE's `ToggleFormatOnWrite`. The visual-mode binding still goes to CoC.
- ALE picks the JS/TS fixer per-buffer via `s:SetJSFixer()`: `biome` if a `biome.json[c]` is found upward from the file, else `prettierd`. ALE is also configured to ignore `tsserver` to avoid overlap with CoC.
- `:TSCheck`, `:Lint`, `:Knip` shell out via `vim-dispatch` and route results to the quickfix list; `<leader>q` opens it (`botright copen`).

## Git integration

`.gitconfig` wires Neovide as both `diff.tool` and `merge.tool`. The custom `git nd` / `git ndc` aliases launch `neovide --fork -c DiffviewOpen ...` for whole-repo diffs (no args) or fall through to per-file `git difftool -t neovide` (with file paths/refs). The plain `git d` / `git dc` aliases are the same idea against the default mvim difftool. Editor for commit messages is `mvim -f`.

Several aliases take a **bare number** as shorthand for `HEAD~N` via a smart shell function: `d N`, `nd N`, `rbi N`, `rs N` expand to `difftool HEAD~N` / diffview at `HEAD~N` / `rebase -i HEAD~N` / `reset --soft HEAD~N`. A single numeric arg triggers the expansion; anything else (a file path, a ref like `origin/main`, `--root`, or zero args) passes straight through to the underlying git command. The `d`/`nd` functions `cd "./$GIT_PREFIX"` first, since `!` shell aliases run from the repo root and would otherwise mis-resolve relative file paths given from a subdirectory. When changing this scheme, keep the numeric-detection `case` and the `GIT_PREFIX` guard intact.

The global gitignore lives at `git/ignore` in this repo, symlinked to `~/.config/git/ignore` (git's XDG default — no `core.excludesfile` setting is needed in `.gitconfig`). It's the *global* excludes file, applied to every repo on this machine. **Distinct from the repo's own `.gitignore`** at the root, which only ignores machine-local files within this repo (vim plugins, `hammerspoon/local.lua`, etc.). Don't conflate them — a prior misstep (commit `0c39b43`) symlinked the repo's `.gitignore` to `~/.gitignore` and had to be reverted.

## Hammerspoon

`~/.hammerspoon` is a **directory** symlink to `hammerspoon/` (not per-file), so `hammerspoon/init.lua` and `~/.hammerspoon/init.lua` are the same inode — editing the repo file IS editing the running config. Never `ln -sf` the init.lua paths: source and dest resolve to the same file, producing a self-loop ("Too many levels of symbolic links"); verify topology by `readlink`-ing the parent *directory*, not the file. The config auto-reloads on save via `hs.pathwatcher` — but **only on atomic editor-style saves, not in-place/programmatic writes** through the symlink: FSEvents doesn't deliver the event for a write that lands on the real repo path, so a tooling edit to `init.lua` needs a **manual menubar "Reload Config"** to go live (you can't reliably nudge the watcher from a shell). The same symlink/FSEvents quirk affects the iTerm2 dynamic-profile file. `init.lua` also loads `hs.ipc`, so the running config is queryable from the shell (`hs -c "return hs.accessibilityState()"`). Two responsibilities:

1. **Per-window/per-app homing.** *Bulk* re-homing (every managed window at once, via `homeAllManagedWindows`) fires on three triggers: (a) the 0.5s post-load initial pass, (b) `hs.screen.watcher` (monitor connect/disconnect/reconfigure), (c) `hs.caffeinate.watcher` `systemDidWake` (after sleep). *Per-window* placement (`placeWindow`) additionally fires as managed windows **appear and get titled**, via an `hs.window.filter` subscribed to `windowCreated` + `windowTitleChanged` (title-pattern `WINDOW_RULES` only match once iTerm2 sets the title, which is after `windowCreated`). This per-window path was once removed (commit `36d8339`) because it caused a feedback loop with iTerm2 (setFrame → char-grid snap → prompt redraw → OSC title escape → `windowTitleChanged` → setFrame → …). It's back, made safe by **placing each window at most once**: `placeWindow` records a window's id in `placedWindows` the first time it's placed (on appear, on its first matching title, or by any bulk pass) and then leaves it alone forever. So the re-fired events can't re-home a window — which both kills the feedback loop *and* means a manual resize/move sticks and ordinary title changes (iTerm2 tracking cwd, Vim tracking the filename) don't snap it back. `windowDestroyed` clears the record so a reused id can't suppress a genuinely new window; the table resets on reload. Bulk passes always re-home (ignoring the record) but also refresh it. Resolution order:
   - **`WINDOW_RULES`** (checked first, first-match-wins). Each rule has an exact `app` name, optional `titlePattern` (Lua pattern), then either a single `screen` + `placement(sf) → frame`, or an ordered `placements` candidate list (see below). Use this when you want to pin a specific window — e.g. an iTerm2 window with a title containing `config` goes to the bottom third on the `LG Ultra HD` monitor.
   - **`APP_PLACEMENTS`** (fallback). Map of app name → either a placement function (placed on `MAIN_SCREEN_NAME`) or an ordered candidate list. Currently: `Neovide`/`MacVim`/`Code` → `centeredWithMargin`, `Juggler` → `leftDock(480)`.

   **Ordered placement candidates.** Both `APP_PLACEMENTS` entries and `WINDOW_RULES` can resolve to a list of `{ screen, placement }` candidates instead of a single one; `resolvePlacement` returns the **first candidate whose target monitor is connected** (`findScreen` returns nil for an absent monitor). A candidate with its `screen` omitted or `""` targets `hs.screen.primaryScreen()` (always connected) — so a trailing `{ placement = h.fill }` is a catch-all fallback (e.g. *external monitor if present, else fullscreen on the built-in display*). If no candidate's screen is connected, the window is left untouched. `h.fill` (fullscreen) is among the exposed helpers.

   For title-pattern rules to take effect, the title needs to be set *before* one of the three trigger events fires. Practical workflow: open the iTerm2 window, set its title to e.g. `config` (Cmd+I → Window Title, or `echo -ne "\033]0;config\007"` in the shell), then trigger a re-home — toggling display mirroring or putting the lid down for a few seconds will work, otherwise the rule kicks in on the next monitor change / sleep-wake naturally.
2. **F18-chord window-placement modal.** Hold F18 and tap a key: `f` (fill), `1`/`2`/`3` (top/middle/bottom third), `q`/`w` (top/bottom half), `a`/`s` (left/right half), or `h` (home — re-run the homing pass on all managed windows, same code path as monitor change / wake). Full key map and rationale in the comment block at the top of `hammerspoon/init.lua`.

**"Placement keys dead / auto-layout dead" = lost Accessibility, NOT Secure Input.** Both the F18 trigger and the placement keys use Carbon `RegisterEventHotKey`, which **Secure Input does not block** (Secure Input blocks `CGEventTap`, the keylogger path). Every placement path ends in `win:setFrame(...)`, which needs the **Accessibility** permission and silently no-ops without it — so a revoked Accessibility grant is the real signature of dead placement + dead auto-layout (auto-layout is keyboard-free, so Secure Input is logically irrelevant to it). `init.lua` accordingly checks `hs.accessibilityState()` — the F18 overlay and a load-time alert both point at Accessibility — rather than the old `secureInputActive()` guard, which was a red herring that misdiagnosed this twice. (Aside: Secure Input can get stuck owned by a dead PID when a login-item app grabs it and quits; that's a fresh per-login leak, cleared on logout, and unrelated to the placement keys.)

### Per-machine config: `hammerspoon/local.lua`

`MAIN_SCREEN_NAME`, `APP_PLACEMENTS`, and `WINDOW_RULES` are **not** in `init.lua` — they live in `hammerspoon/local.lua`, which is **gitignored** (each machine has its own). `init.lua` exposes the placement helpers (`centeredWithMargin`, `leftDock(width)`, `rightOf(width)`, `fill`, the `topThird`/`middleThird`/`bottomThird` and `topHalf`/`bottomHalf`/`leftHalf`/`rightHalf` family) to the local file via a `helpers` argument; the local file returns the per-machine config table.

`install.sh` writes an empty stub at `hammerspoon/local.lua` if one doesn't exist, so a fresh install never errors on a missing file. The stub is a no-op that returns empty config — edit it (or copy from `local.lua.example` for a starting point) to enable auto-placement on this machine.

If `local.lua` is missing, the homing logic silently no-ops (the F18 modal still works fine). If `local.lua` has a runtime error, an `hs.alert` shows it on reload.

Adding a managed window in `local.lua`:
- **By app**: append to `app_placements`. Reuse a built-in helper (`h.centeredWithMargin`, `h.leftDock(width)`, `h.rightOf(width)`, `h.fill`, `h.topThird`/`h.middleThird`/`h.bottomThird`, `h.topHalf`/`h.bottomHalf`, `h.leftHalf`/`h.rightHalf`), or write a new placement function (takes the screen frame `sf`, returns `{x, y, w, h}`). The value can be a single helper or an ordered `{ {screen, placement}, … }` candidate list for monitor fallback.
- **By window title**: append to `window_rules`. Mark the target window's title (in iTerm2: Cmd+I → Window Title; in any shell: `echo -ne "\033]0;config\007"`) so it matches your `titlePattern`.

App names are matched exactly via `app:name()` (no Xcode-vs-Code fuzzy collisions). Screen names need exact matches too — every screen-config change posts an `hs.alert` listing connected screen names so you can copy the right one in. Project convention: "vertical" = stacked rows, "horizontal" = side-by-side columns (opposite of CSS/Moom).

### hidutil remaps (Caps Lock → F18, + per-machine local config)

`hidutil` key remaps are applied in **two layers**, mirroring the hammerspoon `init.lua` / `local.lua` split:

1. **Universal** (committed) — Caps Lock (`0x700000039`) → F18 (`0x70000006D`), the Hammerspoon modal-entry trigger. Lives in the launchd plist `launchd/com.nielsmadan.hidutil-capslock-to-f18.plist` **and** in `install.sh`. The Moonlander should also be configured (via Oryx) to send F18 from a free key.
2. **Per-machine** (gitignored) — `launchd/hidutil.local.sh`, a shell snippet of extra `hidutil` calls for *this machine only*. Sourced **after** the universal set, so it can override per device. `install.sh` writes an empty stub if missing and symlinks it to the fixed path `~/.config/hidutil/local.sh`; the plist sources that fixed path at login (the same fixed-location trick hammerspoon uses, since a committed/symlinked plist can't know the repo's path). Committed template: `launchd/hidutil.local.sh.example`.

Both the plist (at login) and `install.sh` (immediately, so it's live without a logout) apply the universal remap, then source `~/.config/hidutil/local.sh` if present. Because `hidutil --set` **replaces** a matched device's entire `UserKeyMapping`, a scoped per-machine `--set` that should coexist with Caps→F18 on that device must re-include the Caps→F18 entry.

Example per-machine use (this is what the ISO-keyboard machine's `hidutil.local.sh` does): remap the key below Esc, which on a Mac ISO/international keyboard emits `0x35` and renders as the useless section sign (`§`/`±`), so its *source* becomes `0x64` (Non-US `\`) — producing `` ` ``/`~` like US/ANSI. It's scoped via `--matching '{"Product":"Apple Internal Keyboard / Trackpad"}'` so external keyboards keep a normal backtick. **Caveat:** `VendorID`/`ProductID` `0x0`/`0x0` is a `hidutil` *wildcard* (matches every HID service), so the built-in keyboard must be matched by its `Product` string, not by ID.

If a remap stops working after a sleep/wake cycle, re-run the LaunchAgent (re-applies the universal set + sources the local file):

```sh
launchctl kickstart gui/$(id -u)/com.nielsmadan.hidutil-capslock-to-f18
```

Or just the universal Caps Lock → F18 directly:

```sh
hidutil property --set '{"UserKeyMapping":[{"HIDKeyboardModifierMappingSrc":0x700000039,"HIDKeyboardModifierMappingDst":0x70000006D}]}'
```

## iTerm2

`iterm2/` holds a dynamic profile (symlinked into `~/Library/Application Support/iTerm2/DynamicProfiles/`), a colorscheme (`rc.itermcolors`, imported manually inside iTerm2), and `SaveWindowArrangement.py`.

`SaveWindowArrangement.py` is symlinked into iTerm2's `Scripts/AutoLaunch/` dir, so it runs as a long-lived daemon at iTerm2 startup. It does two things: (1) registers the `save_window_arrangement` RPC, bound to **Cmd+S** via a key mapping in `dynamic-profile.json` (action `60` = "Invoke Script Function") — on an untitled window it prompts for a name, sets that as the window title, then saves; (2) auto-saves any window that has a title set, re-saving its named arrangement (name = the title) on a debounce whenever it changes. A window is "known"/auto-saved **iff it has an iTerm2 window title** — the same titles used for Hammerspoon `WINDOW_RULES`. Untitled windows are ignored. Changing the RPC name or the Cmd+S binding means editing both the script and `dynamic-profile.json` in lockstep.

`CloneRepoToTab.py` is the second AutoLaunch daemon (same lifecycle as `SaveWindowArrangement.py`). It registers the `clone_repo_to_tab` RPC, bound to **Cmd+Ctrl+N** in `dynamic-profile.json`. On trigger it resolves the active session's git repo, then scans the **current window's** tabs for that repo's family of sibling checkouts **open** in it (siblings = same parent dir + same base name with trailing digits stripped) and auto-picks the target by **filling the lowest gap** in the family (`select_sibling_slot`). Each open sibling occupies a *slot* = its trailing number, but a **bare name** (no digit suffix) counts as **slot 1** — the first checkout is "the first" whether it's named `foo` or `foo1`. The target is the smallest slot ≥ 1 that's unoccupied, named `base + slot`: with a hole like `foo1, foo3, foo4` it fills `foo2`; with `foo2, foo3` (no `foo1`) it fills `foo1`; a contiguous run like `foo`/`foo1` + `foo2` + `foo3` has no gap so it goes to `foo4` (the old highest-slot + 1 behaviour). Selection is **deterministic** — independent of which sibling triggered it. It then shows an **OK/Cancel** confirmation. **If that sibling directory already exists** on disk, the dialog offers to "open a new tab there (no clone)"; on OK it just opens the tab pointed at the existing directory (splits recreated, every pane in that directory), nothing is cloned, trusted, or copied. **Otherwise** the dialog offers to clone `<origin>` into the new sibling; on OK it creates the empty directory, opens the new tab (titled with the name, same split structure), then sends a shell command into the main pane that runs `git clone <origin> .`, then `mise trust .`, then copies every `.env` file found in the source repo (root and any subdirectories, mirroring their relative paths via `mkdir -p`), then runs `lefthook install` if the freshly-cloned repo has a lefthook config (`lefthook.{yml,yaml,toml,json}` or the dotted variants, in the repo root) — so the user can watch progress. **New-tab placement** follows the gap: `side = "right"` places it immediately right of the sibling *below* the gap (the common case — e.g. `foo2` right of `foo1`), `side = "left"` places it immediately left of the lowest open sibling (when filling below the minimum — e.g. `foo1` left of `foo2`). The `.env` walk prunes `.git`, `node_modules`, `.venv`, `venv`, and `__pycache__`. The lefthook step is a self-gating statement (it checks for the config in the cloned cwd at runtime, since the dir doesn't exist when the command is built). Because targeting fills gaps in the *open* family (not a filesystem skip-existing scan), triggering repeatedly walks through the missing slots and then off the top; if the picked directory already exists on disk it's opened rather than cloned. Setup errors (not a git repo, no `origin` when cloning, name exists but isn't a directory, mkdir failure) abort with an `iterm2.Alert` before the tab is created; clone failures surface in the pane as git's own stderr. The RPC body is fire-and-forget — the real work runs as an `asyncio` task — because iTerm2's RPC dispatcher has a short timeout that the confirm dialog + clone easily exceed. The pure helpers (`select_sibling_slot`, `sibling_base`/`sibling_number`/`is_sibling`, `resolve_repo_root`, `resolve_origin_url`, `compute_destination`) live in `iterm2/clone_repo_lib.py` and have `unittest` tests in `iterm2/test_clone_repo_lib.py` — run via `python3 iterm2/test_clone_repo_lib.py`.

`install.sh` also writes two iTerm2 `defaults` (default-profile GUID + 10% inactive-pane dimming) — but **only when iTerm2 is not running**. iTerm2 flushes its in-memory prefs to disk on quit and would clobber any `defaults write` made while it was open. If install reports `skip iTerm2 defaults`, quit iTerm2 and re-run `install.sh`. (The plist it clobbers is `com.googlecode.iterm2.plist`; the same rule applies to any hand/script edit of that file — do it only while iTerm2 is fully quit.)

**Restored windows use a frozen profile snapshot.** A restored pane/window keeps the profile settings that were live when its arrangement was saved — it does **not** re-read `dynamic-profile.json`. So a dynamic-profile change only affects sessions started *after* the change; a plain new tab heals only new panes, and "some panes behave differently after a profile edit" is expected. Worse, the `SaveWindowArrangement.py` daemon auto-saves titled windows on a debounce, so a *briefly*-toggled profile key gets baked into every saved arrangement inside `com.googlecode.iterm2.plist` and persists there long after the live profile is reverted — the daemon can re-pollute arrangements any time a polluted window is open when it next fires.

**Claude Code + scrollback:** CC repaints the entire alternate screen every frame instead of scrolling lines off the top, so iTerm2's `Scrollback in Alternate Screen` profile key is **inert for CC** — don't add it to `dynamic-profile.json` (it only lets the SaveWindowArrangement daemon re-pollute arrangements, pure downside). Native mouse-wheel scrollback for CC comes instead from `CLAUDE_CODE_DISABLE_ALTERNATE_SCREEN=1` in Claude Code's own `settings.json` env (equivalent to `"tui": "default"`; lives in the aiconf config, outside this repo). That renders CC on the main screen so the terminal owns selection / `Cmd`-click URLs / real scrollback, at the cost of `Ctrl+O` transcript view and in-app mouse.

## SSH profiles and tmux

`iterm2/dynamic-profile.json` carries two SSH profiles (`ssh: mini`, `ssh: barney`); the Default and `rc` profiles have `Custom Command = No` and just launch the local shell — **nothing local ever starts tmux**, the only local footprint is an inert `~/.tmux.conf` symlink.

Current approach: the SSH profiles run `ssh -t <host> /opt/homebrew/bin/tmux -CC new -A -s main` — tmux control mode (`-CC`) so splits follow the *remote* directory and the session persists across disconnect / sleep / network changes (this is the supported way to get remote-dir-following splits; iTerm2's native SSH "reuse directory" does not do it reliably). Trade-offs vs native it2ssh: loses drag-drop/right-click file transfer, inline images (`imgcat`), and mosh — judged acceptable (scp/rsync from a local pane still work). Note: the `⌘D`-split behaviour here was the chosen direction but was **not user-confirmed** at last touch, and the profile changes were left uncommitted.

Gotchas:
- **Absolute `/opt/homebrew/bin/tmux` is mandatory, not cosmetic.** Bare `tmux` is not on PATH for a non-interactive `ssh host cmd` (Homebrew's PATH is only wired up in login/interactive shells via `path_helper`), so `ssh -t <host> tmux …` dies "command not found" and the iTerm2 session "ends" instantly. tmux must also be installed on the remote (`brew install tmux`): mini has it; **barney still needs it** before its profile works.
- **Open each profile once, then `Cmd+T` / drag-tab-out** for more windows. Don't `Cmd+O` the same profile twice — it re-runs the whole command and attaches a *second* `-CC` client to the same `-s main` session, so the two clients mirror in lockstep or fight.
- tmux `-CC` renders panes on a shared integer character grid (a binary-split tree with all windows forced to one size), so splits come out uneven with gray "empty" areas; no setting fixes it (native iTerm2 panes are pixel-positioned).
- **mini's home is `/Users/nielsm` (user `nielsm`); this Mac is `/Users/nielsmadan`.** That mismatch is the root of the recurring `ssh mini … [Errno 2] No such file or directory: '/Users/nielsmadan'` error under it2ssh's "reuse directory" (it feeds mini's conductor the profile's *local* fallback path) — another reason the profiles use tmux `-CC` rather than native SSH.

`tmux/tmux.conf` (symlinked to `~/.tmux.conf` by `install.sh`'s `link tmux tmux/tmux.conf`) is deliberately minimal — **truecolor passthrough is the only load-bearing reason it exists**: `default-terminal tmux-256color` + `terminal-overrides …:Tc` stop tmux stripping truecolor (matters for nvim/harlequin colors). Also kept: `history-limit 50000` and the `update-environment` env-passthrough line. Dropped on purpose: `mouse on` (iTerm2 handles mouse/selection natively in `-CC` and it fights) and the `pane_current_path` prefix-key split bindings (dead weight in `-CC`, where you split with `⌘D`/`⌘T`). `tmux/inherit-dir.sh` exists but is untracked, unwired, and inert (calls bare `tmux`) — ignore it.

Forwarded ssh-agent sockets go stale inside long-lived tmux; `.zshrc`'s `refresh_ssh_auth_sock` precmd hook repairs that (see the Zsh section).

## Finicky

[Finicky](https://github.com/johnste/finicky) (Homebrew cask, **not** mise — it's a GUI `.app`) is set as the system default browser and routes every clicked link: personal → Brave, dev hosts → Chromium, client/customer URLs → LibreWolf (each in its own container).

The config is **split** to keep client identities out of the repo, mirroring the `hammerspoon/local.lua` / `hidutil.local.sh` pattern:

- **`finicky/finicky.ts`** (committed, symlinked to `~/.finicky.ts`) — the routing engine, `DEV_MATCHERS`, and `defaultBrowser`. Names no client. It `import`s `LOCAL` from `./finicky.local`.
- **`finicky/finicky.local.ts`** (**gitignored**) — `export const LOCAL`, an array of `{ container, match: [globs] }` entries holding all the identifiable routing (clients *and* the own `mathfiend` product). `install.sh` writes an empty `export const LOCAL = []` stub if missing so the import never fails on a fresh box; `finicky/finicky.local.ts.example` is the committed template.

**It must be `.ts`, not `.js`.** finicky resolves the `~/.finicky.ts` symlink to its real repo path, then bundles with esbuild — so the relative `import "./finicky.local"` resolves against `finicky/`. A `.js` config is Babel-staged into a cache dir *first* and esbuild bundles from there, which breaks the relative import.

Routing mechanics: a single guarded `rewrite` rule turns a matched URL into the `ext+container:name=<container>&url=<href>` scheme (read by LibreWolf's [Open external links in a container](https://addons.mozilla.org/firefox/addon/open-url-in-container/) add-on), and a handler sends `ext+container:*` to LibreWolf. The rewrite is guarded against re-rewriting an already-rewritten URL so rules can't chain; `containerFor()` returns the first matching entry. Shared services (GitHub, App Store Connect, AWS, Firebase, …) are scoped by path/ID/org/region so they don't collide across containers or hijack personal browsing. **Container names are case-sensitive** and must match those created in LibreWolf exactly.

## Shell prompt

`.zshrc` puts `~/.zsh/pure` on `fpath` and runs `prompt pure`. If the directory is missing, `prompt pure` fails silently and zsh falls back to its default `%m%#` prompt — `install.sh` clones `sindresorhus/pure` into `~/.zsh/pure` to prevent that.

## Zsh: no framework

`.zshrc` has no oh-my-zsh or plugin manager — don't add one. The pieces that replace it:

- `zsh-autosuggestions` and `zsh-syntax-highlighting` are `source`d directly from `~/.zsh/` (cloned there by `install.sh`, same pattern as pure). Their `source` lines must stay at the **very end** of `.zshrc`, after all custom `zle -N`/`bindkey`, with autosuggestions before syntax-highlighting.
- `compinit` uses the cached `-C` fast path (gated on a 24h-fresh `~/.zcompdump`). Keep that guard — don't replace it with a bare `compinit`.
- **Completions for mise-installed CLIs** are generated by the `_zcompgen` loop just above `compinit`. Homebrew tools drop a `_<tool>` into `…/share/zsh/site-functions` (already on `fpath`), but mise-installed CLIs don't — so for those the loop runs each tool's own generator (e.g. `gh completion -s zsh`) once into `~/.zsh/completions/_<tool>` and puts that dir on `fpath`. It forks nothing on a normal startup (only generates when a file is missing). **When you add a mise tool that has shell completion, add a `tool 'generator-cmd'` line to `_zcompgen`** (generator must print a `#compdef` script to stdout; leading blank lines are stripped). Tools that already ship a `site-functions/_<tool>` (most brew installs) or are covered by zsh's bundled completions (`npm`, `ruby`, `gem`) need no entry. HashiCorp-style `complete -C` tools (`terraform`, `vault`) use a different mechanism (`bashcompinit`) and are deliberately omitted. After a major tool upgrade, `rm ~/.zsh/completions/_<tool>` to regenerate (that dir is a machine-local cache in `$HOME`, not tracked in this repo).
- The rest is plain aliases/functions: `g=git` (other git shortcuts are `.gitconfig` aliases), the eza `ls`/`ll`/`la`/`l` aliases, `zoxide init`, and an `extract` function. mise is activated once via its own `eval` — don't add an oh-my-zsh mise plugin on top (double-activates).
- **`refresh_ssh_auth_sock` precmd hook** (registered via `precmd_functions+=()`, right after `set_tab_title`) repairs the forwarded ssh-agent socket inside long-lived tmux: tmux captures `SSH_AUTH_SOCK` at first attach and ssh removes that forwarded socket when the connection drops, so after detach/reconnect the panes point at a dead socket. It's **gated on `$TMUX`** (the function isn't even defined outside tmux, so normal local shells — this Mac never runs tmux — are untouched) and short-circuits on a `-S` live-socket check (returns instantly on the common path: no `tmux` fork per prompt, and it won't clobber a deliberately-set agent), only repulling `tmux show-environment SSH_AUTH_SOCK` when the socket is genuinely gone. Pure universal wiring, so it lives in the committed `.zshrc`; the machine that benefits is mini (running the same committed `.zshrc`), inert here.

## Tool versions

`mise/config.toml` (symlinked to `~/.config/mise/config.toml`) pins node/ruby/python/java/bun/go/fzf/pnpm/sops/age. `mise activate` is hooked in `.zshrc`.

Global npm CLIs are managed through mise's `npm:` backend (`npm:wrangler`, `npm:firebase-tools`, `npm:agent-browser`, `npm:@agentclientprotocol/claude-agent-acp`) so they survive `node` version bumps and stay reproducible. Add new ones with `mise use -g npm:<pkg>` rather than `npm install -g`. `claude-agent-acp` is load-bearing — it's the ACP bridge `nvim/lua/plugins/ai.lua`'s CodeCompanion `claude_code` adapter spawns.

**mise vs brew.** Default to **mise** for standalone dev CLIs and language-ecosystem tools — version-pinned in `mise/config.toml` and auto-replicated across machines. Use **brew** for GUI casks (`.app`s like Finicky), long-running daemons/services, C libraries, and tools needing a launchd unit or absolute path. When moving a tool brew→mise, `brew uninstall` it first so the mise shim wins on `PATH`.

**Vault via mise/aqua:** install with an explicit pin (`aqua:hashicorp/vault@<version>`), **not** `@latest` — aqua's resolver picks bad tags (e.g. `2.0.1` has no darwin build and 404s). Pinning also sidesteps the BSL-relicense tap churn.

**Railway CLI** is mise-managed (pinned in `mise/config.toml`, sops-wrapped so `RAILWAY_API_TOKEN` is injected per call). Upgrade with `mise upgrade railway`, not `railway upgrade` (fails: "Could not detect install method"). It needs a **personal account** token, not a team/workspace token — a team token fails the CLI's `me { email }` identity gate, making every command return "Unauthorized". Generate an unscoped token at railway.com/account/tokens; verify with `railway whoami`. The sops-injected env var shadows any `railway login` session, so the token is the only auth lever.

## Secrets management

Dev API keys (e.g. `JINA_API_KEY`) live in `secrets/secrets.yaml` in this repo, encrypted with [SOPS](https://github.com/getsops/sops) using [age](https://github.com/FiloSottile/age) recipients. Each Mac has its own age identity at `~/.config/sops/age/keys.txt` (mode 600); the corresponding **public** keys are listed in `.sops.yaml` at the repo root. The encrypted file is safe to commit — that's the whole point.

Why this setup: API keys must not sit in long-lived shell env, because Claude Code agents (and similar tools) routinely run `env`/`printenv`/cat configs, and those values end up in transcripts. SOPS' `exec-env` injects decrypted values into a subprocess only — the parent shell never sees them.

Architecture:
- **`.sops.yaml`** (repo root) — SOPS creation rules. Lists allowed age recipients (public keys, one per Mac). Plaintext, committed.
- **`secrets/secrets.yaml`** (repo) — encrypted YAML. Variable names are visible (diff-friendly); values are AES-256-GCM ciphertext, decryptable only by listed recipients. Committed.
- **`secrets/secrets-mini.yaml`** (repo) — encrypted YAML scoped to the Mac mini only (its recipient list in `.sops.yaml` is deliberately limited to the mini's age key). Holds secrets that should not exist on any other machine. When adding a new Mac to `.sops.yaml`, **do not** add it as a recipient of `secrets-mini.yaml` — leave that file's recipient list alone.
- **`SOPS_AGE_KEY_FILE`** — env var set in `.zshrc` to `~/.config/sops/age/keys.txt`. macOS' default location for SOPS is `~/Library/Application Support/sops/age/keys.txt` (path with spaces); we use the cleaner XDG location.
- **CLI wrappers** in `.zshrc` (`claude`, `codex`, `gemini`) invoke each tool via `sops exec-env "$SOPS_SECRETS" --` so keys land only in that subprocess.
- **HTTP-based MCP servers** (e.g. Jina, Todoist) in `~/.claude.json` use `${ENV_VAR}` headers; Claude Code interpolates those at startup. Since our `claude` wrapper goes through `sops exec-env`, Claude Code receives the env var. The parent shell does not.
- **stdio MCP servers** with env-var deps can use `command: "sops"` `args: ["exec-env", "<repo>/secrets/secrets.yaml", "--", "<server>"]` directly, so even Claude Code's own process never sees their keys.

Fresh-machine bootstrap:
1. Clone the repo and run `install.sh` — generates an age identity at `~/.config/sops/age/keys.txt` if missing and prints the public key.
2. On a Mac that already decrypts: append the new public key to `.sops.yaml`, then `sops updatekeys ~/rc/secrets/secrets.yaml`. Commit + push.
3. On the new Mac: `git pull`. Verify with `sops -d --extract '["JINA_API_KEY"]' ~/rc/secrets/secrets.yaml`.

Adding a new secret:
1. `sops edit ~/rc/secrets/secrets.yaml` — opens `$EDITOR` (mvim) on plaintext.
2. Add a line: `OPENAI_API_KEY: sk-xxx`. Save & exit; SOPS re-encrypts in place.
3. `git add secrets/secrets.yaml && git commit && git push` so other Macs can pull.
4. If the new env var is referenced by a CLI tool that doesn't auto-receive env from the wrappers, add a wrapper function in `.zshrc`.

Rotation: `sops edit ~/rc/secrets/secrets.yaml`, change the value, save. Commit + push. No restart needed; SOPS reads the file each call. The entry's old ciphertext disappears from the file (history lives in `git log`).

Migration status: keys still in `~/.airc` work via the legacy plain-env path. Once a key is in `secrets.yaml` and verified via `sops -d --extract`, remove the corresponding `export` line from `~/.airc` so it's not duplicated in shell env.

Note on `.kdbx`: the file at `~/syncthing/keepass/dev-secrets.kdbx` is left in place for personal-life secrets browsed via KeePassXC (different security/UX posture from dev secrets).

## Local-only files (not in this repo)

`.zshrc` sources `~/.airc`, `~/.devrc`, and `~/.zshrc.local` if present (`.devrc` is in the repo and symlinked in; the others are user-local). `.gitconfig` includes `~/.gitconfig-local`. Don't expect to find these here. (`~/.airc` is being phased out as keys migrate to fnox — see the Secrets management section.)
