export CLASSPATH=.:/usr/local/lib/jars/*
export PYLINTRC="$HOME/pylint.rc"
export GEM_HOME=~/.gem

if [ -s "$HOME/.rvm/scripts/rvm" ]; then
    source "$HOME/.rvm/scripts/rvm" # Load RVM into a shell session *as a function*
    PATH=$PATH:$HOME/.rvm/bin # Add RVM to PATH for scripting
fi

if [ -s "$HOME/.cabal/bin" ]; then
    PATH=$PATH:$HOME/.cabal/bin
fi

if [ -d "$HOME/bin" ] ; then
    PATH="$HOME/bin:$PATH"
fi

export PATH

if [ -f ~/.local_bash_profile ]; then
    source ~/.local_bash_profile
fi

[ -f "$HOME/.bashrc" ] && source "$HOME/.bashrc"

if [ -f ~/.git-completion.bash ]; then
    . ~/.git-completion.bash
    __git_complete g __git_main
fi

complete -F _command launch
