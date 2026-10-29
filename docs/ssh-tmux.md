# SSH profiles and tmux

`iterm2/dynamic-profile.json` carries the `ssh: mini` SSH profile; the Default and `rc` profiles have `Custom Command = No` and just launch the local shell — **nothing local ever starts tmux**, the only local footprint is an inert `~/.tmux.conf` symlink.

## Requirements and status

Reconstructed from what each earlier setup was abandoned over (see [Approaches tried](#approaches-tried)). Rows 9, 10 and 12 live in `~/.ssh/config`, which is machine-local and not in this repo.

| # | Want | Status | How |
|---|---|---|---|
| 1 | Session survives disconnect, sleep and network changes | ✅ | `tmux new -A -s main` on mini |
| 2 | Several shells on mini at once (often ~6) | ✅ | tmux windows and panes inside one ssh connection |
| 3 | New splits and windows open in the remote pane's directory | ✅ | `-c "#{pane_current_path}"` rebindings |
| 4 | Same keys as a local session | ⚠️ | `⌘D`/`⌘⇧D`/`⌘T`/`⌘W`/`⌘1`–`9`/`⌥hjkl` send the tmux prefix; `⌘⌃N` (clone repo) has no remote equivalent |
| 5 | iTerm2-native panes: per-pane selection, `⌘F` over the full history | ❌ | Given up with `-CC`. Selection is native but spans tmux pane borders; iTerm2's scrollback and `⌘F` don't see tmux history |
| 6 | Copies reach the local clipboard | ✅ | OSC 52 (`set-clipboard on`) |
| 7 | Truecolor | ✅ | `tmux-256color` + `Tc` |
| 8 | No stray output can wreck the session | ✅ | Plain tmux has no protocol stream to corrupt; `-q` keeps ssh diagnostics off the screen |
| 9 | Forwarded agent keeps working after reattach (commit signing on mini goes through it) | ✅ | `ForwardAgent yes`, `ControlMaster no` + `ControlPath none` for `mini`, `refresh_ssh_auth_sock` |
| 10 | Juggler hooks on mini reach this Mac | ✅ | `RemoteForward 7483 127.0.0.1:7483` |
| 11 | No secrets leave this Mac | ✅ | No `it2ssh` |
| 12 | Works at home and away | ✅ | `mini` resolves to its Tailscale IP, overridden by a `Match … exec "nc -z …"` to `macmini.local` when port 22 answers on the LAN |

## Current setup

The SSH profiles run `ssh -q -t <host> /opt/homebrew/bin/tmux new -A -s main` — **plain tmux, not control mode**. The session persists across disconnect / sleep / network changes, and splits follow the *remote* directory because tmux is doing the splitting.

**`-CC` is off-limits here, and the reason is structural.** In control mode the tmux protocol and the ssh client's own stderr share one stream, and iTerm2 parses every line it gets back as a control command. One line that doesn't start with `%` and iTerm2 drops out of tmux mode, dumps the rest of the protocol on screen as raw `%extended-output …` text, and opens its "Unrecognized command from tmux. Did your ssh session die?" dialog. Observed trigger: `setsockopt TCP_NODELAY: Invalid argument`, an OpenSSH client diagnostic from `set_nodelay()` on a forwarded channel — the Juggler `RemoteForward 7483 localhost:7483` in `~/.ssh/config` tried `::1` first, Juggler listens on IPv4 only, and when the refusal landed before `setsockopt` macOS returned `EINVAL`. That forward now targets `127.0.0.1` and no longer emits it, but the specific line doesn't matter; *any* stray stderr byte does this. `-q` on the ssh command suppresses client diagnostics and is kept for that reason, but it narrows the window rather than closing it — don't take it as a licence to go back to `-CC`.

Because tmux owns the panes, the `ssh: mini` profile remaps the window/split keys to send tmux's prefix (`C-b`, hex `0x02`) plus a key, via `Action 11` (Send Hex Code): `⌘D` → `%`, `⌘⇧D` → `"`, `⌘T` → `c`, `⌘W` → `x`, `⌥h/j/k/l` → `h/j/k/l`, `⌘1`–`⌘9` → window `1`–`9`. A child dynamic profile's `Keyboard Map` **replaces** the parent's rather than merging, so the profile re-declares `⌘S` (`save_window_arrangement()`) itself and deliberately omits `⌘⌃N` (`clone_repo_to_tab()` resolves the *local* session's git repo, which is meaningless in a remote pane). The profile also drops its `Mouse Reporting` override so it inherits `rc`'s wheel-yes / clicks-no setting: the wheel scrolls tmux history, while clicks and drags stay native so selection still reaches the real macOS clipboard.

Gotchas:
- **Absolute `/opt/homebrew/bin/tmux` is mandatory, not cosmetic.** Bare `tmux` is not on PATH for a non-interactive `ssh host cmd` (Homebrew's PATH is only wired up in login/interactive shells via `path_helper`), so `ssh -t <host> tmux …` dies "command not found" and the iTerm2 session "ends" instantly. tmux must also be installed on the remote (`brew install tmux`); mini has it.
- **Open the profile once, then use `⌘T` for more windows** — that is now a tmux window inside the same client. A second `⌘O` of the profile attaches a second client to `-s main`, and the two mirror each other at the smaller client's size.
- **tmux runs on the remote, so `tmux/tmux.conf` only takes effect there after a commit + pull on that machine.** Editing it here changes nothing about an existing ssh session until mini pulls and the session is reloaded (`C-b :source-file ~/.tmux.conf`, or kill the session).
- **mini's home is `/Users/nielsm` (user `nielsm`); this Mac is `/Users/nielsmadan`.** That mismatch produced the recurring `ssh mini … [Errno 2] No such file or directory: '/Users/nielsmadan'` error under iTerm2's native SSH "reuse directory" (it fed mini's conductor the profile's *local* fallback path) — one of the reasons the profiles don't use native SSH integration.

**No iTerm2 SSH integration is in play, on either machine.** `.zshrc` used to alias `ssh` to `it2ssh` under iTerm2 and source `~/.iterm2_shell_integration.zsh`; both are gone. The alias existed to ship terminfo to the remote, which iTerm2 never needed (it reports a standard `xterm-256color`, unlike kitty's `xterm-kitty` — the `kitten ssh` branch stays for exactly that reason). The shell-integration source existed to make iTerm2's "reuse previous session's directory" work over SSH, which tmux now does instead. Worth knowing before reinstating either: `it2ssh` base64-uploads the **entire environment** to the remote, and under the `sops exec-env` wrappers that includes live API tokens. The stale `~/.iterm2_shell_integration.zsh` file on mini is unreferenced, not sourced.

`tmux/tmux.conf` (symlinked to `~/.tmux.conf` by `install.sh`'s `link tmux tmux/tmux.conf`) is small but no longer minimal, because plain tmux means tmux owns the panes. Load-bearing: `default-terminal tmux-256color` + `terminal-overrides …:Tc` stop tmux stripping truecolor (matters for nvim/harlequin colors); `mouse on` makes the wheel scroll history; `set-clipboard on` + `terminal-features …:clipboard` send copies through OSC 52 so they reach the local clipboard; `base-index 1` + `renumber-windows on` keep window numbers lined up with `⌘1`–`⌘9`; the `%`/`"`/`c` rebindings add `-c "#{pane_current_path}"` so splits and new windows inherit the pane's directory; `h/j/k/l` become `select-pane` (this costs the default `l` = `last-window`). Also kept: `history-limit 50000` and the `update-environment` env-passthrough line.

Forwarded ssh-agent sockets go stale inside long-lived tmux; `.zshrc`'s `refresh_ssh_auth_sock` precmd hook repairs that (see the Zsh section).

## Approaches tried

| Since | Setup | Dropped because |
|---|---|---|
| 2026-05-18 (`f90d52c`) | `ssh` aliased to `it2ssh` under iTerm2 | Solves a terminfo problem iTerm2 doesn't have, and uploads the whole environment, sops tokens included (req. 11) |
| 2026-06-09 (`606c949`, `2b40c31`) | iTerm2 native SSH profile (`Custom Command: SSH`) + shell integration, so splits reuse the remote directory | Fed mini the local home path (`Errno 2 … '/Users/nielsmadan'`); one connection per pane, nothing survives a disconnect (req. 1) |
| 2026-06-30 (`d7118c6`, `bb22a95`) | `ssh -t host tmux -CC new -A -s main` (control mode), plus a `tmux/inherit-dir.sh` hook because iTerm2 issues `split-window` without `-c` | Any stray stderr line drops iTerm2 out of control mode (req. 8, see above). The hook script was deleted with it |
| until 2026-09-20 | Connection sharing to mini (the `Host *` `ControlMaster auto` default) | A reused master keeps serving a forwarded agent socket whose agent has died, breaking commit signing (req. 9) |
| 2026-09-22 (`d0ae435`) | Plain tmux over `ssh -q -t`, iTerm2 keys remapped to the tmux prefix | Current |
