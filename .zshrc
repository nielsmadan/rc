# ---------------------------------------------------------------------------
#  Environment Variables and Path
# ---------------------------------------------------------------------------
# If you come from bash you might have to change your $PATH.
# export PATH=$HOME/bin:/usr/local/bin:$PATH

# Path for Android SDK
export ANDROID_HOME="$HOME/Library/Android/sdk"

# Keep brew auto-update, but silence the env-hint footer it prints
export HOMEBREW_NO_ENV_HINTS=1

# Android SDK tools (only when the SDK is actually present)
if [[ -d "$ANDROID_HOME" ]]; then
  export PATH="$PATH:$ANDROID_HOME/emulator"
  export PATH="$PATH:$ANDROID_HOME/tools"
  export PATH="$PATH:$ANDROID_HOME/tools/bin"
  export PATH="$PATH:$ANDROID_HOME/platform-tools"
fi
export PATH="$HOME/development/flutter/bin:$HOME/.local/bin:$PATH"

# ---------------------------------------------------------------------------
#  Completions, plugins & shell sugar (framework-free — no oh-my-zsh)
# ---------------------------------------------------------------------------

# Homebrew's completion functions, on fpath before compinit. Paths are
# hardcoded (Apple-Silicon / Intel) to avoid forking `brew --prefix` at startup.
for _d in /opt/homebrew/share/zsh/site-functions /usr/local/share/zsh/site-functions; do
  [[ -d $_d ]] && fpath=("$_d" $fpath)
done
unset _d

# Completion functions for CLIs that ship their own zsh completion generator but
# install via mise — so they have no Homebrew site-functions/_<tool> file the way
# git/docker/npm do. Each is generated once into a cache dir on fpath. The
# generators run ONLY when a file is missing, so a normal startup forks nothing.
# Cobra/clap scripts bake in the tool's subcommands/flags, so after a major
# upgrade `rm ~/.zsh/completions/_<tool>` (or the whole dir) to refresh them.
_zcompcache=~/.zsh/completions
typeset -A _zcompgen=(
  just     'just --completions zsh'
  gh       'gh completion -s zsh'
  glab     'glab completion -s zsh'
  kubectl  'kubectl completion zsh'
  pnpm     'pnpm completion zsh'
  bun      'bun completions'
  lefthook 'lefthook completion zsh'
  railway  'railway completion zsh'
  sops     'sops completion zsh'
  rustup   'rustup completions zsh'
  cargo    'rustup completions zsh cargo'
)
for _t in "${(@k)_zcompgen}"; do
  [[ -e $_zcompcache/_$_t ]] && continue
  command -v "$_t" >/dev/null 2>&1 || continue
  mkdir -p $_zcompcache
  # Strip leading blank lines so the `#compdef` tag lands on line 1 (sops emits a
  # blank first line otherwise, which makes compinit skip it). Drop empties so a
  # failed generation retries next startup instead of caching a broken file.
  eval "${_zcompgen[$_t]}" 2>/dev/null | sed '/./,$!d' >| "$_zcompcache/_$_t"
  [[ -s $_zcompcache/_$_t ]] || rm -f "$_zcompcache/_$_t"
done
unset _t _zcompgen
[[ -d $_zcompcache ]] && fpath=("$_zcompcache" $fpath)
unset _zcompcache

# Completion styling (set before compinit)
zstyle ':completion:*' matcher-list 'm:{a-zA-Z}={A-Za-z}'
zstyle ':completion:*' menu select
zstyle ':completion:*' use-cache on
zstyle ':completion:*' cache-path ~/.zsh/cache

# compinit, but skip the slow security audit when the dump is fresh (<24h).
# The glob qualifier (#qNmh-24) = "exists and modified within the last 24 hours".
autoload -Uz compinit
if [[ -n ~/.zcompdump(#qNmh-24) ]]; then
  compinit -C
else
  compinit
fi
# Byte-compile the dump so future startups load the compiled .zwc instead of
# re-parsing ~51k of text. Done in a disowned background job so it never blocks
# the prompt; zsh auto-prefers the .zwc on the next shell once it's newer.
if [[ -s ~/.zcompdump && (! -s ~/.zcompdump.zwc || ~/.zcompdump -nt ~/.zcompdump.zwc) ]]; then
  { zcompile ~/.zcompdump } &!
fi

# git: `g` is the one oh-my-zsh git alias worth keeping; the rest of the git
# shortcuts (ca, co, ci, po, d, ...) live in ~/.gitconfig.
alias g='git'

# up N directories: `..` is built into zsh's cd, these add deeper hops
# (replaces oh-my-zsh's lost `...`/`....`/`.....` aliases).
alias ..='cd ..'
alias ...='cd ../..'
alias ....='cd ../../..'
alias .....='cd ../../../..'

# eza (ls replacement)
alias ls='eza -g'
alias ll='eza -gl'
alias la='eza -gla'
alias l='ls -lah'

# zoxide (smarter cd); the `j` alias for `z` is defined further down.
eval "$(zoxide init zsh)"

# extract <archive> ... — unpack common archive formats. Compact replacement
# for oh-my-zsh's extract plugin (which we no longer load).
extract() {
  setopt localoptions noautopushd
  (( $# )) || { echo "usage: extract <archive> [...]" >&2; return 1; }
  local f
  for f in "$@"; do
    [[ -f $f ]] || { echo "extract: '$f' is not a file" >&2; continue; }
    case "${f:l}" in
      *.tar.gz|*.tgz)         tar xzvf "$f" ;;
      *.tar.bz2|*.tbz|*.tbz2) tar xjvf "$f" ;;
      *.tar.xz|*.txz)         tar xJvf "$f" ;;
      *.tar.zst|*.tzst)       tar --zstd -xvf "$f" ;;
      *.tar)                  tar xvf "$f" ;;
      *.gz)                   gunzip -k "$f" ;;
      *.bz2)                  bunzip2 -k "$f" ;;
      *.xz)                   unxz -k "$f" ;;
      *.zst)                  unzstd -k "$f" ;;
      *.zip|*.jar|*.war)      unzip "$f" ;;
      *.rar)                  unrar x "$f" ;;
      *.7z)                   7z x "$f" ;;
      *) echo "extract: don't know how to extract '$f'" >&2 ;;
    esac
  done
}

