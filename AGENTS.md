# AGENTS.md

This file provides guidance to coding agents when working with code in this repository.

## Repository purpose

Personal dotfiles for macOS. `install.sh` symlinks files from this repo into `$HOME` (and a few other places like `~/.config/nvim`, `~/.config/kitty`, iTerm2's scripts dir). Editing a file here = editing the live config. Re-running `install.sh` is idempotent — in steady state every step short-circuits and `--quiet` prints nothing at all.

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

## `install.sh --check` and the git hooks

`install.sh` takes two flags:

- **`--check`** — dry run. Reports each pending change as a `would …` line, performs none of them, and exits **1** if anything is pending (0 when clean). Every side-effecting step in the script is gated behind the `pending()` helper, which counts the change and, under `--check`, prints it and returns non-zero so the caller skips the real work.
- **`--quiet`** — suppress the routine `skip …` chatter (via the `say()` helper); only lines for things that actually changed are printed.

Two steps are deliberately **excluded** from the pending count: the `hidutil property --set` re-apply and the iTerm2 `defaults write`. Both rewrite the same values every run (hidutil's `UserKeyMapping` is session-scoped and must be re-applied), so counting them would leave `--check` permanently dirty and the hook nag permanently on. `--check` skips both outright rather than reporting them.

`--check` also names what the `rm -rf "$dest"` inside `link()` would destroy — `(REPLACES EXISTING FILE)`, `(REPLACES EXISTING DIRECTORY)`, or the old target of a foreign symlink. That case only arises when a link target *moves*, which is exactly what a pull can do, so the warning is the point. `--check` only *warns*: a real run still deletes, with no backup. The delete never fires in steady state (the "already linked" check short-circuits first), which is what makes it look harmless.

**Hooks** live in the committed `githooks/` dir, wired up by `install.sh` setting `core.hooksPath` (that setting lives in `.git/config`, which is machine-local and never committed, so it has to be re-set per clone rather than shipped in the repo). `post-merge`, `post-rewrite` (covers `pull --rebase`, which `post-merge` misses) and `post-checkout` (gated on `$3 = 1`, a branch checkout) all `exec` the shared `githooks/_nudge.sh`. Those three are the full set that can leave a link target stale; `pre-push` is the wrong hook for this and was rejected — pushing doesn't change your working tree.

The hooks **only ever run `install.sh --check`** — they never re-link anything behind your back, and they always `exit 0` so a stale symlink can't fail the git operation that triggered it. A pull that leaves nothing stale prints nothing. Skip the whole mechanism on a machine by uncommenting `githooks` in `install.local`, which also unsets `core.hooksPath` if it currently points here.

The one step the hooks can't keep current is the Obsidian vimrc: it's the script's only interactive step, and it's now gated on a tty (and off under `--check`) so non-interactive runs don't die on EOF reading the prompt. The vault path isn't recorded anywhere, so a non-interactive run always skips it. That's harmless in practice — the existing symlink points into the repo, so content changes flow through automatically; only a *move* of `.obsidian.vimrc` would need an interactive re-run.

**Any interactive step you add must be gated the same way** (`[ -t 0 ]`, plus skipped under `--check`). The script runs under `set -e`, so a `read` that hits EOF with no tty returns non-zero and aborts the whole run *silently and part-way through* — the failure this rule exists for landed after every symlink but before `~/.zshrc.local`, the age identity, `hammerspoon/local.lua`, `finicky.local.ts` and the `install.local` stub were written, leaving the machine half-installed with a zero-ish-looking output.

### Why not lefthook

`lefthook` is installed on this machine (`lefthook = "latest"` in `mise/config.toml`), and `CloneRepoToTab.py` runs `lefthook install` inside repos it *clones* — but **this repo deliberately does not use it for its own hooks.** Don't "modernise" `githooks/` onto it; the availability of the binary was already weighed and rejected.

- **This is the bootstrap repo.** `install.sh`'s job is to bring up a fresh Mac, and it is what links mise's own config into place (`link mise mise/config.toml`) — so on a new box lefthook doesn't exist until *after* `install.sh` has run and `mise install` has finished. A `lefthook install` step inside `install.sh` would fail on exactly the machine that most needs setting up, reproducing the awkward `age-keygen not on PATH — run mise install then re-run install.sh` failure mode. The hand-rolled hooks are POSIX `sh` and work on a machine with nothing installed.
- It wouldn't remove the one manual step either: `lefthook install` is the same per-clone action as setting `core.hooksPath`, with a binary in front of it.
- Nothing it buys applies yet — no linter, no formatter, no staged-file globbing, nothing to parallelise.

**Revisit when** the repo grows real pre-commit work: shellcheck over `install.sh`, luacheck over `hammerspoon/`, `iterm2/test_clone_repo_lib.py` gating pushes. Three or four checks with skip conditions is where a declarative `lefthook.yml` starts beating hand-rolled shell. Below that, the next hook is a few lines of `sh` next to the existing ones.

## Per-machine install skip list (`install.local`)

Every `link` call in `install.sh` carries a short **alias** as its first argument (`gitignore`, `zshrc`, `nvim`, …). `install.local` (repo root, **gitignored**, one alias per line) is a per-machine opt-out: an uncommented alias means `install.sh` skips that target — it won't re-link it, and if the destination is currently a symlink into this repo it's **detached** into a real machine-local copy (`cp -R`) so it can be edited without affecting the repo. Re-comment the line to hand the target back to the repo symlink on the next run — **which destroys the detached copy**: the next `install.sh` `rm -rf`s that real file/dir and puts the repo symlink back, with no backup taken. Detaching is reversible; un-detaching is not. Salvage anything you want to keep out of the machine-local copy first (`install.sh --check` names it as `(REPLACES EXISTING FILE)` / `(REPLACES EXISTING DIRECTORY)` beforehand).

`install.sh` generates `install.local` on first run (at the end, after every `link` call) with all aliases listed but commented out, so the default file skips nothing. The alias list is single-sourced: `link()` calls `seen_key` to append each alias to a `SEEN_KEYS` array, and the stub is built from that — no separate hardcoded list to keep in sync. **When adding or removing a `link` call, just give it an alias; the file keeps itself current.**

An *existing* `install.local` is **merged, not left alone**: aliases added since it was written get appended (commented out, so behaviour is unchanged), and aliases it lists that match no `link` call are flagged with a `warn:` line. Before this merge existed, adding a `link` call left every already-installed machine's file silently stale — the new alias was simply absent, and you cannot skip a target you cannot see. Aliases that aren't plain `link` calls (`obsidian-vimrc`, `githooks`) call `seen_key` directly so they appear in the list too.

## Editor configuration

The Vim/Neovim split and keybinding synchronization rules are in [docs/editor-config.md](docs/editor-config.md).

## Git integration

`.gitconfig` wires Neovide as both `diff.tool` and `merge.tool`. The custom `git nd` / `git ndc` aliases launch `neovide --fork -c DiffviewOpen ...` for whole-repo diffs (no args) or fall through to per-file `git difftool -t neovide` (with file paths/refs). The plain `git d` / `git dc` aliases are the same idea against the default mvim difftool. Editor for commit messages is `mvim -f`.

Several aliases take a **bare number** as shorthand for `HEAD~N` via a smart shell function: `d N`, `nd N`, `rbi N`, `rs N` expand to `difftool HEAD~N` / diffview at `HEAD~N` / `rebase -i HEAD~N` / `reset --soft HEAD~N`. A single numeric arg triggers the expansion; anything else (a file path, a ref like `origin/main`, `--root`, or zero args) passes straight through to the underlying git command. The `d`/`nd` functions `cd "./$GIT_PREFIX"` first, since `!` shell aliases run from the repo root and would otherwise mis-resolve relative file paths given from a subdirectory. When changing this scheme, keep the numeric-detection `case` and the `GIT_PREFIX` guard intact.

The global gitignore lives at `git/ignore` in this repo, symlinked to `~/.config/git/ignore` (git's XDG default — no `core.excludesfile` setting is needed in `.gitconfig`). It's the *global* excludes file, applied to every repo on this machine. **Distinct from the repo's own `.gitignore`** at the root, which only ignores machine-local files within this repo (vim plugins, `hammerspoon/local.lua`, etc.). Don't conflate them — a prior misstep (commit `0c39b43`) symlinked the repo's `.gitignore` to `~/.gitignore` and had to be reverted.

## Hammerspoon

`~/.hammerspoon` is a directory symlink into this repo, so edits are live config changes; programmatic edits need an explicit reload. Placement, window-placement hotkeys, Accessibility/Secure Input, and per-machine configuration details live in [docs/hammerspoon.md](docs/hammerspoon.md).

## iTerm2

The AutoLaunch daemons are loaded once per iTerm2 start, and restored arrangements retain profile snapshots. Their RPC, testing, profile, and scrollback details live in [docs/iterm2.md](docs/iterm2.md).

## SSH profiles and tmux

The remote tmux protocol, key mappings, and stale-agent-socket behavior are in [docs/ssh-tmux.md](docs/ssh-tmux.md).

## Finicky

The split config, container routing, and case-sensitive names are documented in [docs/finicky.md](docs/finicky.md).

## Colima (container runtime)

Colima is the Docker runtime here, not Docker Desktop. Its explicit `mounts:` list is a security boundary: it must expose only the workspace and `/var/folders`. Full mount, isolation, and stale-VM diagnostics live in [docs/colima-hardening.md](docs/colima-hardening.md).

## `bin/` — standalone scripts on PATH

`bin/` holds self-contained helper scripts, each symlinked individually into `~/.local/bin` (already on `PATH` from `.zshrc`) by its own `link` call in `install.sh` — **not** a directory symlink, since `~/.local/bin` also holds unrelated machine-local binaries. Adding a script means adding a `link <alias> bin/<name> ~/.local/bin/<name>` line; the `install.local` skip list keeps itself current from the alias.

The current set turns media into something an agent can actually read — text or a single image. The first two were ported out of a Claude skill's `scripts/` dir and generalized. All self-document via `--help`, which prints their own leading comment block, so that block *is* the documentation — keep it accurate when changing behaviour.

- **`yt-transcript <url> [--lang xx] [--timestamps]`** — prints a `METADATA:` line (`id | upload_date | uploader | title`) and the path to a cleaned, de-duplicated transcript in `TMPDIR`. Prefers manual captions over auto-generated. Exits **0** with a `NO_CAPTIONS:` line when there are none, so a caller can fall back to the title/description (or to `transcribe`) instead of treating it as an error.
- **`transcribe <src> [--model N] [--timestamps]`** — local Whisper speech-to-text for anything without captions: podcasts, Twitch VODs, meeting/screen recordings, voice memos. Covers exactly the hole `yt-transcript` leaves.
- **`video-frames`** — `--sheet` (contact sheet, 1 thumb/60s, keyframe-only decode so long videos sample fast), `--scan <start> <end>` (frame-difference motion profile over a window, proposing the last still frame before sustained motion starts), bare `<src> <ts> <out>` (one high-quality frame, max 1920px), and `--clean`. Intended flow: sheet → scan → extract → look at the frame.
- **`img-sheet <out.jpg> <image|dir>...`** — tiles images into one labelled contact sheet so a pile of screenshots costs one look instead of twenty. Cells are sized by **width only**, so rows pack tightly for uniform-aspect inputs; mixing portrait and landscape leaves padding.
- **`update-tools [--check] [--bump-runtimes]`** — updates global tools managed by mise, Homebrew, uv, and pipx, plus agent-browser's Chrome download; it skips project dependencies and git checkouts and collects failures.
- **`check-runtimes [RUNTIME ...]`** — reports configured mise runtimes against stable and LTS releases without changing versions or pins; optional names limit the check.

Outside that media set, **`resource-log`** is the minute-by-minute memory/CPU sampler behind `launchd/com.nielsmadan.resource-log.plist` (loaded by `install.sh`); `resource-log report` reads the history. It runs under launchd's `/usr/bin/python3` (3.9), so keep it 3.9-compatible. Usage and caveats are in `docs/machine-triage.md`, and the tests are `python3 bin/test_resource_log.py`.

`<src>` for `video-frames` and `transcribe` is a **local file path or any yt-dlp-supported URL**; remote sources download once into `TMPDIR` and are reused across calls, so a sheet/scan/extract sequence costs one download. `video-frames` keys its cache on video id (a URL hash for non-YouTube links, so `youtu.be/X` and `watch?v=X` share an entry); `transcribe` keys on source **plus model** (a different model is a different transcript) and caches the finished VTT, so a re-run is ~0.1s instead of a full pass. Both take `--clean`.

**`--timestamps`** on `yt-transcript` and `transcribe` prefixes each line `[M:SS]` (~60s buckets, `--bucket` to change) instead of emitting one flat paragraph. That's what makes the pair compose: locate a moment in the text, hand the timestamp to `video-frames` to see it. Both go through the shared **`bin/lib/vtt_to_text.py`** — YouTube captions and Whisper output are both VTT, so there's one parser, not two that drift. The scripts locate it via `os.path.realpath("$0")`, which resolves the `~/.local/bin` symlink back into the repo; `install.sh` links only the commands, and the lib rides along in the repo.

### Whisper engine and models

`transcribe` runs a **local** model — nothing is uploaded, and it works offline once weights are cached (this is the point for client recordings). Engine resolution: `mlx_whisper` on `PATH`, else `mise exec -- mlx_whisper` (mise-installed CLIs are absent from `PATH` in a shell that never activated mise — a cron job, an editor subprocess), else `whisper-cli` from whisper.cpp with `$WHISPER_CPP_MODEL`. The mlx path is pinned as `pipx:mlx-whisper` in `mise/config.toml`; **MLX is Apple-Silicon-only**, so that pin can't install on an Intel Mac — the whisper.cpp fallback exists for exactly that case, and the engine detection degrades to a clear install message rather than a stack trace.

Weights land in `~/.cache/huggingface/hub/` (**not** managed by mise — mise installs the CLI, the model is a separate first-run download). Measured: `whisper-large-v3-turbo` **1.5G**, `whisper-tiny` **71M**; `small.en` sits around 0.5G. The default is turbo via `$TRANSCRIBE_MODEL`, because tiny is visibly wrong on real audio (it produced "long prompts" where turbo got the sentence right). Drop to a smaller model with `--model` when speed or disk matters more than accuracy.

### Gotchas baked into these scripts, don't undo them

- **macOS ships bash 3.2**, where a bare `"${arr[@]}"` on an *empty* array trips `set -u` and aborts. Every optional-args array uses `${arr[@]+"${arr[@]}"}`. This is a live path, not theory: it's hit by `img-sheet --no-labels`, by `transcribe` without `--lang`, and by `video-frames` on any machine without node.
- Every ffmpeg output chain ends in `format=yuvj420p`; without it the mjpeg encoder refuses non-full-range YUV and writes **nothing while still exiting 0**. Both output paths therefore run ffmpeg with `|| true` and gate on `[ -s "$out" ]`, so "no frame written" is a real error rather than a silent success.
- `--scan`'s backward walk from the motion onset is bounds-checked: when motion starts at the very start of the window there is no still frame before it, and an unguarded `rows[onset-1]` wraps to the *end* of the list and confidently reports a bogus timestamp.
- YouTube only exposes formats above 360p to a client with a **JS runtime**, hence `--js-runtimes node` — passed only when both `node` and that (newer) yt-dlp flag exist, so an older yt-dlp doesn't hard-fail on an unknown option.
- `yt-dlp` is **not pinned in `mise/config.toml`** — it's a pip install inside the mise python, so a python version bump loses it. `ffmpeg`/`ffprobe` and ImageMagick come from brew, per the mise-vs-brew rule.

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

Tool ownership, upgrade commands, and the shell prompt bootstrap are in [docs/tooling.md](docs/tooling.md).

## Secrets management

Dev API keys (e.g. `JINA_API_KEY`) live in `secrets/secrets.yaml` in this repo, encrypted with [SOPS](https://github.com/getsops/sops) using [age](https://github.com/FiloSottile/age) recipients. Each Mac has its own age identity at `~/.config/sops/age/keys.txt` (mode 600); the corresponding **public** keys are listed in `.sops.yaml` at the repo root. The encrypted file is safe to commit — that's the whole point.

Why this setup: keys stay out of the interactive shell and out of plaintext files on disk — `sops exec-env` decrypts into the launched tool's process tree only, so the parent shell and unrelated processes never see them.

It is **not** a barrier against the agent itself. A tool started this way inherits every injected variable, and so does every command it runs (measured 2026-09-20: `JINA_API_KEY` and `GH_TOKEN` are both present in a Claude Code Bash subprocess). That is acceptable by design, because this store holds low-value dev tokens that are cheap to revoke — which is also the standard it sets for what may go in: anything that would not be safe in an agent's environment does not belong here.

One exception is imposed from outside: **Claude Code strips `CLAUDE_CODE_OAUTH_TOKEN`, `ANTHROPIC_API_KEY` and `ANTHROPIC_AUTH_TOKEN`** from the environment it hands to tool subprocesses (its own behaviour, nothing to do with this setup). So a nested `claude` spawned from inside a session inherits no credential; launch it through `sops-exec claude …` — with `AGENT_REQUIRE_SECRETS=1`, so a re-injection failure exits 78 loudly instead of starting a keyless agent — rather than trying to read the token.

Architecture:
- **`.sops.yaml`** (repo root) — SOPS creation rules. Lists allowed age recipients (public keys, one per Mac). Plaintext, committed.
- **`secrets/secrets.yaml`** (repo) — encrypted YAML. Variable names are visible (diff-friendly); values are AES-256-GCM ciphertext, decryptable only by listed recipients. Committed.
- **`secrets/secrets-mini.yaml`** (repo) — encrypted YAML scoped to the Mac mini only (its recipient list in `.sops.yaml` is deliberately limited to the mini's age key). Holds secrets that should not exist on any other machine. When adding a new Mac to `.sops.yaml`, **do not** add it as a recipient of `secrets-mini.yaml` — leave that file's recipient list alone.
- **`SOPS_AGE_KEY_FILE`** / **`SOPS_SECRETS`** — set in `~/ac/.airc.d/04-sops.zsh`, which `.zshrc` picks up when it sources `~/.airc`. macOS' default location for SOPS is `~/Library/Application Support/sops/age/keys.txt` (path with spaces); we use the cleaner XDG location.
- **CLI wrappers** invoke each tool through `sops-exec` (`~/ac/bin/sops-exec`, linked into `~/.local/bin`), which wraps `sops exec-env` so keys land only in that subprocess. `~/ac` owns the agent wrappers (`claude`, `codex`, `opencode`, `pi`). It is a script, not a shell function, so launchers that never read `.zshrc` can reach it.
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

## Environment variables

Before adding an env var anywhere, read `docs/env-vars.md`. It maps the six slots on this
machine by **reach** — `.zshrc` is interactive-only, mise `[env]` reaches any process via
the shim, `sops-exec` reaches exactly one on purpose — and says which to pick. Picking by
habit rather than by reach is how a var ends up invisible to the tool that needed it.

## Machine troubleshooting

"This Mac is slow" triage — memory-compressor thrash vs. CPU, orphaned iOS Simulators,
the known heavy residents — lives in `docs/machine-triage.md`. Read it before profiling
anything; the answer is usually memory, not a runaway process.

## Local-only files (not in this repo)

`.zshrc` sources `~/.airc`, `~/.devrc`, and `~/.zshrc.local` if present (`.devrc` is in the repo and symlinked in; the others are user-local). `.gitconfig` includes `~/.gitconfig-local`. Don't expect to find these here. (`~/.airc` is a symlink to `~/ac/.airc`, the agent-tooling shell config — see that repo.)
