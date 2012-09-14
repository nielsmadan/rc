alias ls='ls --color=auto'

HISTFILE=~/.histfile

HISTSIZE=1000
SAVEHIST=1000

# setopt appendhistory nomatch
# 
# unsetopt autocd beep extendedglob notify

bindkey -e

zstyle :compinstall filename '/home/nimadan/.zshrc'
if [[ -a ~/.localzshrc ]]
then
  source ~/.localzshrc
fi

autoload -U compinit promptinit
compinit
promptinit
