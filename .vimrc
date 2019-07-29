call plug#begin("~/.vim/plugged")

"--->GENERAL PLUGINS
Plug 'tpope/vim-rsi'
Plug 'tpope/vim-fugitive'
Plug 'tpope/vim-repeat'
Plug 'tpope/vim-surround'
Plug 'tpope/vim-commentary'

Plug 'kien/ctrlp.vim'
Plug 'Chiel92/vim-autoformat'

Plug 'vim-scripts/hexHighlight.vim'
Plug 'vim-scripts/matchit.zip'

Plug 'xolox/vim-misc'

Plug 'Lokaltog/vim-easymotion'

Plug 'junegunn/goyo.vim'
Plug '/usr/local/opt/fzf'
Plug 'junegunn/fzf.vim'

"--->FRAMEWORKS
" Plug 'scrooloose/syntastic'
Plug 'w0rp/ale'
Plug 'Valloric/YouCompleteMe', { 'do': './install.py --clang-completer --ts-completer' }

"--->LANGUAGE SPECIFIC
Plug 'peterhoeg/vim-qml'

Plug 'pangloss/vim-javascript'
Plug 'mxw/vim-jsx'

Plug 'leafgarland/typescript-vim'
Plug 'ianks/vim-tsx'

Plug 'jparise/vim-graphql'

"--->MINE can't do it with git+ssh. :(
Plug 'nielsmadan/harlequin'

call plug#end()

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
  au FileType * setlocal formatoptions-=r
  au FileType * setlocal formatoptions-=o
augroup end

"indent options
set tabstop=2
set expandtab
set shiftwidth=2
set softtabstop=2

au BufRead,BufNewFile *.js,*.json,*.tsx,*.ts,*.yaml,Jenkinsfile setlocal shiftwidth=2 tabstop=2 softtabstop=2

au BufNewFile,BufRead Jenkinsfile setf groovy
au BufNewFile,BufRead *.prisma setf graphql

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
set completeopt=menu

"allow increment for characters
set nrformats=octal,hex,alpha

"status line options
set statusline=
set statusline+=\|\ %f\ \|
set statusline+=%h%m%r%w
set statusline+=%=
set statusline+=C:%c/%{col(\"$\")-1}\
set statusline+=L:%l/%L\
set statusline+=%y

"--->MAPPINGS
let mapleader = ","

"use :W to write file.
cnoreabbrev <expr> W ((getcmdtype() is# ':' && getcmdline() is# 'W')?('w'):('W'))

"Clear search highlighting
nnoremap <leader><space> :noh<CR>

"Folding shortcuts
nnoremap <leader>1 :set foldlevel=1<CR>
nnoremap <leader>2 :set foldlevel=2<CR>
nnoremap <leader>3 :set foldlevel=3<CR>

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

"scroll faster with c-e and c-y
nnoremap <C-e> 3<c-e>
nnoremap <C-y> 3<c-y>

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

fun! <SID>StripTrailingWhitespaces()
  let l = line(".")
  let c = col(".")
  %s/\s\+$//e
  call cursor(l, c)
endfun

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
  nnoremap <c-i> :wqall!<CR>

  "looks like on mac there's some weird window resizing going on at the start when diffing.
  au VimResized * wincmd =
endif

"--->COLORSCHEME
let &t_Co = 256
colo harlequin

"--->PLUGIN CONFIGURATION
"YouCompleteMe
let g:ycm_filter_diagnostics = {
      \ "javascript": {
      \      "regex": [ "ts file", "expected" ],
      \    }
      \ }

nnoremap <leader>gr :YcmCompleter GoToReferences<CR>
nnoremap <leader>gd :YcmCompleter GoToDefinition<CR>
nnoremap <leader>gt :YcmCompleter GetType<CR>


" Flow linting
let g:ale_linters = {'javascript': ['eslint', 'flow']}
let g:ale_linters_ignore = {'javascript': ['tsserver']}

" Typescript linting
" let g:ale_linters = {'javascript': ['eslint', 'tsserver']}
" let g:ale_linters_ignore = {'javascript': ['flow']}

" configure vim-jsx to highlight in .js files (not just .jsx)
let g:jsx_ext_required = 0

" configure flow highlighting
let g:javascript_plugin_flow = 1

" configure autoformat
nnoremap <leader>a :Autoformat<CR>
au BufWrite * :Autoformat
au FileType yaml let b:autoformat_autoindent=0

"configure ctrl-p
let g:ctrlp_map = '<c-g>' " start up the plugin
let g:ctrlp_working_path_mode = '' " start file search from current root
let g:ctrlp_switch_buffer = 0 " don't jump to a selected buffer if it's open

let g:ctrlp_prompt_mappings = {
      \ 'ToggleType(1)':        ['<c-h>'],
      \ 'ToggleType(-1)':       ['<c-l>'],
      \ 'PrtCurLeft()':         ['<left>', '<c-^>'],
      \ 'PrtCurRight()':        ['<right>'],
      \ }

if executable('ag')
  " Use The Silver Searcher https://github.com/ggreer/the_silver_searcher
  set grepprg=ag\ --nogroup\ --nocolor
  " Use ag in CtrlP for listing files. Lightning fast, respects .gitignore
  " and .agignore. Ignores hidden files by default.
  let g:ctrlp_user_command = 'ag %s -l --nocolor -f -g ""'
else
  "ctrl+p ignore files in .gitignore
  let g:ctrlp_user_command = ['.git', 'cd %s && git ls-files . -co --exclude-standard', 'find %s -type f']
endif

map <Leader>+ :call WriteMode()<CR>
let g:write_mode = 0

function! WriteMode()
  if (g:write_mode == 0)
    if has("gui_running")
      if has("gui_macvim")
        let s:FontSize = 24
        exe "set guifont=Inconsolata:h" . s:FontSize
      endif
    endif

    setlocal spell spelllang=en_us
    colo geisha

    exe "Goyo 40%x60%"

    g:write_mode = 1
  elseif
    if has("gui_running")
      if has("gui_macvim")
        let s:FontSize = 28
        exe "set guifont=Inconsolata:h" . s:FontSize
      endif
    endif

    colo harlequin
    setlocal nospell

    exe "Goyo!"

    g:write_mode = 0
  endif
endfunction

"--->SMALL FUNCTIONS
map <Leader>xml <Esc>:call FixupXml()

function! FixupXml()
  %s/></>\r</g
  normal! gg=G
endfunction

map <Leader>qw <Esc>:call CleanClose(1)<CR>
map <Leader>qq <Esc>:call CleanClose(0)<CR>

map <Leader>i <Esc>:set guifont=Inconsolata:h10<CR>

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

nnoremap <leader><c-b> :set guifont=Inconsolata:h20

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
