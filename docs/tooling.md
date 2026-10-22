# Tooling and shell prompt

`mise/config.toml` (symlinked to `~/.config/mise/config.toml`) pins node/ruby/python/java/bun/go/fzf/pnpm/sops/age. `mise activate` is hooked in `.zshrc`.

Global npm CLIs are managed through mise's `npm:` backend (`npm:wrangler`, `npm:firebase-tools`, `npm:agent-browser`) so they survive `node` version bumps and stay reproducible. Add new ones with `mise use -g npm:<pkg>` rather than `npm install -g`.

**mise vs brew.** Default to **mise** for standalone dev CLIs and language-ecosystem tools — version-pinned in `mise/config.toml` and auto-replicated across machines. Use **brew** for GUI casks (`.app`s like Finicky), long-running daemons/services, C libraries, and tools needing a launchd unit or absolute path. When moving a tool brew→mise, `brew uninstall` it first so the mise shim wins on `PATH`.

**Brewfile.** Everything brew-managed is declared in `Brewfile` at the repo root; `install.sh` installs Homebrew itself when missing (interactive runs only — its installer prompts for sudo), then runs `brew bundle install --no-upgrade` whenever `brew bundle check` reports something missing. When you `brew install` something worth keeping, add it there; when you uninstall something, remove its line, or the next `install.sh` reinstalls it. List the tools you use directly, even when another package already pulls them in (`neovim` is a dependency of the Neovide cask), so they survive that package going away. Skip it per machine with `brewfile` in `install.local`. Syncthing keeps its own `install.sh` step, since it may be installed outside brew.

**Vault via mise/aqua:** install with an explicit pin (`aqua:hashicorp/vault@<version>`), **not** `@latest` — aqua's resolver picks bad tags (e.g. `2.0.1` has no darwin build and 404s). Pinning also sidesteps the BSL-relicense tap churn.

**Railway CLI** is mise-managed (pinned in `mise/config.toml`, sops-wrapped so `RAILWAY_API_TOKEN` is injected per call). Upgrade with `mise upgrade railway`, not `railway upgrade` (fails: "Could not detect install method"). It needs a **personal account** token, not a team/workspace token — a team token fails the CLI's `me { email }` identity gate, making every command return "Unauthorized". Generate an unscoped token at railway.com/account/tokens; verify with `railway whoami`. The sops-injected env var shadows any `railway login` session, so the token is the only auth lever.


`.zshrc` puts `~/.zsh/pure` on `fpath` and runs `prompt pure`. If the directory is missing, `prompt pure` fails silently and zsh falls back to its default `%m%#` prompt — `install.sh` clones `sindresorhus/pure` into `~/.zsh/pure` to prevent that.
