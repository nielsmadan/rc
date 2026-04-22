# Neovim custom keybindings

Leader is `,`. Only **custom** bindings are listed here — core vim defaults are not repeated.

## Global

| Key | Mode | Action | Source |
|---|---|---|---|
| `<leader>q` | n | Print syntax group under cursor | `nvim/lua/config/cmd.lua` |

## Completion — blink.cmp

Active in insert mode while the completion menu is visible (falls through otherwise).

| Key | Mode | Action | Source |
|---|---|---|---|
| `<C-k>` | i | Select previous item | `nvim/lua/plugins/lsp.lua` |
| `<C-j>` | i | Select next item | `nvim/lua/plugins/lsp.lua` |
| `<C-Space>` | i | Show menu / toggle docs | `nvim/lua/plugins/lsp.lua` |
| `<C-e>` | i | Hide menu | `nvim/lua/plugins/lsp.lua` |
| `<CR>` | i | Accept current item (no preselect) | `nvim/lua/plugins/lsp.lua` |
| `<C-b>` | i | Snippet jump backward | `nvim/lua/plugins/lsp.lua` |
| `<C-f>` | i | Snippet jump forward | `nvim/lua/plugins/lsp.lua` |

## Picker — snacks.nvim

### Open a picker

| Key | Mode | Action | Source |
|---|---|---|---|
| `<C-g>` | n | Find files | `nvim/lua/plugins/default.lua` |
| `<leader><C-g>` | n | Git files | `nvim/lua/plugins/default.lua` |
| `<leader>f` | n | Live grep | `nvim/lua/plugins/default.lua` |
| `<leader>qq` | n | Buffers | `nvim/lua/plugins/default.lua` |
| `<leader>qa` | n | Help tags | `nvim/lua/plugins/default.lua` |

### Inside a picker's input window

| Key | Mode | Action | Source |
|---|---|---|---|
| `<C-c>` | i/n | Close picker | `nvim/lua/plugins/default.lua` |
| `<C-k>` | i/n | Move selection down (intentional j/k swap) | `nvim/lua/plugins/default.lua` |
| `<C-j>` | i/n | Move selection up (intentional j/k swap) | `nvim/lua/plugins/default.lua` |

Native snacks defaults also active: `<Esc>`/`q` close, `<Tab>`/`<S-Tab>` toggle selection, `<CR>` confirm.

## Jumps — flash.nvim

| Key | Mode | Action | Source |
|---|---|---|---|
| `s` | n/x/o | Flash jump | `nvim/lua/plugins/default.lua` |
| `S` | n/x/o | Flash treesitter | `nvim/lua/plugins/default.lua` |
| `r` | o | Remote flash | `nvim/lua/plugins/default.lua` |
| `R` | o/x | Treesitter search | `nvim/lua/plugins/default.lua` |
| `<C-s>` | c | Toggle flash search | `nvim/lua/plugins/default.lua` |
| `<leader><leader>w` | n/x/o | Flash forward (no wrap, single window) | `nvim/lua/plugins/default.lua` |
| `<leader><leader>b` | n/x/o | Flash backward (no wrap, single window) | `nvim/lua/plugins/default.lua` |

## Diagnostics / LSP lists — trouble.nvim

| Key | Mode | Action | Source |
|---|---|---|---|
| `<leader>xx` | n | Toggle diagnostics (all buffers) | `nvim/lua/plugins/default.lua` |
| `<leader>xX` | n | Toggle buffer diagnostics | `nvim/lua/plugins/default.lua` |
| `<leader>cs` | n | Toggle symbols | `nvim/lua/plugins/default.lua` |
| `<leader>cl` | n | Toggle LSP defs/refs (right pane) | `nvim/lua/plugins/default.lua` |
| `<leader>xL` | n | Toggle location list | `nvim/lua/plugins/default.lua` |
| `<leader>xQ` | n | Toggle quickfix list | `nvim/lua/plugins/default.lua` |

## AI — codecompanion.nvim

