#!/bin/bash
set -e

DOTFILES_DIR="$(cd "$(dirname "$0")" && pwd)"

CHECK=0
QUIET=0
for arg in "$@"; do
  case "$arg" in
    --check) CHECK=1 ;;
    --quiet|-q) QUIET=1 ;;
    -h|--help)
      echo "usage: install.sh [--check] [--quiet]"
      echo "  --check  report what would change without changing anything;"
      echo "           exits 1 if any change is pending"
      echo "  --quiet  print only lines for things that actually changed"
      exit 0
      ;;
    *) echo "unknown option: $arg" >&2; exit 2 ;;
  esac
done

PENDING=0

# Routine "nothing to do" chatter — silenced by --quiet.
say() { [ "$QUIET" = 1 ] || echo "$@"; }

# Gate in front of every side-effecting step: counts the change and, under
# --check, reports it and returns 1 so the caller skips the real work.
pending() {
  PENDING=$((PENDING + 1))
  if [ "$CHECK" = 1 ]; then
    echo "would $1"
    return 1
  fi
  return 0
}

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

seen_key() {
  local k
  for k in "${SEEN_KEYS[@]}"; do
    [ "$k" = "$1" ] && return
  done
  SEEN_KEYS+=("$1")
}

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

  seen_key "$alias"

  if is_skipped "$alias"; then
    # Auto-detach: if dest is still a symlink into this repo, replace it with a
    # real machine-local copy so it can be edited without touching the repo.
    # Copy to a temp sibling first so a failed cp never leaves dest missing.
    if [ -L "$dest" ] && [ "$(readlink "$dest")" = "$src" ]; then
      if pending "detach $dest into a machine-local copy"; then
        cp -R "$src" "$dest.detach.$$"
        rm "$dest"
        mv "$dest.detach.$$" "$dest"
        echo "detach $dest (copied, now machine-local)"
      fi
    fi
    say "skip $dest ($alias in install.local)"
    return
  fi

  if [ -L "$dest" ] && [ "$(readlink "$dest")" = "$src" ]; then
    say "skip $dest (already linked)"
    return
  fi

  # Spell out what the rm -rf below would destroy, so --check can warn before a
  # moved link target silently eats a real file at the new destination.
  local what="link $dest -> $src"
  if [ -L "$dest" ]; then
    what="$what (replaces symlink -> $(readlink "$dest"))"
  elif [ -d "$dest" ]; then
    what="$what (REPLACES EXISTING DIRECTORY)"
  elif [ -e "$dest" ]; then
    what="$what (REPLACES EXISTING FILE)"
  fi

  if pending "$what"; then
    mkdir -p "$(dirname "$dest")"
    rm -rf "$dest"
    ln -s "$src" "$dest"
    echo "link $dest -> $src"
  fi
}

# Install vim-plug if not present
if [ ! -f "$DOTFILES_DIR/.vim/autoload/plug.vim" ]; then
  if pending "install vim-plug"; then
    curl -fLo "$DOTFILES_DIR/.vim/autoload/plug.vim" --create-dirs \
      https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim
    echo "installed vim-plug"
  fi
else
  say "skip vim-plug (already installed)"
fi

# Install pure-prompt if not present. .zshrc references $HOME/.zsh/pure on
# fpath; without it, `prompt pure` fails silently and zsh falls back to
# its default %m%# prompt.
if [ ! -d "$HOME/.zsh/pure" ]; then
  if pending "clone pure-prompt into ~/.zsh/pure"; then
    git clone --depth=1 https://github.com/sindresorhus/pure.git "$HOME/.zsh/pure"
    echo "installed pure-prompt"
  fi
else
  say "skip pure-prompt (already installed)"
fi

