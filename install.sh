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

link .vimrc          ~/.vimrc
link .gvimrc         ~/.gvimrc
link .vim            ~/.vim
link .gitconfig      ~/.gitconfig
link .gitignore      ~/.gitignore
link .zshrc          ~/.zshrc
link .devrc          ~/.devrc
link kitty.conf      ~/.config/kitty/kitty.conf
