#!/bin/bash
set -e

DOTFILES_DIR="$(cd "$(dirname "$0")" && pwd)"

link() {
  local src="$DOTFILES_DIR/$1"
  local dest="$2"

  mkdir -p "$(dirname "$dest")"

  if [ -L "$dest" ] && [ "$(readlink "$dest")" = "$src" ]; then
    echo "skip $dest (already linked)"
    return
  fi

  rm -rf "$dest"
  ln -s "$src" "$dest"
  echo "link $dest -> $src"
}

# Install vim-plug if not present
if [ ! -f "$DOTFILES_DIR/.vim/autoload/plug.vim" ]; then
  curl -fLo "$DOTFILES_DIR/.vim/autoload/plug.vim" --create-dirs \
    https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim
  echo "installed vim-plug"
else
  echo "skip vim-plug (already installed)"
fi

# Install pure-prompt if not present. .zshrc references $HOME/.zsh/pure on
# fpath; without it, `prompt pure` fails silently and zsh falls back to
# its default %m%# prompt.
if [ ! -d "$HOME/.zsh/pure" ]; then
  git clone --depth=1 https://github.com/sindresorhus/pure.git "$HOME/.zsh/pure"
  echo "installed pure-prompt"
else
  echo "skip pure-prompt (already installed)"
fi

link .vimrc          ~/.vimrc
link .gvimrc         ~/.gvimrc
link .vim            ~/.vim
link .gitconfig      ~/.gitconfig
link .gitignore      ~/.gitignore
link .zshrc          ~/.zshrc
link .devrc          ~/.devrc
link kitty.conf      ~/.config/kitty/kitty.conf
link nvim            ~/.config/nvim
link mise/config.toml ~/.config/mise/config.toml
link hammerspoon     ~/.hammerspoon
link iterm2/SaveWindowArrangement.py "$HOME/Library/Application Support/iTerm2/Scripts/SaveWindowArrangement.py"
link iterm2/dynamic-profile.json   "$HOME/Library/Application Support/iTerm2/DynamicProfiles/rc.json"

# LaunchAgent: hidutil remap of Caps Lock → F18 (used by Hammerspoon as
# modal-entry trigger). The plist re-applies the mapping at every login
# because hidutil's setting is session-scoped. Also apply it immediately
# so it works without requiring a logout.
link launchd/com.nielsmadan.hidutil-capslock-to-f18.plist \
  "$HOME/Library/LaunchAgents/com.nielsmadan.hidutil-capslock-to-f18.plist"
hidutil property --set \
  '{"UserKeyMapping":[{"HIDKeyboardModifierMappingSrc":0x700000039,"HIDKeyboardModifierMappingDst":0x70000006D}]}' \
  >/dev/null
echo "applied hidutil Caps Lock → F18 remap"

# iTerm2 global prefs. Run with iTerm2 *not* running, otherwise iTerm2's in-memory
# copy is flushed back to disk on quit and overwrites these values. Sets the "rc"
# dynamic profile as default and dims inactive split panes to 10%.
if ps -A -o comm | grep -q '/iTerm2$'; then
  echo "skip iTerm2 defaults (iTerm2 is running — quit it and re-run install.sh)"
else
  defaults write com.googlecode.iterm2 "Default Bookmark Guid" -string "rc-dotfiles-split-nav"
  defaults write com.googlecode.iterm2 SplitPaneDimmingAmount  -float  0.1
  echo "wrote iTerm2 defaults"
fi

# Obsidian vimrc
read -p "Obsidian vault path (leave empty to skip): " obsidian_vault
if [ -n "$obsidian_vault" ]; then
  obsidian_vault="${obsidian_vault/#\~/$HOME}"
  if [ -d "$obsidian_vault" ]; then
    link .obsidian.vimrc "$obsidian_vault/.obsidian.vimrc"
  else
    echo "skip obsidian vimrc (vault not found: $obsidian_vault)"
  fi
fi

# Create local config files if they don't exist
if [ ! -f ~/.zshrc.local ]; then
  touch ~/.zshrc.local
  echo "created ~/.zshrc.local"
else
  echo "skip ~/.zshrc.local (already exists)"
fi
