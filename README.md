# rc

My macOS dotfiles, plus a handful of small scripts I keep on `PATH`.

This is a personal setup, published so others can read it and borrow from it.
It is not a framework meant to be installed as-is. It assumes an Apple Silicon
Mac, Homebrew, [mise](https://mise.jdx.dev), zsh, and the apps I happen to use.
Take what is useful; read anything before you run it.

## What's here

| Path | What it configures |
| --- | --- |
| `.zshrc`, `zsh/`, `.devrc` | zsh with no framework: [pure](https://github.com/sindresorhus/pure) prompt, autosuggestions, syntax highlighting, cached completions |
| `.vimrc`, `.gvimrc`, `.vim/`, `ultisnips/` | Vim / MacVim |
| `nvim/` | Neovim (lazy.nvim) |
| `.gitconfig`, `git/ignore` | git aliases, Neovide/MacVim as diff and merge tool, global gitignore |
| `tmux/`, `kitty/`, `wezterm/`, `iterm2/` | terminals; iTerm2 also gets a dynamic profile and AutoLaunch scripts |
| `hammerspoon/` | window placement and hotkeys (Caps Lock is remapped to F18 as a hyper key) |
| `finicky/`, `librewolf/` | browser routing and browser prefs |
| `mise/`, `Brewfile` | global CLI tools (mise) and Homebrew formulae and casks |
| `colima/`, `launchd/` | Docker via Colima, plus the LaunchAgents that supervise it and log resource use |
| `secrets/`, `.sops.yaml` | dev API keys encrypted with [SOPS](https://github.com/getsops/sops) + [age](https://github.com/FiloSottile/age) |
| `bin/` | standalone scripts, linked into `~/.local/bin` |
| `githooks/` | hooks that warn when a pull leaves a symlink stale |
| `docs/` | notes on individual parts of the setup |

The keybindings are written up in [VIM_KEYBINDINGS.md](VIM_KEYBINDINGS.md) and
[NVIM_KEYBINDINGS.md](NVIM_KEYBINDINGS.md). The other notes are in `docs/`:
[editor config](docs/editor-config.md), [Hammerspoon](docs/hammerspoon.md),
[iTerm2](docs/iterm2.md), [SSH and tmux](docs/ssh-tmux.md),
[Finicky](docs/finicky.md), [Colima](docs/colima.md) and its
[hardening](docs/colima-hardening.md), [tool versions](docs/tooling.md),
[environment variables](docs/env-vars.md), and
[slow-Mac triage](docs/machine-triage.md).

## Installing

```sh
git clone https://github.com/nielsmadan/rc.git ~/rc
cd ~/rc
./install.sh --check   # dry run: lists every change, makes none
./install.sh
```

`install.sh` symlinks each config from the repo to where its app expects it, so
editing a file in the repo edits the live config. It also:

- installs Homebrew if it is missing, then everything in the `Brewfile`
- clones pure, zsh-autosuggestions, and zsh-syntax-highlighting into `~/.zsh`, and installs vim-plug
- remaps Caps Lock to F18 with `hidutil` and loads the LaunchAgents in `launchd/`
- writes a few iTerm2 preferences (quit iTerm2 first)
- generates an age identity for SOPS at `~/.config/sops/age/keys.txt`
- sets `core.hooksPath` to `githooks/`

Running it again is safe: every step checks whether its work is already done.

> [!WARNING]
> When a target already exists as a real file or directory, `install.sh`
> deletes it and puts the symlink in its place, without a backup. `--check`
> marks these as `(REPLACES EXISTING FILE)` or `(REPLACES EXISTING DIRECTORY)`.
> Back up your own `~/.zshrc`, `~/.config/nvim` and so on first.

### Skipping parts

The first run writes `install.local` (gitignored), which lists every target by a
short alias, all commented out. Uncomment an alias to leave that target alone on
this machine, for example `hammerspoon`, `secrets`, or `homebrew`. If a skipped
target is already a symlink into the repo, it is replaced by a local copy you can
edit freely.

### Machine-local overrides

These files are sourced or included when they exist, and are not in the repo:

- `~/.zshrc.local`, sourced by `.zshrc`
- `~/.gitconfig-local`, included at the end of `.gitconfig`. `.gitconfig` sets my own name and email, so set yours here to override them.
- `hammerspoon/local.lua` and `finicky/finicky.local.ts` (gitignored, stubbed on first run; see the `.example` files next to them)

`.zshrc` also sources `~/.airc`, which comes from a separate private repo. If the
file isn't there, the line does nothing.

### Secrets

`secrets/secrets.yaml` holds my encrypted API keys. Only the age keys listed in
`.sops.yaml` can decrypt it, so on your machine it is opaque. Skip it with the
`secrets` alias, or replace it with your own SOPS file and recipients.

### Shared-Mac profile

`bin/system-install`, `studio-deploy`, and the `studio` branches in `install.sh`
and the `Brewfile` set up one specific Mac, where Homebrew belongs to an admin
account and the repo is deployed read-only to `/opt/rc`. They only take effect
when `/etc/rc-profile` exists, so you can ignore them.

## Scripts

`install.sh` links these into `~/.local/bin`. Each prints its usage with `--help`.

- `yt-transcript <url>`: metadata and cleaned captions for anything `yt-dlp` supports
- `transcribe <file-or-url>`: local Whisper transcription for audio or video without captions
- `video-frames`: contact sheets, motion scans, and single frames from a video
- `img-sheet <out.jpg> <images...>`: tile a pile of screenshots into one labelled image
- `update-tools`: update globally installed tools (see below)
- `check-runtimes`: compare configured language runtimes with the latest stable and LTS releases (see below)
- `resource-log`: per-minute memory and CPU sampler, run by a LaunchAgent
- `colima-watchdog`: keeps the Colima VM up, run by a LaunchAgent

`tailssh <host>` is a zsh function, not a script. It runs `ssh` to one of my own
machines through its Tailscale IP, which is hard-coded in `.zshrc`.

### update-tools

`bin/update-tools` updates global mise CLI tools, Homebrew packages and GUI apps,
uv tools, standalone pipx tools, and agent-browser's Chrome download. It also
updates mise and uv themselves. `install.sh` links it as `update-tools` on PATH.

```sh
update-tools --check          # preview commands without running updates
update-tools                  # run updates
update-tools --bump-runtimes   # also advance language runtime pins
```

The script runs from your home directory so a project's mise config or Python
environment does not select the tools being updated. Mise CLI pins are advanced
with `--bump`, preserving exact versions for npm tools. Language runtimes keep
their configured versions/ranges by default; `node = "24"`, for example, stays
on Node 24. Vault always keeps its explicit pin because its latest-tag resolver
has selected releases without macOS builds.

`--check` prints the planned commands; it does not query available releases or
run installers. It reads mise's current tool list, which requires Python 3.
Missing package managers are skipped. Failed steps are reported at the end with
exit status 1, while independent updates continue. A failed Homebrew metadata
refresh skips its package upgrades. Package-manager prompts remain interactive.

macOS, App Store apps, project dependencies, unmanaged pip/npm installations,
and git checkouts are outside the script's scope. Mise-managed Python tools are
updated through mise; `pipx upgrade-all` covers separate pipx installations.
After updating, open a new terminal and restart long-running agent sessions to
pick up new executable paths.

Run the script's checks with `python3 bin/test_update_tools.py`.

### check-runtimes

`check-runtimes` reports new stable releases for globally configured mise language
runtimes, including releases beyond existing pins. It only queries metadata;
it never installs runtimes or changes configuration. Requires Python 3.9+, mise,
and curl. `install.sh` links it onto PATH.

```sh
check-runtimes                # check all global language runtimes
check-runtimes node java      # check selected runtimes
```

The table shows the configured request, installed version, latest stable release,
and latest LTS release where tracked. `NEW` marks versions newer than the installed
one; `[LTS]` is highlighted in terminals. Set `NO_COLOR` to disable colors. An LTS
version older than your installed version is shown without `NEW`.

The status describes the installed runtime:

| With LTS | Color | Without LTS | Color |
| --- | --- | --- | --- |
| latest lts | green | up to date | green |
| older lts | yellow | patch behind | light green |
| off lts | yellow | minor behind | yellow |
| | | major behind | red |

`latest lts` means the newest LTS release line, even when a patch behind;
`older lts` means an earlier LTS line. Node and Java use major release lines;
Deno and .NET use major.minor lines. Deno's installed `--version` channel must
also be `lts`; stable-channel builds are `off lts` even on the same version line.
Missing installations and failed lookups show `not installed` or `unknown`.

Java checks keep the configured distribution (for example, Zulu) while looking
across major versions. LTS sources are
[Node's release index](https://nodejs.org/dist/index.json),
[Adoptium's Java release metadata](https://api.adoptium.net/v3/info/available_releases),
[Deno's LTS channel](https://dl.deno.land/release-lts-latest.txt), and
[Microsoft's .NET release index](https://builds.dotnet.microsoft.com/dotnet/release-metadata/releases-index.json).
Deno LTS is a separate release channel. `—` means LTS is not tracked for that
runtime; `unknown` means a lookup failed.

The command runs its queries from your home directory, independently of the
current project's config. Mise's release metadata cache may refresh. Exit status
is 0 for a complete check, including when updates exist, 1 for lookup failures,
and 2 for invalid arguments. Successful lookups are still shown if others fail.

Run the checks with `python3 bin/test_check_runtimes.py`.