# Install zsh-autosuggestions + zsh-syntax-highlighting if not present. .zshrc
# sources both from $HOME/.zsh/ directly (no plugin framework — we dropped
# oh-my-zsh); without them the trailing `source` lines error on a fresh box.
if [ ! -d "$HOME/.zsh/zsh-autosuggestions" ]; then
  if pending "clone zsh-autosuggestions into ~/.zsh"; then
    git clone --depth=1 https://github.com/zsh-users/zsh-autosuggestions.git "$HOME/.zsh/zsh-autosuggestions"
    echo "installed zsh-autosuggestions"
  fi
else
  say "skip zsh-autosuggestions (already installed)"
fi

if [ ! -d "$HOME/.zsh/zsh-syntax-highlighting" ]; then
  if pending "clone zsh-syntax-highlighting into ~/.zsh"; then
    git clone --depth=1 https://github.com/zsh-users/zsh-syntax-highlighting.git "$HOME/.zsh/zsh-syntax-highlighting"
    echo "installed zsh-syntax-highlighting"
  fi
else
  say "skip zsh-syntax-highlighting (already installed)"
fi

# Install Syncthing (menu-bar app) if not present. It's the login daemon that
# syncs the KeePass vaults in ~/syncthing/; pairing/folder setup stays manual.
# Cask, not mise — it's a long-lived daemon, not a per-shell dev tool.
if [ ! -d "/Applications/Syncthing.app" ]; then
  if command -v brew >/dev/null 2>&1; then
    if pending "brew install --cask syncthing"; then
      brew install --cask syncthing
      echo "installed syncthing"
    fi
  else
    say "skip syncthing (brew not on PATH)"
  fi
else
  say "skip syncthing (already installed)"
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
LEGACY_SAVEWINDOW="$HOME/Library/Application Support/iTerm2/Scripts/SaveWindowArrangement.py"
if [ -e "$LEGACY_SAVEWINDOW" ] || [ -L "$LEGACY_SAVEWINDOW" ]; then
  if pending "remove pre-daemon $LEGACY_SAVEWINDOW"; then
    rm -f "$LEGACY_SAVEWINDOW"
    echo "removed pre-daemon SaveWindowArrangement.py"
  fi
fi
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
  if pending "create launchd/hidutil.local.sh"; then
    cat > "$DOTFILES_DIR/launchd/hidutil.local.sh" <<'EOF'
# Per-machine hidutil remaps (gitignored). Sourced AFTER the universal
# Caps Lock -> F18 remap, by the LaunchAgent at login and by install.sh.
# Add hidutil commands here for remaps specific to THIS machine.
# See hidutil.local.sh.example for the format.
EOF
    echo "created launchd/hidutil.local.sh"
  fi
else
  say "skip launchd/hidutil.local.sh (already exists)"
fi

HIDUTIL_LOCAL_LINK="$HOME/.config/hidutil/local.sh"
if [ "$(readlink "$HIDUTIL_LOCAL_LINK" 2>/dev/null)" = "$DOTFILES_DIR/launchd/hidutil.local.sh" ]; then
  say "skip $HIDUTIL_LOCAL_LINK (already linked)"
elif pending "link $HIDUTIL_LOCAL_LINK -> launchd/hidutil.local.sh"; then
  mkdir -p "$HOME/.config/hidutil"
  ln -sfn "$DOTFILES_DIR/launchd/hidutil.local.sh" "$HIDUTIL_LOCAL_LINK"
  echo "link $HIDUTIL_LOCAL_LINK -> $DOTFILES_DIR/launchd/hidutil.local.sh"
fi

# Re-applied unconditionally (hidutil's UserKeyMapping is session-scoped, so
# this is a no-op in effect, not a pending change) — but never under --check,
# which must not touch the running system or report spurious work.
if [ "$CHECK" = 0 ]; then
  hidutil property --set \
    '{"UserKeyMapping":[{"HIDKeyboardModifierMappingSrc":0x700000039,"HIDKeyboardModifierMappingDst":0x70000006D}]}' \
    >/dev/null
  [ -r "$HIDUTIL_LOCAL_LINK" ] && . "$HIDUTIL_LOCAL_LINK" >/dev/null
  say "applied hidutil remaps (Caps Lock → F18 + per-machine local.sh)"