# ---------------------------------------------------------------------------
#  Tool & Language Version Managers (mise)
# ---------------------------------------------------------------------------

# mise
eval "$(mise activate zsh)"

# flutterfire CLI
export PATH="$PATH":"$HOME/.pub-cache/bin"

# ---------------------------------------------------------------------------
#  Custom Aliases and Settings
# ---------------------------------------------------------------------------
# Preferred editor for local and remote sessions
if [[ -n $SSH_CONNECTION ]]; then
  export EDITOR='vim'
elif command -v mvim >/dev/null 2>&1; then
  export EDITOR='mvim'
else
  export EDITOR='vim'
fi

unsetopt correct_all
setopt correct

setopt no_share_history
setopt inc_append_history
setopt append_history
setopt HIST_IGNORE_ALL_DUPS
setopt HIST_IGNORE_SPACE
setopt HIST_VERIFY
setopt EXTENDED_HISTORY

setopt AUTO_CD
setopt AUTO_PUSHD
setopt PUSHD_IGNORE_DUPS
setopt PUSHD_SILENT

# Custom function to search global history with fzf.
fzf-global-history-widget() {
    local selected
    [[ -r $HISTFILE ]] || return
    selected=$(
        sed 's/^: [0-9]*:[0-9]*;//' "$HISTFILE" \
            | awk '{ l[NR]=$0 } END { for (i=NR;i>=1;i--) if (!seen[l[i]]++) print l[i] }' \
            | fzf --no-sort --exact
    )
    BUFFER=$selected
    zle end-of-line
}

zle -N fzf-global-history-widget
bindkey '^R' fzf-global-history-widget

alias j="z"

alias n="neovide &"

# MacVim-only. `mvim` is the MacVim GUI launcher; also prefer MacVim's
# full-featured CLI vim for the terminal (Apple's /usr/bin/vim is stripped).
if [[ "$OSTYPE" == darwin* && -x /Applications/MacVim.app/Contents/bin/vim ]]; then
  alias vim="/Applications/MacVim.app/Contents/bin/vim"
  alias m="mvim"
fi

loadenv() {
  local envfile="${1:-.env}"
  if [[ -f "$envfile" ]]; then
    set -a && source "$envfile" && set +a
    echo "Loaded $envfile"
  else
    echo "File not found: $envfile"
    return 1
  fi
}

alias flt="flutter"

alias rc="cd ~/rc"
alias srcz="source ~/.zshrc"
alias zshrc="mvim ~/.zshrc"

# Inside kitty, route ssh through the kitten so xterm-kitty terminfo gets
# installed on the remote — otherwise prompt redraws produce garbled output.
# Same idea for iTerm2: it2ssh ships shell integration + terminfo to the remote.
# WezTerm uses TERM=xterm-256color by default, so no wrapper needed.
if [[ "$TERM" == "xterm-kitty" ]] && command -v kitten >/dev/null 2>&1; then
  alias ssh="kitten ssh"
elif [[ "$LC_TERMINAL" == "iTerm2" ]] && command -v it2ssh >/dev/null 2>&1; then
  alias ssh="it2ssh"
fi

# iTerm2 shell integration: lets the shell report cwd + host to iTerm2 so
# "reuse previous session's directory" works over SSH — split panes inherit the
# remote dir instead of trying to cd into a local-only path. Per-machine: only
# loads where the script has been fetched into $HOME. Harmless in other terminals.
[[ -e "${HOME}/.iterm2_shell_integration.zsh" ]] && source "${HOME}/.iterm2_shell_integration.zsh"

# AI tools (Claude, etc.) — legacy plain-env source. Migrate each key into
# secrets/secrets.yaml (via `sops edit`), then remove the corresponding
# `export` line from ~/.airc so it's not also in shell env.
[ -f ~/.airc ] && source ~/.airc

# SOPS reads the age identity from this path. Default macOS location uses a
# space-padded `Library/Application Support/sops/age/` path; we keep ours at
# the cross-platform XDG location instead.
export SOPS_AGE_KEY_FILE="$HOME/.config/sops/age/keys.txt"

