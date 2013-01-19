export CLASSPATH=.:/usr/local/lib/jars/*
export PYLINTRC="$HOME/pylint.rc"

if [ -s "$HOME/.rvm/scripts/rvm" ]; then
    source "$HOME/.rvm/scripts/rvm" # Load RVM into a shell session *as a function*
    PATH=$PATH:$HOME/.rvm/bin # Add RVM to PATH for scripting
fi

if [ -d "$HOME/bin" ] ; then
    PATH=$PATH:$HOME/bin
fi

export PATH

if [ -f ~/.local_bash_profile ]; then
    source ~/.local_bash_profile
fi

[ -f "$HOME/.bashrc" ] && source "$HOME/.bashrc"
