# /etc/rc-profile names an admin-managed machine (bin/system-install); empty elsewhere.
studio = (File.read("/etc/rc-profile").strip rescue "") == "studio"

brew "neovim"
brew "gnupg"
brew "pinentry"
brew "libpq"
brew "bat"
brew "eza"
brew "fd"
brew "flock"
brew "gawk"
brew "lazygit"
brew "ripgrep"
brew "rsync"
brew "the_silver_searcher"
brew "tmux"
brew "tree"
brew "ttyd"
brew "universal-ctags"
brew "zoxide"
brew "git-filter-repo"
brew "git-secret"
brew "stylua"
brew "watchman"

brew "colima"
brew "docker"
brew "docker-buildx"
brew "docker-compose"
brew "docker-credential-helper"

brew "fastlane"
brew "ios-deploy"
brew "periphery"
brew "swiftformat"
brew "swiftlint"
brew "xcode-build-server"

brew "ffmpeg"
brew "poppler"

unless studio
  brew "imagemagick"
  brew "potrace"
  brew "typst"
end

brew "perl"
brew "pkgconf"
brew "redis"

unless studio
  cask "audacity"
  cask "codexbar"
  cask "finicky"
  cask "gcloud-cli"
  cask "hammerspoon"
  cask "keepassxc"
  cask "librewolf"
  cask "maccy"
  cask "neovide-app"
  cask "stats"
  cask "swiftformat-for-xcode"
  cask "ungoogled-chromium"
  cask "wezterm"
  cask "nielsmadan/tap/juggler", trusted: true
end

# The Studio's tools that the MacBook gets elsewhere: mise and uv from their own
# installers, git from Xcode's command line tools.
if studio
  brew "mise"
  brew "uv"
  brew "git"
  brew "context7-mcp"
  brew "et"
  brew "mosh"
end
