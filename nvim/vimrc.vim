"status line options
set statusline=
set statusline+=\|\ %f\ \|
set statusline+=%h%m%r%w
set statusline+=%=
set statusline+=C:%c/%{col(\"$\")-1}\
set statusline+=L:%l/%L\
set statusline+=%y
set guifont=Monaco:h12

"--->MAPPINGS
let mapleader = ","

map <Leader>fu <Esc>:set guifont=Monaco:h16<CR>
map <Leader>fd <Esc>:set guifont=Monaco:h12<CR>

"use :W to write file.
cnoreabbrev <expr> W ((getcmdtype() is# ':' && getcmdline() is# 'W')?('w'):('W'))

"Clear search highlighting
nnoremap <leader><space> :noh<CR>

"Switch mode options
inoremap jj <C-c>
inoremap Jj <C-c>
inoremap JJ <C-c>

"move through wrapped lines
nnoremap j gj
nnoremap k gk
vnoremap j gj
vnoremap k gk

"Switch windows
nnoremap <C-h> <C-w>h
nnoremap <C-j> <C-w>j
nnoremap <C-k> <C-w>k
nnoremap <C-l> <C-w>l
nnoremap <C-=> <C-w>=

"copy/paste to system clipboard
vnoremap <leader>y "+y
nnoremap <leader>y "+y
vnoremap <leader>p "+p
nnoremap <leader>p "+p

"Search/Replace word under cursor
nnoremap <leader>s :%s/<C-r><C-w>//gc<Left><Left><Left>

"Set spell checking for commit logs
au filetype svn,*commit*,rst setlocal spell

colo harlequin