fi

# iTerm2 global prefs. Run with iTerm2 *not* running, otherwise iTerm2's in-memory
# copy is flushed back to disk on quit and overwrites these values. Sets the "rc"
# dynamic profile as default and dims inactive split panes to 10%.
# Rewriting the same values every run is a no-op in effect, so --check neither
# reports nor performs it.
if [ "$CHECK" = 1 ]; then
  :
elif ps -A -o comm | grep -q '/iTerm2$'; then
  say "skip iTerm2 defaults (iTerm2 is running — quit it and re-run install.sh)"
else
  defaults write com.googlecode.iterm2 "Default Bookmark Guid" -string "rc-dotfiles-split-nav"
  defaults write com.googlecode.iterm2 SplitPaneDimmingAmount  -float  0.1
  say "wrote iTerm2 defaults"
fi

# Obsidian vimrc. The only interactive step — gated on a tty (and off under
# --check) so hooks and other non-interactive runs don't die on EOF here.
seen_key obsidian-vimrc
if [ "$CHECK" = 1 ] || [ ! -t 0 ]; then
  say "skip obsidian vimrc (non-interactive run)"
else
  read -p "Obsidian vault path (leave empty to skip): " obsidian_vault
  if [ -n "$obsidian_vault" ]; then
    obsidian_vault="${obsidian_vault/#\~/$HOME}"
    if [ -d "$obsidian_vault" ]; then
      link obsidian-vimrc .obsidian.vimrc "$obsidian_vault/.obsidian.vimrc"
    else
      echo "skip obsidian vimrc (vault not found: $obsidian_vault)"
    fi
  fi
fi

# Create local config files if they don't exist
if [ ! -f ~/.zshrc.local ]; then
  if pending "create ~/.zshrc.local"; then
    touch ~/.zshrc.local
    echo "created ~/.zshrc.local"
  fi
else
  say "skip ~/.zshrc.local (already exists)"
fi

# SOPS age identity — needs to exist at ~/.config/sops/age/keys.txt for
# sops to decrypt secrets/secrets.yaml. If missing, generate a fresh one
# (per-machine; the resulting public key must be added to .sops.yaml on
# any Mac that already decrypts, then `sops updatekeys` re-wraps).
if [ ! -f "$HOME/.config/sops/age/keys.txt" ]; then
  if ! command -v age-keygen >/dev/null 2>&1; then
    echo "sops: age-keygen not on PATH — run \`mise install\` then re-run install.sh"
  elif pending "generate a sops age identity at ~/.config/sops/age/keys.txt"; then
    mkdir -p "$HOME/.config/sops/age"
    age-keygen -o "$HOME/.config/sops/age/keys.txt"
    chmod 600 "$HOME/.config/sops/age/keys.txt"
    echo
    echo "sops: generated fresh age identity at ~/.config/sops/age/keys.txt"
    echo "Add the printed public key (above) to .sops.yaml on a Mac that"
    echo "already decrypts secrets/secrets.yaml, then run:"
    echo "  sops updatekeys ~/rc/secrets/secrets.yaml"
    echo "Commit + push, then \`git pull\` here to be able to decrypt."
  fi
fi

# Per-machine Hammerspoon config (gitignored). Stub returns empty config
# so init.lua's loadfile/return-function check passes — no auto-placement
# until customized. See hammerspoon/local.lua.example for the full API.
if [ ! -f "$DOTFILES_DIR/hammerspoon/local.lua" ]; then
  if pending "create hammerspoon/local.lua"; then
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
  fi
else
  say "skip hammerspoon/local.lua (already exists)"
fi

