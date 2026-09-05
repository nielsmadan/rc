# Environment variables: how they reach a process

Where a variable has to be set so that a *given* process actually sees it. This machine
has six mechanisms that all look like "setting an env var" and differ only in reach —
`.zshrc` reaches nothing non-interactive, mise `[env]` reaches almost everything, and
`sops-exec` reaches exactly one process on purpose.

- [The model](#the-model)
- [The slots, by reach](#the-slots-by-reach)
- [zsh startup files](#zsh-startup-files)
- [mise: two mechanisms, not one](#mise-two-mechanisms-not-one)
- [sops-exec: deliberately not the shell](#sops-exec-deliberately-not-the-shell)
- [launchd](#launchd)
- [Picking a slot](#picking-a-slot)
- [Gotchas](#gotchas)
- [Debugging](#debugging)

## The model

There is no ambient "environment". Each process carries its own block of `KEY=value`
strings and obtains it in exactly two ways:

1. **Inherited** — copied from the parent at `fork`/`exec`.
2. **Set by itself** — while running.

It is a *copy*, not a reference, so a child can never write back to its parent. That is
why `export` inside a script never reaches the calling shell, and why config is `source`d
rather than executed.

Every mechanism below is one of those two cases. What differs is only **who the parent is**
and **what that parent runs at startup**.

## The slots, by reach

| Slot | Reaches | Owned by |
|---|---|---|
| `~/.zshenv` | every zsh, including `zsh -c` | untracked, and **empty on purpose** — see Gotchas |
| mise `[env]` via **shims** | any process that execs a shim, from *any* parent | `mise/config.toml` (this repo) |
| mise `[env]` via **activate** | interactive shells, directory-aware | `.zshrc:135` |
| `~/.zprofile` | login shells | untracked, machine-local |
| `.zshrc` → `~/.airc` → `.airc.d/*.zsh` | interactive shells and their children | `.zshrc` (this repo), `~/ac` |
| launchd plist `EnvironmentVariables` | that one job | `launchd/*.plist` (this repo) |
| `sops exec-env` (`sops-exec`) | exactly one child process | `~/ac/bin/sops-exec` |
| `FOO=x cmd` | that one command | — |

## zsh startup files

zsh reads a *different subset* of its rc files depending on how it was started. This is
the source of most "but it works in my terminal" reports:

| File | Read by |
|---|---|
| `/etc/zshenv`, `~/.zshenv` | **every** zsh, including `zsh -c 'cmd'` |
| `~/.zprofile` | login shells only |
| `~/.zshrc` | **interactive** shells only |
| `~/.zlogin` | login shells only |

**On this machine:** `~/.zshenv` exists but is empty. `~/.zlogin` does not exist.
`~/.zprofile` holds `brew shellenv` plus PATH lines appended by third-party installers,
and is **not tracked** — `install.sh:183` links `.zshrc` and nothing else. So the entire
tracked env chain hangs off an interactive-only file.

The chain, in order:

1. `.zshrc:15` — first PATH prepend (`~/development/flutter/bin`, `~/.local/bin`).
2. `.zshrc:135` — `eval "$(mise activate zsh)"`. Applies mise's env **immediately**, not at
   the first prompt; `.zshrc:138` depends on that, reading `$ANDROID_HOME` to decide whether
   to add the Android SDK dirs.
3. `.zshrc:247` — sources `~/.airc`, which loops over `~/ac/.airc.d/*.zsh`: PATH additions,
   `SOPS_AGE_KEY_FILE` / `SOPS_SECRETS`, the Claude Code vars, and the sandboxed agent
   wrappers.
4. `.zshrc:274`, `:277` — `~/.devrc`, then `~/.zshrc.local`.

Because `brew shellenv` lives in the untracked `.zprofile`, `/opt/homebrew/bin` is absent
from a non-login shell. `~/ac/.airc.d/00-path.zsh` compensates by appending Homebrew, the
mise shim dir, `~/.local/bin` and `~/.opencode/bin`, so that sourcing `~/.airc` alone is
self-sufficient for a consumer that never ran a login shell.

## mise: two mechanisms, not one

mise looks like one thing and is two. Conflating them is what makes "does mise work
non-interactively?" ambiguous.

**`mise activate`** (`.zshrc:135`) installs a `precmd` hook that recomputes the environment
for the current directory and exports it into the live shell. Directory-aware, and
**interactive-only**, because it lives in `.zshrc`.

**Shims** don't involve a shell at all. `~/.local/share/mise/shims/<tool>` is an executable
that, when run, loads mise's config, applies `[env]` and the tool paths, then execs the real
binary. The shim is the process setting the variables — case 2 of the model, not inheritance.

That is the whole reason tool-support config belongs in mise `[env]`: it reaches launchd
jobs, cron, editor subprocesses and agent sandboxes, none of which read `.zshrc`.

**Verified 2026-09-04 against mise 2026.5.2**: with inheritance cut entirely,

```sh
env -i HOME=$HOME PATH=/usr/bin:/bin ~/.local/share/mise/shims/node \
  -e 'console.log(process.env.AGENT_DEVICE_IOS_TEAM_ID, process.env.ANDROID_HOME)'
```

prints both values. No shell ran, so no rc file could have supplied them.

**Config layering** (a separate axis — *which files mise merges*, not how the result is
delivered). The global paths, in the order baked into the 2026.5.2 binary:
`~/.config/mise/config.toml`, `~/.config/mise/conf.d/*.toml`, then the `.local.toml`
variants. Only the first is in use here (`mise doctor` → `config_files`). `conf.d/` is the
supported way to let another repo contribute global env without editing this one's config.

## sops-exec: deliberately not the shell

`~/ac/bin/sops-exec` exists to do the opposite of everything above. `sops exec-env <file>
"<cmd>"` decrypts the store, builds an env block containing the keys, and execs **one**
child with it. The parent shell's block is never touched.

That is the entire security argument: an agent can run `env` freely and find nothing,
because the keys were never in the shell it inherited from. They were assembled for the
`claude` process alone and die with it. `.zshrc:265-269` wraps `nvim`/`mvim`/`neovide` the
same way.

It is a **script, not a shell function**, so launchers that load no shell config can reach
it off PATH.

## launchd

GUI apps and LaunchAgents are started by launchd, which is not a shell and never reads
`.zshrc`. They inherit launchd's own sparse environment. A variable such a job needs must
come from the plist's `EnvironmentVariables` key, or the job has to fetch it itself.

This is also why `launchd/com.nielsmadan.hidutil-capslock-to-f18.plist` sources a **fixed
path** (`~/.config/hidutil/local.sh`) rather than a repo path: the plist has no shell config
to tell it where the repo lives.

## Picking a slot

| The variable is… | Put it in |
|---|---|
| config for a mise-managed tool | `mise/config.toml` `[env]` |
| the same but owned by another repo | that repo's file, linked into `~/.config/mise/conf.d/` |
| a secret | `secrets/secrets.yaml`, reached via `sops-exec` |
| shell UX (`EDITOR`, prompt, aliases) | `.zshrc` |
| agent-harness behavior | `~/ac/.airc.d/*.zsh` |
| needed by a LaunchAgent | that plist's `EnvironmentVariables` |
| machine-specific | `~/.zshrc.local`, or the repo's `*.local.*` stub for that tool |

## Gotchas

- **`~/.zshenv` is empty on purpose.** It is the only file every zsh reads, which also means
  everything in it runs for every script, every `zsh -c`, every subshell — so it is the most
  expensive slot on the machine, and the one most likely to break a tool that assumes a clean
  environment. mise `[env]` gives the same reach through the shim without that cost. Keep it
  empty; if something genuinely needs universal reach and is not a mise tool, that is the
  decision to make deliberately.
- **`~/.zprofile` and `~/.zshenv` are untracked, but `.zshrc` is not.** Third-party
  installers append PATH lines to whichever of the three they find, and `~/.zshrc` is a
  symlink into this repo — so an installer's edit lands as a repo change. After running
  one, check `git diff .zshrc`.
- **PATH is de-duplicated** by `typeset -U path PATH` at `.zshrc:13`, set before the first
  assignment so it covers every later one. A dir prepended twice collapses to its first
  occurrence instead of accumulating, which also stops nested shells (an agent's `Bash`
  tool, `srcz`) from growing PATH each level. Without it, measured 2026-09-04: 53 entries
  with `~/.local/bin` and `~/.opencode/bin` doubled; with it, 51 and no duplicates.
- **PATH order is not stable across the first prompt.** mise's precmd hook re-prepends its
  own install dirs *every* prompt, so anything prepended during `.zshrc` gets pushed down
  once the shell settles. Measured 2026-09-04 against mise 2026.5.2: `~/ac/bin` sits at
  position 4 of 53 when `.zshrc` finishes and at **45 of 53** after the hook runs, behind
  mise's `gh` at 16. So a script in `~/ac/bin` whose name collides with a mise tool is
  silently shadowed in the steady state, and a check made before the first prompt will not
  show it. `gh` handles this with a shell function (`~/ac/.airc.d/gh.zsh`), which outranks
  PATH entirely; any future collision needs the same treatment. Reproduce with:

  ```sh
  env -i HOME=$HOME TERM=xterm-256color zsh -ic \
    'for f in $precmd_functions; do $f >/dev/null 2>&1; done; print -l $path' | grep -n ac/bin
  ```
- **`mise activate` and the shim dir are both on PATH** (`mise doctor` → `activated: yes`,
  `shims_on_path: yes`). Harmless, but it means a tool can be resolved by either mechanism,
  and only the shim path applies `[env]` to a non-activated caller.
- **A bare assignment is not an env var.** `FOO=1` without `export` sets a shell variable
  that no child process sees. Easy to miss in a file where the surrounding lines are exported.

## Debugging

When a process can't see a variable, ask in order:

1. **Who is the parent?** A terminal, launchd, or another agent — each has a different chain.
2. **Does that parent's startup path include the file that sets it?** `zsh -c` reads only
   `.zshenv`.
3. **If it's a mise tool** — is it reached through the shim, or by an absolute install path
   that bypasses it?

`env -i` plus an absolute shim path answers all three at once, because it removes inheritance
as a variable:

```sh
env -i HOME=$HOME PATH=/usr/bin:/bin ~/.local/share/mise/shims/<tool> ...
```

Other useful probes: `mise doctor` (which config files are merged, and whether activate and
shims are both live), `mise env` (the computed env for the current directory), `type -a <cmd>`
(function vs alias vs each PATH hit, in resolution order), and `print -l $path | sort | uniq -d`
(PATH duplicates).

## Related

- `docs/machine-triage.md` — "this Mac is slow" triage.
- `AGENTS.md` § Secrets management — the SOPS store and how keys are injected.
- `AGENTS.md` § Zsh: no framework — why `.zshrc` has no plugin manager.
