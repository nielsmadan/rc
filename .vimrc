"--->VUNDLE
    set nocompatible

    filetype off
    
    if has('win32') || has('win64')
        set rtp+=$HOME/vimfiles/bundle/vundle/
        call vundle#rc('$HOME/vimfiles/bundle/')
    else
        set rtp+=~/.vim/bundle/vundle/
        call vundle#rc()

        "run shell in interactive mode to get aliases
        set shellcmdflag=-ic
    endif

    Bundle 'gmarik/vundle'

"------->GENERAL PLUGINS
        Bundle 'tpope/vim-surround'
        Bundle 'repeat.vim'
        Bundle 'tomtom/tcomment_vim'
        Bundle 'kien/ctrlp.vim'
        " Bundle 'YankRing.vim'
        Bundle 'yankstack'
        " Bundle 'sjl/gundo.vim'

        " this is just a mirror
        " Bundle 'rson/vim-conque'
        "Bundle 'joonty/vim-sauce.git'
        Bundle 'xolox/vim-shell'

        " easytags does not like diff
        if ! &diff
            Bundle 'xolox/vim-easytags'
        endif

        Bundle 'Lokaltog/vim-easymotion'
        Bundle 'ervandew/supertab'
        "Bundle 'AutoTag' " remove dangling tags on closing vim (test with easytags)
        "Bundle 'DirDiff.vim'

"------->FRAMEWORKS
        Bundle 'scrooloose/syntastic'
        "Bundle 'Shougo/neocomplcache'

"------->LANGUAGE SPECIFIC
        "Bundle 'slimv'
        Bundle 'VimClojure'

        " latest version of built-in omnicomplete
        Bundle 'pythoncomplete'

        " improved syntax highlighting
        Bundle 'python.vim'

        "Bundle 'pydoc.vim'

        " python tab completion for built ins
        " Bundle 'Pydiction'
        "configure pydiction
        " if has('win32') || has('win64')
        "     let g:pydiction_location = '$HOME/.tmp/complete-dict'
        " else
        "     let g:pydiction_location = '~/.tmp/complete-dict'
        " endif

        " vim-scripts repos
        "Bundle 'taglist.vim'
        "Bundle 'git://git.wincent.com/command-t.git'

"--->PATHOGEN
    call pathogen#infect('pathogen')

"--->OPTIONS
    filetype plugin indent on
    syntax on

    "show line numbers, show command, show mode, always show status line
    set number
    set showcmd
    set showmode
    set laststatus=2
    set lazyredraw "don't redraw while executing macros

    "do not create backup files
    set nobackup
    set noswapfile
    "set undofile

    "backspace over line breaks
    set backspace=indent,eol,start

    "file options
    set autowrite
    set autoread

    "text wrapping
    set wrap
    set textwidth=119
    set formatoptions=tcqn1
    " set colorcolumn=120
    set linebreak

    "indent options
    set tabstop=4
    set expandtab
    set shiftwidth=4
    set softtabstop=4

    "folding options
    set foldmethod=indent
    set foldminlines=2
    set foldlevelstart=20

    "search options
    set hlsearch
    set ignorecase
    set smartcase
    set incsearch
    set scrolloff=5 "show lines above/below search result

    "command line completion
    set wildmenu
    set wildmode=list:longest,full

    "show menu and preview for completion
    set completeopt=menu,preview

