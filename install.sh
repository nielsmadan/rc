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
