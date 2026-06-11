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

let s:FontSize = 12
map <Leader>fu :call IncreaseFontSize()<CR>
map <Leader>fd :call DecreaseFontSize()<CR>
map <Leader>f1 :call SetFontSize(12)<CR>
map <Leader>f2 :call SetFontSize(18)<CR>

" guifont takes effect in Neovide; it is a no-op in terminal Neovim.
function! SetFontSize(size)
  let s:FontSize = a:size
  exe "set guifont=Monaco:h" . s:FontSize
endfunction

function! IncreaseFontSize()
  call SetFontSize(s:FontSize + 1)
endfunction

function! DecreaseFontSize()
  call SetFontSize(s:FontSize - 1)
endfunction

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
