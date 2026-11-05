# The Mac Studio admin account's shell; bin/system-install links ~/.zshrc here.
# It stands alone: nothing from ~/ac, no secrets, no agent tooling. Pure and the
# two plugins are Homebrew's (the Brewfile's studio block).

[[ -z $HOMEBREW_PREFIX && -x /opt/homebrew/bin/brew ]] && eval "$(/opt/homebrew/bin/brew shellenv)"
_brew=${HOMEBREW_PREFIX:-/opt/homebrew}

# Where system-install puts the rustup proxies, so a manual `mise install --system`
# doesn't move them into this home.
export MISE_CARGO_HOME=/usr/local/share/mise/cargo

HISTFILE=~/.zsh_history
HISTSIZE=50000
SAVEHIST=50000
setopt extended_history hist_ignore_dups hist_ignore_space share_history
setopt auto_cd interactive_comments

fpath=("$_brew/share/zsh/site-functions" $fpath)
autoload -Uz compinit && compinit
zstyle ':completion:*' menu select

if (( $+commands[eza] )); then
  alias ls='eza --group-directories-first'
  alias ll='eza -l --group-directories-first'
  alias la='eza -la --group-directories-first'
else
  export CLICOLOR=1
  alias ll='ls -lh'
  alias la='ls -lha'
fi

# Pure shows user@host only over ssh; this shows it in every admin shell.
export PROMPT_PURE_SSH_CONNECTION=${PROMPT_PURE_SSH_CONNECTION:-local}
zstyle :prompt:pure:user color red
autoload -Uz promptinit && promptinit
(( ${prompt_themes[(Ie)pure]} )) && prompt pure

# Last, so syntax-highlighting wraps every widget; autosuggestions goes first.
for _p in zsh-autosuggestions zsh-syntax-highlighting; do
  [[ -f $_brew/share/$_p/$_p.zsh ]] && source "$_brew/share/$_p/$_p.zsh"
done
unset _p _brew
