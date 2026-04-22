# Vim (`.vimrc`) custom keybindings

Leader is `,`. All bindings live in `.vimrc`.

## Mode switching & misc

| Key | Mode | Action |
|---|---|---|
| `jj` / `Jj` / `JJ` | i | Exit to normal mode (`<C-c>`) |
| `:W` | c | Abbreviates to `:w` |
| `<leader><space>` | n | Clear search highlight (`:noh`) |

## Navigation

| Key | Mode | Action |
|---|---|---|
| `j` | n/v | `gj` (move through wrapped lines) |
| `k` | n/v | `gk` |
| `<C-h>` | n | Switch to left window |
| `<C-j>` | n | Switch to below window |
| `<C-k>` | n | Switch to above window |
| `<C-l>` | n | Switch to right window |
| `<C-=>` | n | Equalize window sizes (`<C-w>=`) |
| `<C-e>` | n | Scroll 3 lines down |
| `<C-y>` | n | Scroll 3 lines up |

## Clipboard

| Key | Mode | Action |
|---|---|---|
| `<leader>y` | n/v | Yank to system clipboard (`"+y`) |
| `<leader>p` | n/v | Paste from system clipboard (`"+p`) |

## Search / Replace

| Key | Mode | Action |
|---|---|---|
| `<leader>s` | n | Search-replace word under cursor |

## Files

| Key | Mode | Action |
|---|---|---|
| `<leader>n` | n | Start new file in current file's dir |
| `<leader>~` | n | Open `~/.vimrc` |

## Font / UI

| Key | Mode | Action |
|---|---|---|
| `<Leader>fu` | n (map) | Set guifont to Monaco:h16 |
| `<Leader>fd` | n (map) | Set guifont to Monaco:h12 |

## fzf

| Key | Mode | Action |
|---|---|---|
| `<C-G>` | n | `:Files` |
| `<C-T>` | n | `:Rg` |
| `<leader>t` | n | `:Rg <word-under-cursor>` |

## Project-wide checks & quickfix

| Key / Command | Mode | Action |
|---|---|---|
| `:TSCheck` | c | `:Dispatch tsc --noEmit` → quickfix |
| `:Lint` | c | `:Dispatch biome check .` → quickfix |
| `:Knip` | c | `:Dispatch npx knip --reporter compact` → quickfix |
| `]q` | n | Next quickfix entry (`:cnext`) |
| `[q` | n | Previous quickfix entry (`:cprev`) |
| `]Q` | n | Last quickfix entry (`:clast`) |
| `[Q` | n | First quickfix entry (`:cfirst`) |
| `<leader>q` | n | Open quickfix window (`:botright copen`) |
| `<leader>Q` | n | Close quickfix window (`:cclose`) |

## CoC — completion (insert mode)

| Key | Mode | Action |
|---|---|---|
| `<TAB>` | i | Confirm / expand snippet / refresh |
| `<C-j>` | i | Next item in popup / literal `<C-j>` |
| `<C-k>` | i | Previous item in popup / literal `<C-k>` |
| `<CR>` | i | Confirm completion or `on_enter` |
| `<c-space>` / `<c-@>` | i | Trigger completion |
| `<C-l>` | i | Expand snippet |
| `<C-j>` | i | Expand-or-jump snippet |
| `<C-j>` | v | Select placeholder |
| `<C-f>` | i/n/v | Scroll float popup down (fallback: move) |
| `<C-b>` | i/n/v | Scroll float popup up (fallback: move) |

## CoC — navigation (normal mode)

| Key | Mode | Action |
|---|---|---|
| `K` | n | Show documentation (hover) |
| `[g` | n | Previous diagnostic |
| `]g` | n | Next diagnostic |
| `gd` | n | Goto definition |
| `gy` | n | Goto type definition |
| `gi` | n | Goto implementation |
| `gr` | n | Goto references |
| `<C-s>` | n/x | Range select |

## CoC — actions

| Key | Mode | Action |
|---|---|---|
| `<leader>rn` | n | Rename symbol |
| `<leader>f` | n/x | Format selected (overridden by ALE map in normal mode — see below) |
| `<leader>qf` | n | Fix current problem |
| `<leader>cl` | n | Code lens action |
| `<leader>x` | x | Convert visual selection to snippet |

## CoC — text objects

| Key | Mode | Action |
|---|---|---|
| `if` | x/o | Inner function |
| `af` | x/o | Around function |
| `ic` | x/o | Inner class |
| `ac` | x/o | Around class |

## CoC — lists (space-prefixed)

Note: `<space>` is literal space, not leader.

| Key | Mode | Action |
|---|---|---|
| `<space>a` | n | Diagnostics list |
| `<space>e` | n | Extensions |
| `<space>c` | n | Commands |
| `<space>o` | n | Document outline |
| `<space>s` | n | Workspace symbols |
| `<space>j` | n | CoC next |
| `<space>k` | n | CoC previous |
| `<space>p` | n | Resume last CoC list |

## ALE

| Key | Mode | Action |
|---|---|---|
| `<leader>f` | n | Toggle `ale_fix_on_save` (overrides CoC's `<leader>f` in normal mode) |

## Goyo

| Key | Mode | Action |
|---|---|---|
| `<leader><leader>g` | n | `:Goyo` |

## Diff mode (when `&diff`)

| Key | Mode | Action |
|---|---|---|
| `<Down>` | n | Next hunk (`]c`) |
| `<Up>` | n | Previous hunk (`[c`) |
| `<Left>` | n | Pull hunk (`do`) |
| `<Right>` | n | Push hunk (`dp`) |
| `<M-r>` | n | `:diffupdate` |
| `<M-d>` | n | Next hunk |
| `<M-u>` | n | Previous hunk |
| `<M-1>` | n | `:diffget 1` |
| `<M-2>` | n | `:diffget 2` |
| `<M-3>` | n | `:diffget 3` |
| `<M-g>` | n | `:diffget` |
| `<M-p>1` | n | `:diffput 1` |
| `<M-p>2` | n | `:diffput 2` |
| `<M-p>3` | n | `:diffput 3` |
| `<M-p><M-p>` | n | `:diffput` |
| `<leader><C-i>` | n | `:wqall!` (force close readonly difftool) |

## Syntax debugging

| Key | Mode | Action |
|---|---|---|
| `<leader><C-p>` | n | Print syntax stack under cursor |
| `<leader><C-t>` | n | Print highlight/trans/link groups under cursor |
