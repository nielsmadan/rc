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

# Install Syncthing (menu-bar app) if not present. It's the login daemon that
# syncs the KeePass vaults in ~/syncthing/; pairing/folder setup stays manual.
# Cask, not mise — it's a long-lived daemon, not a per-shell dev tool.
if [ ! -d "/Applications/Syncthing.app" ]; then
  if command -v brew >/dev/null 2>&1; then
    brew install --cask syncthing
    echo "installed syncthing"
  else
    echo "skip syncthing (brew not on PATH)"
  fi
else
  echo "skip syncthing (already installed)"
fi

link vimrc            .vimrc           ~/.vimrc
link gvimrc           .gvimrc          ~/.gvimrc
link vim              .vim             ~/.vim
link gitconfig        .gitconfig       ~/.gitconfig
link zshrc            .zshrc           ~/.zshrc
link devrc            .devrc           ~/.devrc
link tmux             tmux/tmux.conf   ~/.tmux.conf
link kitty            kitty/kitty.conf ~/.config/kitty/kitty.conf
link wezterm          wezterm/wezterm.lua ~/.config/wezterm/wezterm.lua
link nvim             nvim             ~/.config/nvim
link mise             mise/config.toml ~/.config/mise/config.toml
link gitignore        git/ignore       ~/.config/git/ignore
link secrets          secrets/secrets.yaml ~/.config/sops/secrets.yaml
link hammerspoon      hammerspoon      ~/.hammerspoon
link finicky          finicky/finicky.ts ~/.finicky.ts
# SaveWindowArrangement.py runs as an AutoLaunch daemon (auto-saves window
# arrangements + registers the Cmd+S RPC). Drop the pre-daemon manual-script
# symlink from the plain Scripts dir if a prior install left one there.
rm -f "$HOME/Library/Application Support/iTerm2/Scripts/SaveWindowArrangement.py"
link iterm2-savewindow iterm2/SaveWindowArrangement.py "$HOME/Library/Application Support/iTerm2/Scripts/AutoLaunch/SaveWindowArrangement.py"
link iterm2-clonetab  iterm2/CloneRepoToTab.py        "$HOME/Library/Application Support/iTerm2/Scripts/AutoLaunch/CloneRepoToTab.py"
link iterm2-profile   iterm2/dynamic-profile.json     "$HOME/Library/Application Support/iTerm2/DynamicProfiles/rc.json"

# LaunchAgent: hidutil key remaps, re-applied at every login because hidutil's
# UserKeyMapping is session-scoped (lost across reboot/logout). Two layers,
# mirroring the hammerspoon init.lua / local.lua split:
#   1. Universal (committed, here + in the plist): Caps Lock → F18, the
#      Hammerspoon modal-entry trigger. Applied to every keyboard.
#   2. Per-machine (gitignored launchd/hidutil.local.sh, symlinked to a fixed
#      path so the LaunchAgent can source it by absolute path): extra/override
#      remaps for this machine only — e.g. an ISO built-in keyboard's § →
#      backtick fix. Sourced AFTER the universal set so it can override per
#      device. See launchd/hidutil.local.sh.example.
# Both the plist and the immediate-apply below run the universal set, then
# source the local file if present, so the mapping is live without a logout.
link hidutil launchd/com.nielsmadan.hidutil-capslock-to-f18.plist \
  "$HOME/Library/LaunchAgents/com.nielsmadan.hidutil-capslock-to-f18.plist"

# Per-machine hidutil remaps (gitignored). Empty stub if missing (so other
# machines apply only the universal remap), symlinked to a fixed location the
# LaunchAgent sources by absolute path. Customize from hidutil.local.sh.example.
if [ ! -f "$DOTFILES_DIR/launchd/hidutil.local.sh" ]; then
  cat > "$DOTFILES_DIR/launchd/hidutil.local.sh" <<'EOF'
# Per-machine hidutil remaps (gitignored). Sourced AFTER the universal
# Caps Lock -> F18 remap, by the LaunchAgent at login and by install.sh.
# Add hidutil commands here for remaps specific to THIS machine.
# See hidutil.local.sh.example for the format.
EOF
  echo "created launchd/hidutil.local.sh"
else
  echo "skip launchd/hidutil.local.sh (already exists)"
fi
mkdir -p "$HOME/.config/hidutil"
ln -sf "$DOTFILES_DIR/launchd/hidutil.local.sh" "$HOME/.config/hidutil/local.sh"

hidutil property --set \
  '{"UserKeyMapping":[{"HIDKeyboardModifierMappingSrc":0x700000039,"HIDKeyboardModifierMappingDst":0x70000006D}]}' \
  >/dev/null
[ -r "$HOME/.config/hidutil/local.sh" ] && . "$HOME/.config/hidutil/local.sh" >/dev/null
echo "applied hidutil remaps (Caps Lock → F18 + per-machine local.sh)"

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

# Per-machine Finicky container routing (gitignored). finicky.ts imports LOCAL
# from here; an empty stub keeps the import valid on a fresh machine (no
# container routing until customized). See finicky/finicky.local.ts.example.
if [ ! -f "$DOTFILES_DIR/finicky/finicky.local.ts" ]; then
  cat > "$DOTFILES_DIR/finicky/finicky.local.ts" <<'EOF'
// finicky.local.ts — GITIGNORED per-machine container routing. Imported by
// finicky.ts. See finicky.local.ts.example for the format.
export const LOCAL = [];
EOF
  echo "created finicky/finicky.local.ts"
else
  echo "skip finicky/finicky.local.ts (already exists)"
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