# `sops edit` shells out to $EDITOR and waits for it to exit. Plain `mvim`
# (our $EDITOR) spawns its GUI in the background and returns instantly, which
# makes sops think the user saved an empty file. Force a terminal nvim for
# sops specifically.
export SOPS_EDITOR=nvim

# AI CLI wrappers — invoke each via `sops exec-env` so its API keys are
# injected only into the subprocess, never into this shell's env.
#
# `sops exec-env <file> <command>` takes the command as a single string that
# sops re-tokenizes via the shell, NOT a `--`-separated argv. We use
# `printf '%q '` to shell-quote each user-supplied arg so prompts with spaces
# (`claude -p "tell me about cats"`) survive the round-trip.
#
# If sops, the secrets file, or the age identity is missing on this machine,
# fall through to the bare command — useful on hosts that don't need the
# dev secrets (e.g. fresh installs where you just want mvim/nvim to work).
SOPS_SECRETS="$HOME/.config/sops/secrets.yaml"
_sops_exec() {
  local cmd=$1; shift
  if command -v sops >/dev/null 2>&1 && [ -f "$SOPS_SECRETS" ] && [ -f "$SOPS_AGE_KEY_FILE" ]; then
    sops exec-env "$SOPS_SECRETS" "$cmd $(printf '%q ' "$@")"
  else
    command "$cmd" "$@"
  fi
}
claude()   { _sops_exec claude   "$@"; }
codex()    { _sops_exec codex    "$@"; }
gemini()   { _sops_exec gemini   "$@"; }
opencode() { _sops_exec opencode "$@"; }
railway()  { _sops_exec railway  "$@"; }

# Editor wrappers — codecompanion.nvim reads CLAUDE_CODE_OAUTH_TOKEN from
# env, so nvim/mvim/neovide need the secrets injected too. The existing
# `m` / `n` aliases (mvim, neovide &) keep working: they expand to the
# function name, then the function runs.
nvim()    { _sops_exec nvim    "$@"; }
mvim()    { _sops_exec mvim    "$@"; }
neovide() { _sops_exec neovide "$@"; }

alias sec="sops edit $SOPS_SECRETS"

# Dev helper functions (mksim, etc.)
[ -f ~/.devrc ] && source ~/.devrc

# Local config (not checked in)
[ -f ~/.zshrc.local ] && source ~/.zshrc.local

# ---------------------------------------------------------------------------
#  Tool-specific Completions (e.g. gcloud)
#  NOTE: It is recommended to install gcloud via Homebrew to manage this automatically.
# ---------------------------------------------------------------------------
# The next line updates PATH for the Google Cloud SDK.
if [ -f "$HOME/google-cloud-sdk/path.zsh.inc" ]; then . "$HOME/google-cloud-sdk/path.zsh.inc"; fi

# The next line enables shell command completion for gcloud.
if [ -f "$HOME/google-cloud-sdk/completion.zsh.inc" ]; then . "$HOME/google-cloud-sdk/completion.zsh.inc"; fi

# Apple-Silicon Homebrew keg-only libpq (path only exists on such machines)
[[ -d /opt/homebrew/opt/libpq/bin ]] && export PATH="/opt/homebrew/opt/libpq/bin:$PATH"

# increase resources for reliable watchman
ulimit -n 65536
ulimit -u 2048

# docker context use mac-mini

alias setdockerlocal='docker context use default && echo "✅ Docker now using LOCAL (MacBook)"'
alias setdockermini='docker context use mac-mini && echo "✅ Docker now using MAC MINI"'
alias dockerwhere='docker context show'

bindkey '^[b' backward-word  # ESC+b
bindkey '^[f' forward-word   # ESC+f

# pure

fpath+=("$HOME/.zsh/pure")
autoload -U promptinit; promptinit
prompt pure

## [Completion]
## Completion scripts setup. Remove the following line to uninstall
[[ -f "$HOME/.dart-cli-completion/zsh-config.zsh" ]] && . "$HOME/.dart-cli-completion/zsh-config.zsh" || true
## [/Completion]

set_tab_title() {
  echo -ne "\033]0;${PWD##*/}\033\\"
}

precmd_functions+=(set_tab_title)


# opencode
export PATH="$HOME/.opencode/bin:$PATH"

# Added by Antigravity CLI installer
export PATH="$HOME/.local/bin:$PATH"

# ---------------------------------------------------------------------------
#  zsh-autosuggestions + zsh-syntax-highlighting
# ---------------------------------------------------------------------------
# Sourced directly (no plugin framework). These MUST come last — after every
# custom ZLE widget and bindkey above — so syntax-highlighting can wrap them
# all. autosuggestions is sourced before syntax-highlighting.
source "$HOME/.zsh/zsh-autosuggestions/zsh-autosuggestions.zsh"
source "$HOME/.zsh/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh"

autoload -U +X bashcompinit && bashcompinit
complete -o nospace -C /Users/nielsmadan/.local/share/mise/installs/aqua-hashicorp-vault/2.0.2/vault vault
