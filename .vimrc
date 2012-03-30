set nocompatible

filetype off

if has('win32') || has('win64')
    set rtp+=$HOME/vimfiles/bundle/vundle/
    call vundle#rc('$HOME/vimfiles/bundle/')
    set tags+=$HOME/tags/tags
else
    set rtp+=~/.vim/bundle/vundle/
    call vundle#rc()
endif


" let Vundle manage Vundle
" required! 
Bundle 'gmarik/vundle'

" My Bundles here:
"
" original repos on github
Bundle 'scrooloose/syntastic'
"Bundle 'xolox/vim-shell'
"Bundle 'xolox/vim-easytags'
"Bundle 'Lokaltog/vim-easymotion'
"Bundle 'rstacruz/sparkup', {'rtp': 'vim/'}
"Bundle 'tpope/vim-rails.git'
" vim-scripts repos
"Bundle 'taglist.vim'
"Bundle 'python.vim'
"Bundle 'pydoc.vim'
Bundle 'pythoncomplete'
"Bundle 'Pydiction'
"Bundle 'L9'
"Bundle 'FuzzyFinder'
" non github repos
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

"indent options
set tabstop=4
set expandtab
set shiftwidth=4

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
nmap <S-F12> :so $HOME/.gvimrc<CR>:so $HOME/.vimrc
nmap <F12> :e $HOME/.gvimrc<CR>:sp<CR>:e $HOME/.vimrc

"Close scratch buffer after omni complete
autocmd CursorMovedI * if pumvisible() == 0|pclose|endif
autocmd InsertLeave * if pumvisible() == 0|pclose|endif

" ******* PLUGIN CONFIGURATION *******

"configure syntastic
let g:syntastic_mode_map = {'mode': 'active',
                            \ 'active_filetypes': ['python'],
                            \ 'passive_filetypes': [] }
let g:syntastic_check_on_open=1

"configure conque
let g:ConqueTerm_EscKey = '<C-c>'
let g:ConqueTerm_CWInsert = 1
let g:ConqueTerm_ExecFileKey = '<F5>'

"if has('win32') || has('win64')
    "let g:pydiction_location = '$HOME/vimfiles/bundle/Pydiction/complete-dict'
"else
    "let g:pydiction_location = '$HOME/.vim/bundle/Pydiction/complete-dict'
"endif

" ******* small function *******

map clr <Esc>:call ClearSearch()

function! ClearSearch()
let @/ = ""
endfunction

map clx <Esc>:call FixupXml()

function! FixupXml()
%s/></>\r</g
normal! gg=G
endfunction

map fc <Esc>:call CleanClose(1)
map fq <Esc>:call CleanClose(0)

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