# Per-machine Finicky container routing (gitignored). finicky.ts imports LOCAL
# from here; an empty stub keeps the import valid on a fresh machine (no
# container routing until customized). See finicky/finicky.local.ts.example.
if [ ! -f "$DOTFILES_DIR/finicky/finicky.local.ts" ]; then
  if pending "create finicky/finicky.local.ts"; then
    cat > "$DOTFILES_DIR/finicky/finicky.local.ts" <<'EOF'
// finicky.local.ts — GITIGNORED per-machine container routing. Imported by
// finicky.ts. See finicky.local.ts.example for the format.
export const LOCAL = [];
EOF
    echo "created finicky/finicky.local.ts"
  fi
else
  say "skip finicky/finicky.local.ts (already exists)"
fi

# Git hooks: after a pull/rebase/checkout, nudge if install.sh targets went
# stale. The hooks only ever run `install.sh --check` — nothing is re-linked
# behind your back. core.hooksPath lives in .git/config, which is machine-local
# and never committed, so it has to be set here rather than shipped in the repo.
seen_key githooks
HOOKS_DIR="$DOTFILES_DIR/githooks"
if git -C "$DOTFILES_DIR" rev-parse --git-dir >/dev/null 2>&1; then
  CURRENT_HOOKS="$(git -C "$DOTFILES_DIR" config --local --get core.hooksPath || true)"
  if is_skipped githooks; then
    if [ "$CURRENT_HOOKS" = "$HOOKS_DIR" ]; then
      if pending "unset core.hooksPath (githooks listed in install.local)"; then
        git -C "$DOTFILES_DIR" config --local --unset core.hooksPath
        echo "unset core.hooksPath"
      fi
    fi
    say "skip githooks (githooks in install.local)"
  elif [ "$CURRENT_HOOKS" = "$HOOKS_DIR" ]; then
    say "skip core.hooksPath (already set)"
  elif pending "set core.hooksPath -> $HOOKS_DIR"; then
    git -C "$DOTFILES_DIR" config --local core.hooksPath "$HOOKS_DIR"
    echo "set core.hooksPath -> $HOOKS_DIR"
  fi
fi

# Per-machine install.sh skip list (gitignored). Written here, after every
# link() call has run, with all aliases listed but commented out — so the
# default file skips nothing. Uncomment a line to skip that target on this
# machine and re-run install.sh.
#
# An existing file is *merged*, not left alone: aliases added since it was
# written get appended (commented out, so behaviour is unchanged), and aliases
# it lists that no longer exist are flagged. Without this, adding a link() call
# left every existing machine's file silently stale — you cannot skip a target
# you cannot see.
if [ ! -f "$SKIP_FILE" ]; then
  if pending "create install.local"; then
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
  fi
else
  MISSING_KEYS=()
  for k in "${SEEN_KEYS[@]}"; do
    grep -qE "^[[:space:]]*#?[[:space:]]*$k[[:space:]]*$" "$SKIP_FILE" || MISSING_KEYS+=("$k")
  done
  if [ ${#MISSING_KEYS[@]} -gt 0 ]; then
    if pending "add to install.local: ${MISSING_KEYS[*]}"; then
      for k in "${MISSING_KEYS[@]}"; do
        echo "# $k" >> "$SKIP_FILE"
      done
      echo "install.local: added ${MISSING_KEYS[*]}"
    fi
  else
    say "skip install.local (up to date)"
  fi

  # A typo'd or removed alias skips nothing and gives no feedback — say so.
  for k in "${SKIP_KEYS[@]}"; do
    is_seen=0
    for s in "${SEEN_KEYS[@]}"; do
      if [ "$s" = "$k" ]; then
        is_seen=1
        break
      fi
    done
    if [ "$is_seen" = 0 ]; then
      echo "warn: install.local lists unknown alias '$k' (no such link target)"
    fi
  done
fi

if [ "$CHECK" = 1 ]; then
  if [ "$PENDING" -gt 0 ]; then
    echo
    echo "install.sh: $PENDING pending change(s) — run ./install.sh"
    exit 1
  fi
  say "install.sh: up to date"
fi