| Key | Mode | Action | Source |
|---|---|---|---|
| `<leader>aa` | n/v | CodeCompanion actions menu | `nvim/lua/plugins/ai.lua` |
| `<leader>at` | n/v | Toggle chat pane | `nvim/lua/plugins/ai.lua` |
| `<leader>ac` | v | Add selection to chat | `nvim/lua/plugins/ai.lua` |
| `<leader>ai` | n/v | Inline (`:CodeCompanion `) | `nvim/lua/plugins/ai.lua` |

## File explorer — oil.nvim

| Key | Mode | Action | Source |
|---|---|---|---|
| `-` | n | Open current file's parent dir in oil (plugin default) | `nvim/lua/plugins/default.lua` |
| `<leader><leader>f` | n | Open current file's dir in oil | `nvim/lua/plugins/default.lua` |
| `<leader><leader>r` | n | Open cwd (project root) in oil | `nvim/lua/plugins/default.lua` |

## LSP — buffer-local (active after LSP attaches)

| Key | Mode | Action | Source |
|---|---|---|---|
| `gd` | n | Goto definition (Snacks picker) | `nvim/lua/plugins/lsp.lua` |
| `gr` | n | Goto references (Snacks picker) | `nvim/lua/plugins/lsp.lua` |
| `gI` | n | Goto implementation (Snacks picker) | `nvim/lua/plugins/lsp.lua` |
| `<leader>D` | n | Type definition (Snacks picker) | `nvim/lua/plugins/lsp.lua` |
| `<leader>ds` | n | Document symbols (Snacks picker) | `nvim/lua/plugins/lsp.lua` |
| `<leader>ws` | n | Workspace symbols (Snacks picker) | `nvim/lua/plugins/lsp.lua` |
| `<leader>rn` | n | Rename symbol | `nvim/lua/plugins/lsp.lua` |
| `<leader>ca` | n/x | Code action | `nvim/lua/plugins/lsp.lua` |
| `gD` | n | Goto declaration | `nvim/lua/plugins/lsp.lua` |
| `<leader>th` | n | Toggle inlay hints (if server supports) | `nvim/lua/plugins/lsp.lua` |

## Diff mode — buffer-local (when `&diff` is set)

Applies to `git difftool`/`mergetool` sessions and diffview.nvim diff windows.

| Key | Mode | Action | Source |
|---|---|---|---|
| `<Down>` | n | Next hunk (`]c`) | `nvim/lua/config/diff.lua` |
| `<Up>` | n | Previous hunk (`[c`) | `nvim/lua/config/diff.lua` |
| `<Left>` | n | Pull hunk from other side (`do`) | `nvim/lua/config/diff.lua` |
| `<Right>` | n | Push hunk to other side (`dp`) | `nvim/lua/config/diff.lua` |
| `<M-r>` | n | `:diffupdate` | `nvim/lua/config/diff.lua` |
| `<M-d>` | n | Next hunk | `nvim/lua/config/diff.lua` |
| `<M-u>` | n | Previous hunk | `nvim/lua/config/diff.lua` |
| `<M-1>` | n | `:diffget 1` | `nvim/lua/config/diff.lua` |
| `<M-2>` | n | `:diffget 2` | `nvim/lua/config/diff.lua` |
| `<M-3>` | n | `:diffget 3` | `nvim/lua/config/diff.lua` |
| `<M-g>` | n | `:diffget` | `nvim/lua/config/diff.lua` |
| `<M-p>1` | n | `:diffput 1` | `nvim/lua/config/diff.lua` |
| `<M-p>2` | n | `:diffput 2` | `nvim/lua/config/diff.lua` |
| `<M-p>3` | n | `:diffput 3` | `nvim/lua/config/diff.lua` |
| `<M-p><M-p>` | n | `:diffput` | `nvim/lua/config/diff.lua` |
| `<leader><C-i>` | n | `:wqall!` (force close) | `nvim/lua/config/diff.lua` |
