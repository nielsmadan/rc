"--->VUNDLE
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

"--->GENERAL PLUGINS
        Bundle 'tpope/vim-surround'
        Bundle 'tpope/vim-rsi'
        Bundle 'repeat.vim'

        Bundle 'tomtom/tcomment_vim'
        Bundle 'kien/ctrlp.vim'
        Bundle 'fholgado/minibufexpl.vim'
        Bundle 'mileszs/ack.vim'

        Bundle 'yankstack'
        Bundle 'hexHighlight.vim'
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

"--->FRAMEWORKS
        Bundle 'scrooloose/syntastic'
        "Bundle 'Shougo/neocomplcache'

"--->LANGUAGE SPECIFIC
        "Bundle 'slimv'
        Bundle 'VimClojure'

        Bundle 'derekwyatt/vim-scala'

        Bundle 'tpope/vim-ragtag'
        Bundle 'matchit.zip'

        " latest version of built-in omnicomplete
        Bundle 'pythoncomplete'
        " improved syntax highlighting
        Bundle 'python.vim'
        "Bundle 'pydoc.vim'

        Bundle 'Jinja'
        Bundle 'peterhoeg/vim-qml'

"--->MINE can't do it with git+ssh. :(
        " Bundle 'git+ssh://git@github.com/nielsmadan/harlequin'
        " Bundle 'git+ssh://git@github.com/nielsmadan/venom'
        " Bundle 'git+ssh://git@github.com/nielsmadan/mercury'

"--->PATHOGEN
    call pathogen#infect('pathogen')

