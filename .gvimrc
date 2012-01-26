"set font
if has("gui_running")
  if has("gui_gtk2")
    set guifont=Inconsolata\ 10
  elseif has("gui_win32")
    set guifont=Consolas:h12:cANSI
  endif
endif

"file type
filetype plugin indent on

"file numbers
set nu

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

"Shortcut to reload .gvimc
nmap <S-F12> :so $HOME/.gvimrc<CR>
nmap <F12> :e $HOME/.gvimrc<CR>

map cs <Esc>:call ClearSearch()

function! ClearSearch()
let @/ = ""
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

if (bufnr("%") == to_del_buf_nr)
    new
endif
exe "bd".to_del_buf_nr
endfunction

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
