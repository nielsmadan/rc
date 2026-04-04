# ---------------------------------------------------------------------------
#  Environment Variables and Path
# ---------------------------------------------------------------------------
# If you come from bash you might have to change your $PATH.
# export PATH=$HOME/bin:/usr/local/bin:$PATH

# Path to your oh-my-zsh installation.
export ZSH="$HOME/.oh-my-zsh"

# Path for Android SDK
export ANDROID_HOME="$HOME/Library/Android/sdk"

# Add various tools to the PATH
export PATH="$PATH:$ANDROID_HOME/emulator"
export PATH="$PATH:$ANDROID_HOME/tools"
export PATH="$PATH:$ANDROID_HOME/tools/bin"
export PATH="$PATH:$ANDROID_HOME/platform-tools"
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
  macos
  macports
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

# Rust / Cargo
. "$HOME/.cargo/env"

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
else
  export EDITOR='mvim'
fi

unsetopt correct_all
setopt correct

setopt no_share_history
setopt append_history
setopt HIST_IGNORE_ALL_DUPS
setopt HIST_IGNORE_SPACE
setopt HIST_VERIFY
setopt EXTENDED_HISTORY

setopt AUTO_CD
setopt AUTO_PUSHD
setopt PUSHD_IGNORE_DUPS
setopt PUSHD_SILENT

# Custom function to search global history with fzf
fzf-global-history-widget() {
    local selected
    selected=$(fc -l 1 | fzf --tac --no-sort --exact | sed 's/^[[:space:]]*[0-9]*[[:space:]]*//')
    BUFFER=$selected
    zle end-of-line
}

zle -N fzf-global-history-widget
bindkey '^R' fzf-global-history-widget

alias j="z"

alias m="mvim"
alias n="neovide &"

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

# AI tools (Claude, etc.)
[ -f ~/.airc ] && source ~/.airc

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

export PATH="/opt/homebrew/opt/libpq/bin:$PATH"

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
[[ -f /Users/nielsmadan/.dart-cli-completion/zsh-config.zsh ]] && . /Users/nielsmadan/.dart-cli-completion/zsh-config.zsh || true
## [/Completion]

set_tab_title() {
  echo -ne "\033]0;${PWD##*/}\033\\"
}

precmd_functions+=(set_tab_title)


# opencode
export PATH=/Users/nielsmadan/.opencode/bin:$PATH
