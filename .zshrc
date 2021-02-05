# If you come from bash you might have to change your $PATH.
  # export PATH=$HOME/bin:/usr/local/bin:$PATH

# Path to your oh-my-zsh installation.
export ZSH=/Users/nielsm/.oh-my-zsh
export ANDROID_HOME=/Users/nielsm/Library/Android/sdk

export PATH=$PATH:/Users/nielsm/.fastlane/bin:/Users/nielsm/bin

# Set name of the theme to load. Optionally, if you set this to "random"
# it'll load a random theme each time that oh-my-zsh is loaded.
# See https://github.com/robbyrussell/oh-my-zsh/wiki/Themes
ZSH_THEME="af-magic"

# Uncomment the following line to enable command auto-correction.
ENABLE_CORRECTION="true"

# Uncomment the following line if you want to change the command execution time
# stamp shown in the history command output.
# The optional three formats: "mm/dd/yyyy"|"dd.mm.yyyy"|"yyyy-mm-dd"
# HIST_STAMPS="mm/dd/yyyy"

# Which plugins would you like to load? (plugins can be found in ~/.oh-my-zsh/plugins/*)
# Custom plugins may be added to ~/.oh-my-zsh/custom/plugins/
# Example format: plugins=(rails git textmate ruby lighthouse)
# Add wisely, as too many plugins slow down shell startup.
plugins=(brew extract git history macports node npm vi-mode themes react-native yarn)

source $ZSH/oh-my-zsh.sh

alias bn="./node_modules/.bin/babel-node"
alias hl="nodemon --exec 'heroku local' --signal SIGTERM"
alias m="mvim"
alias gat="gatsby"
alias gatd="gatsby develop"
alias rniosSE="react-native run-ios --simulator=\"iPhone SE\""
alias rnios7="react-native run-ios --simulator=\"iPhone 7\""
alias rnios8="react-native run-ios --simulator=\"iPhone 8\""
alias rnios7plus="react-native run-ios --simulator=\"iPhone 7 Plus (12.4)\"&& react-native log-ios"
alias rniosXR="react-native run-ios --simulator=\"iPhone Xʀ\"&& react-native log-ios"
alias rnios11="react-native run-ios --simulator=\"iPhone 11\""
alias rniospad="react-native run-ios --simulator=\"iPad (6th generation) (12.4)\"&& react-native log-ios"
alias rnand="react-native run-android && react-native log-android"
alias rc="cd ~/rc"

unsetopt correct_all

export JAVA_HOME=/Library/Java/Home
export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8

export NVM_DIR=~/.nvm
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"

eval "$(pyenv init -)"
