# ---------------------------------------------------------------------------
#  Environment Variables and Path
# ---------------------------------------------------------------------------
# If you come from bash you might have to change your $PATH.
# export PATH=$HOME/bin:/usr/local/bin:$PATH

# Path to your oh-my-zsh installation.
export ZSH="$HOME/.oh-my-zsh"

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
#  Oh My Zsh Configuration
# ---------------------------------------------------------------------------

# Set name of the theme to load.
ZSH_THEME=""

# Oh My Zsh plugins.
plugins=(
  brew
  docker
  docker-compose
  extract
  eza
  git
  history
  node
  npm
  mise
  vi-mode
  vscode
  yarn
  zoxide
  zsh-autosuggestions
  zsh-syntax-highlighting
)

# macOS-only oh-my-zsh plugins (avoid "plugin not found" on other OSes)
[[ "$OSTYPE" == darwin* ]] && plugins+=(macos macports)

# Oh My Zsh settings
zstyle ':omz:update' mode auto
ENABLE_CORRECTION="true"

# Load Oh My Zsh. This MUST come after the settings above.
source "$ZSH/oh-my-zsh.sh"

# Completion styling
zstyle ':completion:*' matcher-list 'm:{a-zA-Z}={A-Za-z}'
zstyle ':completion:*' menu select
zstyle ':completion:*' use-cache on
zstyle ':completion:*' cache-path ~/.zsh/cache

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