"--->OPTIONS
    filetype plugin indent on
    syntax on

    "show line numbers, show command, show mode, always show status line
    set number
    set showcmd
    set showmode
    set mousehide "hide mouse while typing
    set laststatus=2
    set lazyredraw "don't redraw while executing macros
    set more "active pager
    set shortmess+=I "no intro
    set display=lastline "show as much of last line as possible if it doesn't fit.
    set helpheight=0 "no min window height for help window.

    "do not create backup files
    set nobackup
    set noswapfile
    set undodir=~/.tmp/undofiles
    set undofile

    "backspace over line breaks
    set backspace=indent,eol,start

    "easily toggle paste
    set pastetoggle=<f10>

    "file options
    set autowrite
    set autoread

    "text wrapping
    set wrap
    set textwidth=119
    set formatoptions=cqn1
    set linebreak

    "override any ftplugin that thinks it's a good idea to redefine
    "the formatoptions that were explicitly set in .vimrc. >:|
    augroup reset_fo
        au!
        au FileType * setlocal formatoptions-=o
    augroup end

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

    "scrolloffs
    set scrolloff=5
    set sidescrolloff=7

    "command line completion
    set wildmenu
    set wildmode=list:longest,full

    "show menu and preview for completion
    set completeopt=menu,preview

    "status line options
    set statusline=
    set statusline+=\|\ %f\ \|\ 
    set statusline+=%h%m%r%w
    set statusline+=%=
    set statusline+=C:%c/%{col(\"$\")-1}\ 
    set statusline+=L:%l/%L\ 
    set statusline+=%y

"--->MAPPINGS
    let mapleader = ","
    cnoreabbrev <expr> W ((getcmdtype() is# ':' && getcmdline() is# 'W')?('w'):('W'))

    "Clear search highlighting
    nnoremap <leader><space> :noh<CR>

    "Folding shortcuts
    nnoremap z1 :set foldlevel=1<CR>
    nnoremap z2 :set foldlevel=2<CR>

    "run external nose command
    nnoremap <m-t> :!nose<CR>

    "Switch mode options
    inoremap jj <C-c>
    inoremap Jj <C-c>
    inoremap JJ <C-c>
    inoremap <C-j> <C-c>

    "move through wrapped lines
    nnoremap j gj
    nnoremap k gk

    "make Y work the same way as C and D (yank to the end of the line)
    nnoremap Y y$

    "Switch windows
    nnoremap <C-h> <C-w>h
    nnoremap <C-j> <C-w>j
    nnoremap <C-k> <C-w>k
    nnoremap <C-l> <C-w>l
    nnoremap <C-=> <C-w>=

    "scroll faster with c-e and c-y
    nnoremap <C-e> 3<c-e>
    nnoremap <C-y> 3<c-y>

    "reload vimrc
    nnoremap <F12> :so $MYVIMRC<CR>

    "copy/paste to system clipboard
    vnoremap <leader>y "+y
    nnoremap <leader>y "+y
    vnoremap <leader>p "+p
    nnoremap <leader>p "+p

    "Search/Replace word under cursor
    nnoremap <Leader>s :%s/<C-r><C-w>//gc<Left><Left><Left>
    nnoremap <Leader><c-s> :bufdo %s/<C-r><C-w>//gc \| update<s-left><s-left><left><left><left><left>

    "Set spell checking for commit logs
    au filetype svn,*commit*,rst setlocal spell

    "Execute selection or execute file for python (overwrite: suspend program)
    "we are writing to a 'file' here, where the file is the python interpreter
    au FileType python noremap <c-z> :w !python<CR>
    au FileType ruby noremap <c-z> :w !ruby<CR>

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

        nnoremap <m-1> :diffget 1<CR>
        nnoremap <m-2> :diffget 2<CR>
        nnoremap <m-3> :diffget 3<CR>
        nnoremap <m-g> :diffget<CR>

        nnoremap <m-p>1 :diffput 1<CR>
        nnoremap <m-p>2 :diffput 2<CR>
        nnoremap <m-p>3 :diffput 3<CR>
        nnoremap <m-p><m-p> :diffput<CR>

        "when using gvimdiff as git difftool, it will open both sides in readonly mode, which is why we need the !
        nnoremap <m-q> :wqall!<CR>
    endif

"--->COLORSCHEME
    let &t_Co = 256
    colo harlequin

"--->PLUGIN CONFIGURATION

    "configure easytags, and tag management in general

    "Add language specific tags folders to search path (generated by easytags)
    au FileType python setl tags+=~/.tmp/python
    au FileType ruby setl tags+=~/.tmp/ruby

    set tags+=tags
    set tags+=./tags
    set tags+=tags;

    if ! &diff
        let g:easytags_dynamic_files = 1 " add tags to project tag file (if it already exists)
        let g:easytags_by_filetype = '~/.tmp/' " store tag files by filetype in specified directory
        let g:easytags_updatetime_autodisable = 1 " disable updatetime warning
    endif

    "configure minibufexplorer
    let g:miniBufExplMapWindowNavArrows=1 " ctrl + arrow = windows movement
    let g:miniBufExplMapCTabSwitchWindows = 1 " ctrl( + shift) + tab = window movement
    let g:miniBufExplUseSingleClick = 1 " click to go to buffer
    let g:miniBufExplorerMoreThanOne = 999
    let g:miniBufExplCheckDupeBufs = 0
    nnoremap <leader>e :TMiniBufExplorer<CR>

    "configure ack.vim
    nnoremap <c-a> :Ack 

    "configure syntastic
    let g:syntastic_check_on_open = 1
    let g:syntastic_mode_map = {'mode': 'active',
                                \ 'active_filetypes': ['python'],
                                \ 'passive_filetypes': ['xml', 'rst'] }
    let g:syntastic_python_checker="flake8"

    "configure supertab
    " let g:SuperTabDefaultCompletionType = "context"
    " let g:SuperTabContextDefaultCompletionType = "<c-p>"
    let g:SuperTabClosePreviewOnPopupClose = 1
    let g:SuperTabRetainCompletionDuration = 'completion'

    "fall back to local completion if omni does not exist for file type
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
    let g:ctrlp_map = '<c-g>' " overwrite: display current file name and position
    let g:ctrlp_working_path_mode = '' " start file search from current root
    let g:ctrlp_switch_buffer = 0 " don't jump to a selected buffer if it's open

    let g:ctrlp_prompt_mappings = {
    \ 'ToggleType(1)':        ['<c-h>'],
    \ 'ToggleType(-1)':       ['<c-l>'],
    \ 'PrtCurLeft()':         ['<left>', '<c-^>'],
    \ 'PrtCurRight()':        ['<right>'],
    \ }
    
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

    "Show syntax highlighting groups for word under cursor
    nnoremap <leader><c-p> :call <SID>SynStack()<CR>
    function! <SID>SynStack()
        if !exists("*synstack")
            return
        endif
        let sgroup_list = map(synstack(line('.'), col('.')), 'synIDattr(v:val, "name")')
        echo sgroup_list
        let @s = join(sgroup_list, ' ')
    endfunc

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

ext_rc_list_file = open(os.path.join(home_dir, ".extvimrc"))
ext_rc_list = ext_rc_list_file.readlines()

for line in ext_rc_list:
    vim.command('call SourceFile("%s")' % line.rstrip())
endpython
