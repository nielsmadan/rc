#!/bin/bash
set -e

DOTFILES_DIR="$(cd "$(dirname "$0")" && pwd)"

# Per-machine skip list (gitignored). Each uncommented line is the alias of a
# link target to leave alone on this machine. The file is generated at the end
# of this script with every alias listed but commented out.
SKIP_FILE="$DOTFILES_DIR/install.local"
SKIP_KEYS=()
if [ -f "$SKIP_FILE" ]; then
  while IFS= read -r line || [ -n "$line" ]; do
    line="${line%%#*}"
    line="${line//[[:space:]]/}"
    [ -n "$line" ] && SKIP_KEYS+=("$line")
  done < "$SKIP_FILE"
fi

# Every alias passed to link(), in call order — single source of truth for the
# generated install.local stub.
SEEN_KEYS=()

is_skipped() {
  local k
  for k in "${SKIP_KEYS[@]}"; do
    [ "$k" = "$1" ] && return 0
  done
  return 1
}

link() {
  local alias="$1"
  local src="$DOTFILES_DIR/$2"
  local dest="$3"

  SEEN_KEYS+=("$alias")

  if is_skipped "$alias"; then
    # Auto-detach: if dest is still a symlink into this repo, replace it with a
    # real machine-local copy so it can be edited without touching the repo.
    # Copy to a temp sibling first so a failed cp never leaves dest missing.
    if [ -L "$dest" ] && [ "$(readlink "$dest")" = "$src" ]; then
      cp -R "$src" "$dest.detach.$$"
      rm "$dest"
      mv "$dest.detach.$$" "$dest"
      echo "detach $dest (copied, now machine-local)"
    fi
    echo "skip $dest ($alias in install.local)"
    return
  fi

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

# Install zsh-autosuggestions + zsh-syntax-highlighting if not present. .zshrc
# sources both from $HOME/.zsh/ directly (no plugin framework — we dropped
# oh-my-zsh); without them the trailing `source` lines error on a fresh box.
if [ ! -d "$HOME/.zsh/zsh-autosuggestions" ]; then
  git clone --depth=1 https://github.com/zsh-users/zsh-autosuggestions.git "$HOME/.zsh/zsh-autosuggestions"
  echo "installed zsh-autosuggestions"
else
  echo "skip zsh-autosuggestions (already installed)"
fi

if [ ! -d "$HOME/.zsh/zsh-syntax-highlighting" ]; then
  git clone --depth=1 https://github.com/zsh-users/zsh-syntax-highlighting.git "$HOME/.zsh/zsh-syntax-highlighting"
  echo "installed zsh-syntax-highlighting"
else
  echo "skip zsh-syntax-highlighting (already installed)"
fi

link vimrc            .vimrc           ~/.vimrc
link gvimrc           .gvimrc          ~/.gvimrc
link vim              .vim             ~/.vim
link gitconfig        .gitconfig       ~/.gitconfig
link zshrc            .zshrc           ~/.zshrc
link devrc            .devrc           ~/.devrc
link kitty            kitty/kitty.conf ~/.config/kitty/kitty.conf
link wezterm          wezterm/wezterm.lua ~/.config/wezterm/wezterm.lua
link nvim             nvim             ~/.config/nvim
link mise             mise/config.toml ~/.config/mise/config.toml
link gitignore        git/ignore       ~/.config/git/ignore
link secrets          secrets/secrets.yaml ~/.config/sops/secrets.yaml
link hammerspoon      hammerspoon      ~/.hammerspoon
# SaveWindowArrangement.py runs as an AutoLaunch daemon (auto-saves window
# arrangements + registers the Cmd+S RPC). Drop the pre-daemon manual-script
# symlink from the plain Scripts dir if a prior install left one there.
rm -f "$HOME/Library/Application Support/iTerm2/Scripts/SaveWindowArrangement.py"
link iterm2-savewindow iterm2/SaveWindowArrangement.py "$HOME/Library/Application Support/iTerm2/Scripts/AutoLaunch/SaveWindowArrangement.py"
link iterm2-clonetab  iterm2/CloneRepoToTab.py        "$HOME/Library/Application Support/iTerm2/Scripts/AutoLaunch/CloneRepoToTab.py"
link iterm2-profile   iterm2/dynamic-profile.json     "$HOME/Library/Application Support/iTerm2/DynamicProfiles/rc.json"

# LaunchAgent: hidutil remap of Caps Lock → F18 (used by Hammerspoon as
# modal-entry trigger). The plist re-applies the mapping at every login
# because hidutil's setting is session-scoped. Also apply it immediately
# so it works without requiring a logout.
link hidutil launchd/com.nielsmadan.hidutil-capslock-to-f18.plist \
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
    link obsidian-vimrc .obsidian.vimrc "$obsidian_vault/.obsidian.vimrc"
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

# SOPS age identity — needs to exist at ~/.config/sops/age/keys.txt for
# sops to decrypt secrets/secrets.yaml. If missing, generate a fresh one
# (per-machine; the resulting public key must be added to .sops.yaml on
# any Mac that already decrypts, then `sops updatekeys` re-wraps).
if [ ! -f "$HOME/.config/sops/age/keys.txt" ]; then
  if command -v age-keygen >/dev/null 2>&1; then
    mkdir -p "$HOME/.config/sops/age"
    age-keygen -o "$HOME/.config/sops/age/keys.txt"
    chmod 600 "$HOME/.config/sops/age/keys.txt"
    echo
    echo "sops: generated fresh age identity at ~/.config/sops/age/keys.txt"
    echo "Add the printed public key (above) to .sops.yaml on a Mac that"
    echo "already decrypts secrets/secrets.yaml, then run:"
    echo "  sops updatekeys ~/rc/secrets/secrets.yaml"
    echo "Commit + push, then \`git pull\` here to be able to decrypt."
  else
    echo "sops: age-keygen not on PATH — run \`mise install\` then re-run install.sh"
  fi
fi

# Per-machine Hammerspoon config (gitignored). Stub returns empty config
# so init.lua's loadfile/return-function check passes — no auto-placement
# until customized. See hammerspoon/local.lua.example for the full API.
if [ ! -f "$DOTFILES_DIR/hammerspoon/local.lua" ]; then
  cat > "$DOTFILES_DIR/hammerspoon/local.lua" <<'EOF'
-- Per-machine Hammerspoon config. See local.lua.example for the API.
return function(h)
  return {
    -- main_screen    = "...",
    -- app_placements = {},
    -- window_rules   = {},
  }
end
EOF
  echo "created hammerspoon/local.lua"
else
  echo "skip hammerspoon/local.lua (already exists)"
fi

# Per-machine install.sh skip list (gitignored). Generated here, after every
# link() call has run, with all aliases listed but commented out — so the
# default file skips nothing. Uncomment a line to skip that target on this
# machine and re-run install.sh.
if [ ! -f "$SKIP_FILE" ]; then
  {
    echo "# install.local — per-machine install.sh skip list (gitignored)."
    echo "#"
    echo "# Uncomment an alias to skip that target on THIS machine. install.sh"
    echo "# then leaves the destination alone; if it is currently a symlink into"
    echo "# this repo it is detached into a real, machine-local copy you can edit"
    echo "# freely. Re-comment a line to hand the target back to the repo symlink."
    echo "#"
    echo "# All link targets:"
    for k in "${SEEN_KEYS[@]}"; do
      echo "# $k"
    done
  } > "$SKIP_FILE"
  echo "created install.local"
else
  echo "skip install.local (already exists)"
fi
