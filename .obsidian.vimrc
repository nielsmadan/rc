" Obsidian Vimrc - synced from ~/rc/.obsidian.vimrc
" Plugin: https://github.com/esm7/obsidian-vimrc-support

" Search
set hlsearch
set ignorecase
set smartcase
set incsearch

" Clipboard
set clipboard=unnamed

" Tabs
set tabstop=2

" Escape mappings
imap jj <Esc>
imap Jj <Esc>
imap JJ <Esc>

" Move through wrapped lines
nmap j gj
nmap k gk
vmap j gj
vmap k gk

" Clear search highlighting
nmap ,<space> :noh

" Scroll faster
nmap <C-e> 3<C-e>
nmap <C-y> 3<C-y>

" Quick Switcher (mirrors <C-G> fzf mapping from .vimrc)
exmap quickswitcher obcommand switcher:open
nmap <C-g> :quickswitcher<CR>
