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
  macports
  macos
  node
  npm
  nvm
  vscode
  docker
  eza
  extract
  git
  history
  vi-mode
  yarn
  zsh-autosuggestions
  zsh-syntax-highlighting
)

# Oh My Zsh settings
zstyle ':omz:update' mode auto
ENABLE_CORRECTION="true"

# Load Oh My Zsh. This MUST come after the settings above.
source "$ZSH/oh-my-zsh.sh"


# ---------------------------------------------------------------------------
#  Tool & Language Version Managers (nvm, pyenv, rbenv, bun, mise)
# ---------------------------------------------------------------------------

# rbenv (Ruby Version Manager)
eval "$(rbenv init - zsh)"

# pyenv (Python Version Manager)
export PYENV_ROOT="$HOME/.pyenv"
command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"

# bun
export BUN_INSTALL="$HOME/.bun"
export PATH="$BUN_INSTALL/bin:$PATH"
[ -s "$HOME/.bun/_bun" ] && source "$HOME/.bun/_bun"

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

if [ -f ~/.fzf.zsh ]; then
    source ~/.fzf.zsh
    
    # Custom function to search global history with fzf
    fzf-global-history-widget() {
        local selected
        selected=$(fc -l 1 | fzf --tac --no-sort --exact | sed 's/^[[:space:]]*[0-9]*[[:space:]]*//')
        BUFFER=$selected
        zle end-of-line
    }
    
    zle -N fzf-global-history-widget
    bindkey '^R' fzf-global-history-widget
fi

alias m="mvim"
alias n="neovide &"

alias todo="mvim ~/Dropbox/notes/todos/mathfiend.md"
alias idea="mvim ~/Dropbox/notes/ideas/mathfiend.md"
alias note="mvim ~/Dropbox/notes/overview.md"

alias flt="flutter"

alias rc="cd ~/rc"
alias srcz="source .zshrc"
alias zshrc="mvim ~/.zshrc"

# ---------------------------------------------------------------------------
#  Tool-specific Completions (e.g. gcloud)
#  NOTE: It is recommended to install gcloud via Homebrew to manage this automatically.
# ---------------------------------------------------------------------------
# The next line updates PATH for the Google Cloud SDK.
if [ -f "$HOME/google-cloud-sdk/path.zsh.inc" ]; then . "$HOME/google-cloud-sdk/path.zsh.inc"; fi

# The next line enables shell command completion for gcloud.
if [ -f "$HOME/google-cloud-sdk/completion.zsh.inc" ]; then . "$HOME/google-cloud-sdk/completion.zsh.inc"; fi

export PATH="/opt/homebrew/opt/libpq/bin:$PATH"

alias claude="~/.claude/local/claude"
alias clco="claude --continue"

# for more reliable watchman
ulimit -n 65536
ulimit -u 2048

# docker context use mac-mini

alias setdockerlocal='docker context use default && echo "✅ Docker now using LOCAL (MacBook)"'
alias setdockermini='docker context use mac-mini && echo "✅ Docker now using MAC MINI"'
alias dockerwhere='docker context show'

fpath+=("$HOME/.zsh/pure")
autoload -U promptinit; promptinit
prompt pure

eval "$(zoxide init zsh)"
