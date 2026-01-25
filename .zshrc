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
  bun
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
  nvm
  pyenv
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


# ---------------------------------------------------------------------------
#  Tool & Language Version Managers (nvm, pyenv, rbenv, bun, mise)
# ---------------------------------------------------------------------------

# rbenv (Ruby Version Manager)
eval "$(rbenv init - zsh)"

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

alias j="z"

alias m="mvim"
alias n="neovide &"

note() {
  mvim -c "cd ~/Dropbox/notes" ~/Dropbox/notes/overview.md
}

todo() {
  mvim -c "cd ~/Dropbox/notes" ~/Dropbox/notes/todos/mathfiend.md
}

idea() {
  mvim -c "cd ~/Dropbox/notes" ~/Dropbox/notes/ideas/mathfiend.md
}

alias flt="flutter"

alias rc="cd ~/rc"
alias srcz="source ~/.zshrc"
alias zshrc="mvim ~/.zshrc"

# AI tools (Claude, etc.)
[ -f ~/.airc ] && source ~/.airc

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


# pnpm
export PNPM_HOME="/Users/nielsmadan/Library/pnpm"
case ":$PATH:" in
  *":$PNPM_HOME:"*) ;;
  *) export PATH="$PNPM_HOME:$PATH" ;;
esac
# pnpm end

# bun completions
[ -s "/Users/nielsmadan/.bun/_bun" ] && source "/Users/nielsmadan/.bun/_bun"