"--->MAPPINGS
    let mapleader = ","

    "Clear search highlighting
    nnoremap <leader><space> :noh<CR>

    "Folding shortcuts
    nnoremap z1 :set foldlevel=1<CR>
    nnoremap z2 :set foldlevel=2<CR>

    "run external nose command
    nnoremap <m-t> :!nose<CR>

    "Switch mode options
    imap ` <C-c>
    inoremap jj <C-c>

    "Switch windows
    nnoremap <C-h> <C-w>h
    nnoremap <C-j> <C-w>j
    nnoremap <C-k> <C-w>k
    nnoremap <C-l> <C-w>l

    "reload vimrc
    nnoremap <F12> :so $MYVIMRC<CR>

    "copy/paste to system clipboard
    vnoremap <Leader><m-c> "+y
    nnoremap <Leader><m-c> "+y
    vnoremap <Leader><m-v> "+p
    nnoremap <Leader><m-v> "+p

    "Search/Replace word under cursor
    nnoremap <Leader>s :%s/<C-r><C-w>//gc<Left><Left><Left>
    nnoremap <Leader><c-s> :bufdo %s/<C-r><C-w>//gc \| update<s-left><s-left><left><left><left><left>

    au FileType python setl tags+=~/.tmp/python

    "Execute selection or execute file for python
    au FileType python noremap <m-e> :w !python<CR>

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

"--->COLORSCHEME
    "colorscheme Wombat
    colorscheme molokai

    "let moria_style = 'white' " possible moria styles: dark, black, white, light
    "let moria_monochrome = 1 " monochrome status line, Pmenu, line nr 
    "let moria_fontface = 'mixed' " bold statement, type in 'black' and 'dark'
    "colorscheme moria

"--->PLUGIN CONFIGURATION

    "configure easytags
    if ! &diff
        set tags+=tags
        set tags+=./tags
        set tags+=tags;
        let g:easytags_dynamic_files = 1 " add tags to project tag file (if it already exists)
        let g:easytags_by_filetype = '~/.tmp/' " store tag files by filetype in specified directory
        let g:easytags_updatetime_autodisable = 1 " disable updatetime warning
    endif

    "configure syntastic
    let g:syntastic_check_on_open = 1
    let g:syntastic_mode_map = {'mode': 'active',
                                \ 'active_filetypes': ['python'],
                                \ 'passive_filetypes': ['xml'] }

    "configure supertab
    " let g:SuperTabDefaultCompletionType = "context"
    " let g:SuperTabContextDefaultCompletionType = "<c-p>"
    let g:SuperTabClosePreviewOnPopupClose = 1
    let g:SuperTabRetainCompletionDuration = 'completion'

    "fall back to local completion if omni does not return anything
    autocmd FileType *
    \ if &omnifunc != '' |
    \   call SuperTabChain(&omnifunc, "<c-p>") |
    \   call SuperTabSetDefaultCompletionType("<c-x><c-u>") |
    \ endif

    "configure conque
    " let g:ConqueTerm_EscKey = '<C-c>'
    " let g:ConqueTerm_CWInsert = 1
    " let g:ConqueTerm_ExecFileKey = '<F5>'

    "configure ctrl-p
    let g:ctrlp_map = '<c-p><c-f>'
    nmap <c-p><c-b> :CtrlPBuffer<CR>
    nmap <c-p><c-a> :CtrlPMixed<CR>

    "configure yank ring
    " nnoremap <silent> <F3> :YRShow<cr>
    " inoremap <silent> <F3> <ESC>:YRShow<cr>
    " let g:yankring_manage_numbered_reg = 1
    " let g:yankring_zap_keys = 'f F t T / ?'

"--->SMALL FUNCTIONS
    map <Leader>xml <Esc>:call FixupXml()

    function! FixupXml()
    %s/></>\r</g
    normal! gg=G
    endfunction

    nnoremap <leader>w :w<CR>
    map <Leader>qw <Esc>:call CleanClose(1)
    map <Leader>q <Esc>:call CleanClose(0)

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

"--->LOAD .EXTVIMRC

" load .extvimrc (from same directory as .vimrc) and source all files
" specified in there (expected to also be in the same directory)
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

try:
    ext_rc_list_file = open(os.path.join(home_dir, ".extvimrc"))
    ext_rc_list = ext_rc_list_file.readlines()

    for line in ext_rc_list:
            vim.command("call SourceFile(\"%s\")" % line.rstrip())
except IOError as e:
    pass
endpython
