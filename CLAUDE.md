# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository purpose

Personal dotfiles for macOS. `install.sh` symlinks files from this repo into `$HOME` (and a few other places like `~/.config/nvim`, `~/.config/kitty`, iTerm2's scripts dir). Editing a file here = editing the live config. Re-running `install.sh` is idempotent (skips already-correct symlinks).

## Two editor configs coexist

This repo maintains **both** a legacy Vim config and a modern Neovim config in parallel — they are not migrating from one to the other.

- **Vim** — single-file `.vimrc` (~537 lines), plugins via `vim-plug`, completion via `coc.nvim`, linting/fixing via `ALE`, fuzzy finding via `fzf.vim`.
- **Neovim** — Lua config under `nvim/`, plugins via `lazy.nvim`, completion via `blink.cmp` + `nvim-lspconfig` + `mason`, fuzzy finding via `snacks.nvim` picker, AI via `codecompanion.nvim`. `nvim/init.lua` also `:source`s `nvim/vimrc.vim` for shared baseline mappings (leader, `jj`→Esc, window nav, system clipboard, etc.).

Leader is `,` in both. Both define the same diff-mode mappings (arrows for hunk nav/pull/push, `<M-1/2/3>` for `:diffget N`, `<M-p>N` for `:diffput N`).

## Keybinding docs — keep them in sync

`VIM_KEYBINDINGS.md` and `NVIM_KEYBINDINGS.md` are hand-curated tables of *custom* mappings. **Whenever you add, remove, or change a mapping in `.vimrc`, `nvim/vimrc.vim`, or any `nvim/lua/**` file, update the matching keybindings doc in the same change.** `NVIM_KEYBINDINGS.md` still references source files (the nvim config is split across multiple files); `VIM_KEYBINDINGS.md` no longer tracks line numbers.

## Neovim layout

```
nvim/
  init.lua              # bootstraps lazy + sources vimrc.vim
  vimrc.vim             # shared vim-style baseline (mappings, statusline, colorscheme)
  lazy-lock.json        # plugin lockfile (gitignored)
  lua/
    config/
      lazy.lua          # lazy.nvim bootstrap; sets <leader>, requires the other config/* files
      opt.lua           # vim.opt.* settings
      gui.lua           # neovide options
      cmd.lua           # ad-hoc commands (e.g. <leader>q syntax dump)
      diff.lua          # diff-mode keymaps (works for both `nvim -d` and diffview windows)
    plugins/            # auto-imported by lazy via { import = "plugins" }
      default.lua       # treesitter, snacks, flash, trouble, diffview, oil, conform, mini.*
      lsp.lua           # lspconfig + mason + blink.cmp; LspAttach autocmd defines gd/gr/gI/<leader>rn/...
      ai.lua            # codecompanion.nvim (claude_code ACP adapter)
      colorscheme.lua   # loads `harlequin` from ~/wrksp/harlequin (local, not in this repo)
```

Adding a new plugin = drop a spec into an existing `nvim/lua/plugins/*.lua` (or a new file there — lazy auto-imports the directory). `nvim/lua/config/*.lua` files only run if `require`d explicitly from `lazy.lua`.

The `harlequin` colorscheme is a separate local repo at `~/wrksp/harlequin` referenced by both `.vimrc` (`Plug '~/wrksp/harlequin'`) and `nvim/lua/plugins/colorscheme.lua` (`dir = "~/wrksp/harlequin"`). Don't try to install it from a remote.

## Vim quirks worth knowing

- `<leader>f` is bound twice in `.vimrc`: CoC's `coc-format-selected` (line ~330) is later overridden in normal mode by ALE's `ToggleFormatOnWrite` (line ~494). The visual-mode binding still goes to CoC.
- ALE picks the JS/TS fixer per-buffer via `s:SetJSFixer()`: `biome` if a `biome.json[c]` is found upward from the file, else `prettierd`. ALE is also configured to ignore `tsserver` to avoid overlap with CoC.
- `:TSCheck`, `:Lint`, `:Knip` shell out via `vim-dispatch` and route results to the quickfix list; `<leader>q` opens it (`botright copen`).

## Git integration

`.gitconfig` wires Neovide as both `diff.tool` and `merge.tool`. The custom `git d` / `git d1` / `git dc` aliases launch `neovide --no-fork -c DiffviewOpen ...` for whole-repo diffs (no args) or fall through to per-file `git difftool` (with args). Editor for commit messages is `mvim -f`.

## Hammerspoon

`hammerspoon/init.lua` is symlinked to `~/.hammerspoon/init.lua`. The config auto-reloads on save via `hs.pathwatcher`. Currently it does one thing: auto-moves windows of the apps listed in `EDITOR_APPS` (Neovide, MacVim, "Code" for VS Code) to the monitor whose name matches the `MAIN_SCREEN_NAME` constant at the top of the file. The move triggers on window creation (`hs.window.filter` → `windowCreated`) and on screen-configuration changes (`hs.screen.watcher`) — so plugging the main monitor in re-homes already-open editor windows. If `MAIN_SCREEN_NAME` is blank or doesn't match, the move logic no-ops silently. Every screen-config change also posts an `hs.alert` listing connected screen names (and prints to the Hammerspoon Console) so the right name can be copied into the constant.

## Tool versions

`mise/config.toml` (symlinked to `~/.config/mise/config.toml`) pins node/ruby/python/java/bun/go/fzf/pnpm. `mise activate` is hooked in `.zshrc`.

## Local-only files (not in this repo)

`.zshrc` sources `~/.airc`, `~/.devrc`, and `~/.zshrc.local` if present (`.devrc` is in the repo and symlinked in; the others are user-local). `.gitconfig` includes `~/.gitconfig-local`. Don't expect to find these here.
