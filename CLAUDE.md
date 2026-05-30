# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository purpose

Personal dotfiles for macOS. `install.sh` symlinks files from this repo into `$HOME` (and a few other places like `~/.config/nvim`, `~/.config/kitty`, iTerm2's scripts dir). Editing a file here = editing the live config. Re-running `install.sh` is idempotent.

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

`.gitconfig` wires Neovide as both `diff.tool` and `merge.tool`. The custom `git d` / `git d1` / `git dc` aliases launch `neovide --no-fork -c DiffviewOpen ...` for whole-repo diffs (no args) or fall through to per-file `git difftool` (with args). Editor for commit messages is `mvim -f`.

The global gitignore lives at `git/ignore` in this repo, symlinked to `~/.config/git/ignore` (git's XDG default — no `core.excludesfile` setting is needed in `.gitconfig`). It's the *global* excludes file, applied to every repo on this machine. **Distinct from the repo's own `.gitignore`** at the root, which only ignores machine-local files within this repo (vim plugins, `hammerspoon/local.lua`, etc.). Don't conflate them — a prior misstep (commit `0c39b43`) symlinked the repo's `.gitignore` to `~/.gitignore` and had to be reverted.

## Hammerspoon

`hammerspoon/init.lua` is symlinked to `~/.hammerspoon/init.lua`. The config auto-reloads on save via `hs.pathwatcher`. Two responsibilities:

1. **Per-window/per-app homing.** Re-homes managed windows on three triggers, deliberately *not* on per-window events: (a) the 0.5s post-load initial pass, (b) `hs.screen.watcher` (monitor connect/disconnect/reconfigure), (c) `hs.caffeinate.watcher` `systemDidWake` (after sleep). Subscribing to `windowCreated` / `windowTitleChanged` caused a feedback loop with iTerm2 (setFrame → char-grid snap → prompt redraw → OSC title escape → re-place → repeat). Resolution order:
   - **`WINDOW_RULES`** (checked first, first-match-wins). Each rule has an exact `app` name, optional `titlePattern` (Lua pattern), then either a single `screen` + `placement(sf) → frame`, or an ordered `placements` candidate list (see below). Use this when you want to pin a specific window — e.g. an iTerm2 window with a title containing `config` goes to the bottom third on the `LG Ultra HD` monitor.
   - **`APP_PLACEMENTS`** (fallback). Map of app name → either a placement function (placed on `MAIN_SCREEN_NAME`) or an ordered candidate list. Currently: `Neovide`/`MacVim`/`Code` → `centeredWithMargin`, `Juggler` → `leftDock(480)`.

   **Ordered placement candidates.** Both `APP_PLACEMENTS` entries and `WINDOW_RULES` can resolve to a list of `{ screen, placement }` candidates instead of a single one; `resolvePlacement` returns the **first candidate whose target monitor is connected** (`findScreen` returns nil for an absent monitor). A candidate with its `screen` omitted or `""` targets `hs.screen.primaryScreen()` (always connected) — so a trailing `{ placement = h.fill }` is a catch-all fallback (e.g. *external monitor if present, else fullscreen on the built-in display*). If no candidate's screen is connected, the window is left untouched. `h.fill` (fullscreen) is among the exposed helpers.

   For title-pattern rules to take effect, the title needs to be set *before* one of the three trigger events fires. Practical workflow: open the iTerm2 window, set its title to e.g. `config` (Cmd+I → Window Title, or `echo -ne "\033]0;config\007"` in the shell), then trigger a re-home — toggling display mirroring or putting the lid down for a few seconds will work, otherwise the rule kicks in on the next monitor change / sleep-wake naturally.
2. **F18-leader window-placement modal.** Hold F18 to enter, then `w` for window mode, then a flat terminal key: `f` (fill), `1`/`2`/`3` (top/middle/bottom third), `q`/`w` (top/bottom half), `a`/`s` (left/right half), or `h` (home — re-run the homing pass on all managed windows, same code path as monitor change / wake). Full key map and rationale in the comment block at the top of `hammerspoon/init.lua`.

### Per-machine config: `hammerspoon/local.lua`

`MAIN_SCREEN_NAME`, `APP_PLACEMENTS`, and `WINDOW_RULES` are **not** in `init.lua` — they live in `hammerspoon/local.lua`, which is **gitignored** (each machine has its own). `init.lua` exposes the placement helpers (`centeredWithMargin`, `leftDock(width)`, `rightOf(width)`, `fill`, the `topThird`/`middleThird`/`bottomThird` and `topHalf`/`bottomHalf`/`leftHalf`/`rightHalf` family) to the local file via a `helpers` argument; the local file returns the per-machine config table.

`install.sh` writes an empty stub at `hammerspoon/local.lua` if one doesn't exist, so a fresh install never errors on a missing file. The stub is a no-op that returns empty config — edit it (or copy from `local.lua.example` for a starting point) to enable auto-placement on this machine.

If `local.lua` is missing, the homing logic silently no-ops (the F18 modal still works fine). If `local.lua` has a runtime error, an `hs.alert` shows it on reload.

Adding a managed window in `local.lua`:
- **By app**: append to `app_placements`. Reuse a built-in helper (`h.centeredWithMargin`, `h.leftDock(width)`, `h.rightOf(width)`, `h.fill`, `h.topThird`/`h.middleThird`/`h.bottomThird`, `h.topHalf`/`h.bottomHalf`, `h.leftHalf`/`h.rightHalf`), or write a new placement function (takes the screen frame `sf`, returns `{x, y, w, h}`). The value can be a single helper or an ordered `{ {screen, placement}, … }` candidate list for monitor fallback.
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

`iterm2/` holds a dynamic profile (symlinked into `~/Library/Application Support/iTerm2/DynamicProfiles/`), a colorscheme (`rc.itermcolors`, imported manually inside iTerm2), and `SaveWindowArrangement.py`.

`SaveWindowArrangement.py` is symlinked into iTerm2's `Scripts/AutoLaunch/` dir, so it runs as a long-lived daemon at iTerm2 startup. It does two things: (1) registers the `save_window_arrangement` RPC, bound to **Cmd+S** via a key mapping in `dynamic-profile.json` (action `60` = "Invoke Script Function") — on an untitled window it prompts for a name, sets that as the window title, then saves; (2) auto-saves any window that has a title set, re-saving its named arrangement (name = the title) on a debounce whenever it changes. A window is "known"/auto-saved **iff it has an iTerm2 window title** — the same titles used for Hammerspoon `WINDOW_RULES`. Untitled windows are ignored. Changing the RPC name or the Cmd+S binding means editing both the script and `dynamic-profile.json` in lockstep.

`CloneRepoToTab.py` is the second AutoLaunch daemon (same lifecycle as `SaveWindowArrangement.py`). It registers the `clone_repo_to_tab` RPC, bound to **Cmd+Ctrl+N** in `dynamic-profile.json`. On trigger it resolves the active session's git repo, auto-picks the next sibling name (the repo root's folder name + 1, e.g. `dev2` → `dev3`; a name with no trailing digit gets `2`), then shows an **OK/Cancel** confirmation describing what it will do. **If that sibling directory already exists** (e.g. invoked from `dev2` with `dev3` already present), the dialog offers to "open a new tab there (no clone)"; on OK it just opens the tab pointed at the existing directory (splits recreated, positioned immediately right of the original tab, every pane in that directory), nothing is cloned, trusted, or copied. **Otherwise** the dialog offers to clone `<origin>` into the new sibling; on OK it creates the empty directory, opens the new tab (titled with the name, positioned right of the original, same split structure), then sends a shell command into the main pane that runs `git clone <origin> .`, then `mise trust .`, then copies every `.env` file found in the source repo (root and any subdirectories, mirroring their relative paths via `mkdir -p`) — so the user can watch progress. The `.env` walk prunes `.git`, `node_modules`, `.venv`, `venv`, and `__pycache__`. Because the target name is the immediate +1 (no skip-existing), this is a "walk to the next checkout, creating it if missing" command — to reach `dev4` from `dev2` when `dev3` exists, invoke again from `dev3`'s tab. Setup errors (not a git repo, no `origin` when cloning, name exists but isn't a directory, mkdir failure) abort with an `iterm2.Alert` before the tab is created; clone failures surface in the pane as git's own stderr. The RPC body is fire-and-forget — the real work runs as an `asyncio` task — because iTerm2's RPC dispatcher has a short timeout that the confirm dialog + clone easily exceed. The pure helpers (`next_sibling_name`, `resolve_repo_root`, `resolve_origin_url`, `compute_destination`) live in `iterm2/clone_repo_lib.py` and have `unittest` tests in `iterm2/test_clone_repo_lib.py` — run via `python3 iterm2/test_clone_repo_lib.py`.

