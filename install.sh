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

# Create local config files if they don't exist
if [ ! -f ~/.zshrc.local ]; then
  touch ~/.zshrc.local
  echo "created ~/.zshrc.local"
else
  echo "skip ~/.zshrc.local (already exists)"
fi
