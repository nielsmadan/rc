# ~/.bashrc: executed by bash(1) for non-login shells.
# see /usr/share/doc/bash/examples/startup-files (in the package bash-doc)
# for examples

# If not running interactively, don't do anything
[ -z "$PS1" ] && return

# don't put duplicate lines in the history. See bash(1) for more options
# ... or force ignoredups and ignorespace
HISTCONTROL=ignoredups:ignorespace

# don't add some commands to history (anything that's less than 3 letters)
export HISTIGNORE="?:??:exit:clear:reset"

# append to the history file, don't overwrite it
shopt -s histappend

# case insensitive globbing
shopt -s nocaseglob

# autocorrect for tab completion in cd
shopt -s cdspell

# for setting history length see HISTSIZE and HISTFILESIZE in bash(1)
HISTSIZE=32768
HISTFILESIZE=32768

# check the window size after each command and, if necessary,
# update the values of LINES and COLUMNS.
shopt -s checkwinsize

# make less more friendly for non-text input files, see lesspipe(1)
[ -x /usr/bin/lesspipe ] && eval "$(SHELL=/bin/sh lesspipe)"

# set variable identifying the chroot you work in (used in the prompt below)
if [ -z "$debian_chroot" ] && [ -r /etc/debian_chroot ]; then
    debian_chroot=$(cat /etc/debian_chroot)
fi

# set a fancy prompt (non-color, unless we know we "want" color)
case "$TERM" in
    xterm-color) color_prompt=yes;;
esac

# uncomment for a colored prompt, if the terminal has the capability; turned
# off by default to not distract the user: the focus in a terminal window
# should be on the output of commands, not on the prompt
#force_color_prompt=yes

if [ -n "$force_color_prompt" ]; then
    if [ -x /usr/bin/tput ] && tput setaf 1 >&/dev/null; then
	# We have color support; assume it's compliant with Ecma-48
	# (ISO/IEC-6429). (Lack of such support is extremely rare, and such
	# a case would tend to support setf rather than setaf.)
	color_prompt=yes
    else
	color_prompt=
    fi
fi

if [ "$color_prompt" = yes ]; then
    PS1='${debian_chroot:+($debian_chroot)}\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ '
else
    PS1='${debian_chroot:+($debian_chroot)}\u@\h:\w\$ '
fi
unset color_prompt force_color_prompt

# If this is an xterm set the title to user@host:dir
case "$TERM" in
xterm*|rxvt*)
    PS1="\[\e]0;${debian_chroot:+($debian_chroot)}\u@\h: \w\a\]$PS1"
    ;;
*)
    ;;
esac

# enable color support of ls and also add handy aliases
if [ -x /usr/bin/dircolors ]; then
    test -r ~/.dircolors && eval "$(dircolors -b ~/.dircolors)" || eval "$(dircolors -b)"
    alias ls='ls --color=always'

    alias grep='grep --color=auto'
    alias fgrep='fgrep --color=auto'
    alias egrep='egrep --color=auto'
    alias grp='grep --color=always'
fi

# some more ls aliases
alias l='ls'
alias ll='ls -alF'
alias la='ls -A'
alias lspage='ls -Cw $COLUMNS | less -r'

# Add an "alert" alias for long running commands.  Use like so:
#   sleep 10; alert
alias alert='notify-send --urgency=low -i "$([ $? = 0 ] && echo terminal || echo error)" "$(history|tail -n1|sed -e '\''s/^\s*[0-9]\+\s*//;s/[;&|]\s*alert$//'\'')"'

# Alias definitions.
# You may want to put all your additions into a separate file like
# ~/.bash_aliases, instead of adding them here directly.
# See /usr/share/doc/bash-doc/examples in the bash-doc package.

if [ -f ~/.bash_aliases ]; then
    . ~/.bash_aliases
fi

# enable programmable completion features (you don't need to enable
# this, if it's already enabled in /etc/bash.bashrc and /etc/profile
# sources /etc/bash.bashrc).
if [ -f /etc/bash_completion ] && ! shopt -oq posix; then
    . /etc/bash_completion
fi

if [ -f ~/.localbashrc ]; then
    source ~/.localbashrc
fi

# if this is set, things go wrong when starting some programs (like gvim) from tmux
unset DBUS_SESSION_BUS_ADDRESS

export FIGNORE=%FIGNORE:.pyc
export MANPAGER="less -X"

alias less="less -R"

GREP_OPTIONS="--exclude-dir=\.svn --exclude-dir=\.git --exclude-dir=\.hg --exclude=tags -I"
export GREP_OPTIONS
alias pygrep='grep --include="*.py"'
alias xmlgrep='grep --include="*.xml"'
alias qmlgrep='grep --include="*.qml"'

alias ack='ack-grep'

alias fu='curl -s http://www.commandlinefu.com/commands/browse/sort-by-votes/p... | grep -vE "^$|^#"'

alias tag='ctags -a -R --fields=+l --c-kinds=+p --c++-kinds=+p -ftags'
alias pytag='ctags -a -R --languages="python" --fields=+l --c-kinds=+p --c++-kinds=+p -ftags'

alias nose='nosetests -s'

alias py='python2.7'
alias py27='python2.7'
alias py26='python2.6'

alias clearcache='/sbin/sysctl -w vm.drop_caches=3'

alias ..='cd ..'
alias ...='cd ../..'
alias ....='cd ../../..'
alias .....='cd ../../../..'
alias ~='cd ~'
alias -- -='cd -'

alias d="cd ~/Documents/Dropbox"
alias venom="cd ~/rc/.vim/pathogen/venom"
alias merc="cd ~/rc/.vim/pathogen/mercury"
alias harl="cde ~/rc/.vim/pathogen/harlequin"

# stop global warning message on Ubuntu
alias gvim='UBUNTU_MENUPROXY= gvim'
alias gvimdiff='UBUNTU_MENUPROXY= gvimdiff'

alias g="git"
alias h="hg"
alias v="gvim"

alias upgrade='sudo apt-get -y update && sudo apt-get -y upgrade && sudo apt-get -y dist-upgrade && sudo apt-get -y autoclean && sudo apt-get -y autoremove'

if [[ ! $TERM =~ screen ]]; then
    exec tmux
fi

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh --no-use"  # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion

# Add RVM to PATH for scripting. Make sure this is the last PATH variable change.
export PATH="$PATH:$HOME/.rvm/bin"