`install.sh` also writes two iTerm2 `defaults` (default-profile GUID + 10% inactive-pane dimming) — but **only when iTerm2 is not running**. iTerm2 flushes its in-memory prefs to disk on quit and would clobber any `defaults write` made while it was open. If install reports `skip iTerm2 defaults`, quit iTerm2 and re-run `install.sh`.

## Shell prompt

`.zshrc` puts `~/.zsh/pure` on `fpath` and runs `prompt pure`. If the directory is missing, `prompt pure` fails silently and zsh falls back to its default `%m%#` prompt — `install.sh` clones `sindresorhus/pure` into `~/.zsh/pure` to prevent that.

## Tool versions

`mise/config.toml` (symlinked to `~/.config/mise/config.toml`) pins node/ruby/python/java/bun/go/fzf/pnpm/sops/age. `mise activate` is hooked in `.zshrc`.

Global npm CLIs are managed through mise's `npm:` backend (`npm:wrangler`, `npm:firebase-tools`, `npm:agent-browser`, `npm:@agentclientprotocol/claude-agent-acp`) so they survive `node` version bumps and stay reproducible. Add new ones with `mise use -g npm:<pkg>` rather than `npm install -g`. `claude-agent-acp` is load-bearing — it's the ACP bridge `nvim/lua/plugins/ai.lua`'s CodeCompanion `claude_code` adapter spawns.

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
