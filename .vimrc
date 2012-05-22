set nocompatible

filetype off

if has('win32') || has('win64')
    set rtp+=$HOME/vimfiles/bundle/vundle/
    call vundle#rc('$HOME/vimfiles/bundle/')
    set tags+=$HOME/.tmp/
else
    set rtp+=~/.vim/bundle/vundle/
    call vundle#rc()
endif


" let Vundle manage Vundle
" required! 
Bundle 'gmarik/vundle'

" small utilities
Bundle 'tpope/vim-surround'
Bundle 'repeat.vim'
Bundle 'tomtom/tcomment_vim'
Bundle 'kien/ctrlp.vim'

if ! &diff
    Bundle 'xolox/vim-shell'
    Bundle 'xolox/vim-easytags'
endif

Bundle 'Lokaltog/vim-easymotion'
"Bundle 'DirDiff.vim'

" frameworks
Bundle 'scrooloose/syntastic'

" language specific
"Bundle 'slimv'
"Bundle 'VimClojure'
Bundle 'pythoncomplete'
"Bundle 'python.vim'
"Bundle 'pydoc.vim'
"Bundle 'Pydiction'

" vim-scripts repos
"Bundle 'taglist.vim'
"Bundle 'git://git.wincent.com/command-t.git'

call pathogen#infect('pathogen')

let mapleader = ","

filetype plugin indent on
syntax on
set nu
set showcmd

set nobackup

"always show the status line, (default only shows it when there are two or
"more windows.
set laststatus=2

"backspace over line breaks
set backspace=2

"file options
set autowrite
set autoread

"vimdiff options
if &diff
    "quick arrow nav, left pull, right push (regardless of side)
    nnoremap <down> ]c
    nnoremap <up> [c
    nnoremap <left> do
    nnoremap <right> dp

    nnoremap <m-r> :diffupdate<CR>
    nnoremap <m-d> ]c
    nnoremap <m-u> [c

    nnoremap <m-g>1 :diffget 1<CR>
    nnoremap <m-g>2 :diffget 2<CR>
    nnoremap <m-g>3 :diffget 3<CR>
    nnoremap <m-g><m-g> :diffget<CR>

    nnoremap <m-p>1 :diffput 1<CR>
    nnoremap <m-p>2 :diffput 2<CR>
    nnoremap <m-p>3 :diffput 3<CR>
    nnoremap <m-p><m-p> :diffput<CR>

    nnoremap <m-q> :wqall<CR>
endif

"indent options
set tabstop=4
set expandtab
set shiftwidth=4

"folding options
set foldmethod=indent
set foldminlines=2
set foldlevelstart=20
nnoremap z1 :set foldlevel=1<CR>
nnoremap z2 :set foldlevel=2<CR>

"search options
set hlsearch
set ignorecase
set smartcase
set incsearch

"Switch mode options
imap <Esc> <Nop>
imap ` <C-c>

"emacs bindings for insert mode
inoremap <C-f> <C-c>la
inoremap <C-b> <C-c>i
inoremap <C-x><C-s> <C-c>:w<CR>a

nnoremap <Leader>s :%s/\<<C-r><C-w>\>//gc<Left><Left><Left>

"Shortcut to reload .gvimc
nmap <S-F12> :so $HOME/.gvimrc<CR>:so $HOME/.vimrc<CR>
nmap <F12> :e $HOME/.gvimrc<CR>:sp<CR>:e $HOME/.vimrc<CR>

"Close scratch buffer after omni complete
autocmd CursorMovedI * if pumvisible() == 0|pclose|endif
autocmd InsertLeave * if pumvisible() == 0|pclose|endif


" ******* COLORSCHEME CONFIGURATION *******

"colorscheme Wombat
colorscheme molokai

"let moria_style = 'white' " possible moria styles: dark, black, white, light
"let moria_monochrome = 1 " monochrome status line, Pmenu, line nr 
"let moria_fontface = 'mixed' " bold statement, type in 'black' and 'dark'
"colorscheme moria

"colo vividchalk

" ******* PLUGIN CONFIGURATION *******

"configure easytags

if ! &diff
    set tags=./tags
    let g:easytags_dynamic_files = 1 " add tags to project tag file (if it already exists)
    let g:easytags_by_filetype = '~/.tmp/' " store tag files by filetype in specified directory
endif

"configure syntastic
let g:syntastic_mode_map = {'mode': 'active',
                            \ 'active_filetypes': ['python'],
                            \ 'passive_filetypes': [] }
let g:syntastic_check_on_open=1

"configure conque
let g:ConqueTerm_EscKey = '<C-c>'
let g:ConqueTerm_CWInsert = 1
let g:ConqueTerm_ExecFileKey = '<F5>'

"configure ctrl-p
let g:ctrlp_map = '<c-p><c-f>'
nmap <c-p><c-b> :CtrlPBuffer<CR>
nmap <c-p><c-a> :CtrlPMixed<CR>

"if has('win32') || has('win64')
    "let g:pydiction_location = '$HOME/vimfiles/bundle/Pydiction/complete-dict'
"else
    "let g:pydiction_location = '$HOME/.vim/bundle/Pydiction/complete-dict'
"endif

" ******* small function *******

map <Leader>clr<CR> <Esc>:call ClearSearch()<CR>

function! ClearSearch()
let @/ = ""
endfunction

map <Leader>xml<CR> <Esc>:call FixupXml()

function! FixupXml()
%s/></>\r</g
normal! gg=G
endfunction

map <Leader>wq<CR> <Esc>:call CleanClose(1)<CR>
map <Leader>q<CR> <Esc>:call CleanClose(0)<CR>

function! CleanClose(tosave)
if (a:tosave == 1)
    w!
endif
let to_del_buf_nr = bufnr("%")
let new_buf_nr = bufnr("#")
if ((new_buf_nr != -1) && (new_buf_nr != to_del_buf_nr) && buflisted(new_buf_nr))
    exe "b".new_buf_nr
else
    bnext
endif
endfunction

" ******* .extvimrc loading *******

" load .extvimrc (from same directory as .vimrc) and source all files
" specified in there (expected to also be in the same directory.
function! SourceFile(file_name)
python << endpython
import vim
import os

home_dir = vim.eval("$HOME")
file_name = vim.eval("a:file_name")

abs_path = os.path.join(home_dir, file_name)

try:
    open(abs_path)
    vim.command("so " + abs_path)

except IOError as e:
    print "Did not find %s." % abs_path

endpython
endfunction

python << endpython
import os
import vim

home_dir = vim.eval("$HOME")

ext_rc_list_file = open(os.path.join(home_dir, ".extvimrc"))
ext_rc_list = ext_rc_list_file.readlines()

for line in ext_rc_list:
    vim.command("call SourceFile(\"%s\")" % line.rstrip())
endpython
