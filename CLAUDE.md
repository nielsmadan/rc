# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository purpose

Personal dotfiles for macOS. `install.sh` symlinks files from this repo into `$HOME` (and a few other places like `~/.config/nvim`, `~/.config/kitty`, iTerm2's scripts dir). Editing a file here = editing the live config. Re-running `install.sh` is idempotent.

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

`.gitconfig` wires Neovide as both `diff.tool` and `merge.tool`. The custom `git d` / `git d1` / `git dc` aliases launch `neovide --no-fork -c DiffviewOpen ...` for whole-repo diffs (no args) or fall through to per-file `git difftool` (with args). Editor for commit messages is `mvim -f`.

## Hammerspoon

`hammerspoon/init.lua` is symlinked to `~/.hammerspoon/init.lua`. The config auto-reloads on save via `hs.pathwatcher`. Two responsibilities:

1. **Per-window/per-app homing.** Re-homes managed windows on three triggers, deliberately *not* on per-window events: (a) the 0.5s post-load initial pass, (b) `hs.screen.watcher` (monitor connect/disconnect/reconfigure), (c) `hs.caffeinate.watcher` `systemDidWake` (after sleep). Subscribing to `windowCreated` / `windowTitleChanged` caused a feedback loop with iTerm2 (setFrame → char-grid snap → prompt redraw → OSC title escape → re-place → repeat). Resolution order:
   - **`WINDOW_RULES`** (checked first, first-match-wins). Each rule has an exact `app` name, optional `titlePattern` (Lua pattern), target `screen` name, and a `placement(sf) → frame`. Use this when you want to pin a specific window — e.g. an iTerm2 window with a title containing `config` goes to the bottom third on the `LG Ultra HD` monitor.
   - **`APP_PLACEMENTS`** (fallback). Map of app name → placement function on `MAIN_SCREEN_NAME`. Currently: `Neovide`/`MacVim`/`Code` → `centeredWithMargin`, `Juggler` → `leftDock(480)`.

   For title-pattern rules to take effect, the title needs to be set *before* one of the three trigger events fires. Practical workflow: open the iTerm2 window, set its title to e.g. `config` (Cmd+I → Window Title, or `echo -ne "\033]0;config\007"` in the shell), then trigger a re-home — toggling display mirroring or putting the lid down for a few seconds will work, otherwise the rule kicks in on the next monitor change / sleep-wake naturally.
2. **F18-leader window-placement modal.** Hold F18 to enter, then `w` for window mode, then `f`/`v`/`b`/`h` for fill/rows/cols/home (re-run the homing pass on all managed windows — same code path as monitor change / wake), then `1`/`2`/`⇧1`-`⇧3` for the rows/cols submodes. Full key map and rationale in the comment block at the top of `hammerspoon/init.lua`.

### Per-machine config: `hammerspoon/local.lua`

`MAIN_SCREEN_NAME`, `APP_PLACEMENTS`, and `WINDOW_RULES` are **not** in `init.lua` — they live in `hammerspoon/local.lua`, which is **gitignored** (each machine has its own). `init.lua` exposes the placement helpers (`centeredWithMargin`, `leftDock(width)`, `bottomThird`) to the local file via a `helpers` argument; the local file returns the per-machine config table.

`install.sh` writes an empty stub at `hammerspoon/local.lua` if one doesn't exist, so a fresh install never errors on a missing file. The stub is a no-op that returns empty config — edit it (or copy from `local.lua.example` for a starting point) to enable auto-placement on this machine.

If `local.lua` is missing, the homing logic silently no-ops (the F18 modal still works fine). If `local.lua` has a runtime error, an `hs.alert` shows it on reload.

Adding a managed window in `local.lua`:
- **By app**: append to `app_placements`. Reuse `h.centeredWithMargin` / `h.leftDock(width)` / `h.bottomThird`, or write a new placement function (takes the screen frame `sf`, returns `{x, y, w, h}`).
- **By window title**: append to `window_rules`. Mark the target window's title (in iTerm2: Cmd+I → Window Title; in any shell: `echo -ne "\033]0;config\007"`) so it matches your `titlePattern`.

App names are matched exactly via `app:name()` (no Xcode-vs-Code fuzzy collisions). Screen names need exact matches too — every screen-config change posts an `hs.alert` listing connected screen names so you can copy the right one in. Project convention: "vertical" = stacked rows, "horizontal" = side-by-side columns (opposite of CSS/Moom).

### hidutil remap (Caps Lock → F18)

F18 is produced by `hidutil` remapping Caps Lock to it; the launchd plist `launchd/com.nielsmadan.hidutil-capslock-to-f18.plist` re-applies this at every login because `hidutil`'s mapping is **session-scoped** (lost across reboot and full logout). `install.sh` also runs hidutil directly during install so the mapping is live without a logout. The Moonlander should also be configured (via Oryx) to send F18 from a free key.

If the remap stops working after a sleep/wake cycle:

```sh
hidutil property --set '{"UserKeyMapping":[{"HIDKeyboardModifierMappingSrc":0x700000039,"HIDKeyboardModifierMappingDst":0x70000006D}]}'
```

Or `launchctl kickstart gui/$(id -u)/com.nielsmadan.hidutil-capslock-to-f18`.

## iTerm2

`iterm2/` holds a dynamic profile (symlinked into `~/Library/Application Support/iTerm2/DynamicProfiles/`), a colorscheme (`rc.itermcolors`, imported manually inside iTerm2), and `SaveWindowArrangement.py` (symlinked into iTerm2's Scripts dir).

`install.sh` also writes two iTerm2 `defaults` (default-profile GUID + 10% inactive-pane dimming) — but **only when iTerm2 is not running**. iTerm2 flushes its in-memory prefs to disk on quit and would clobber any `defaults write` made while it was open. If install reports `skip iTerm2 defaults`, quit iTerm2 and re-run `install.sh`.

## Shell prompt

`.zshrc` puts `~/.zsh/pure` on `fpath` and runs `prompt pure`. If the directory is missing, `prompt pure` fails silently and zsh falls back to its default `%m%#` prompt — `install.sh` clones `sindresorhus/pure` into `~/.zsh/pure` to prevent that.

## Tool versions

`mise/config.toml` (symlinked to `~/.config/mise/config.toml`) pins node/ruby/python/java/bun/go/fzf/pnpm. `mise activate` is hooked in `.zshrc`.

## Local-only files (not in this repo)

`.zshrc` sources `~/.airc`, `~/.devrc`, and `~/.zshrc.local` if present (`.devrc` is in the repo and symlinked in; the others are user-local). `.gitconfig` includes `~/.gitconfig-local`. Don't expect to find these here.
