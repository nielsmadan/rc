call plug#begin("~/.vim/plugged")

"--->GENERAL PLUGINS
Plug 'tpope/vim-rsi'
Plug 'tpope/vim-fugitive'
Plug 'tpope/vim-repeat'
Plug 'tpope/vim-surround'
Plug 'tpope/vim-eunuch'
Plug 'tpope/vim-vinegar'
Plug 'tpope/vim-commentary'

Plug 'github/copilot.vim'

Plug 'mileszs/ack.vim'

Plug 'vim-autoformat/vim-autoformat'
Plug 'sbdchd/neoformat'

Plug 'vim-scripts/hexHighlight.vim'
Plug 'vim-scripts/ReplaceWithRegister'

Plug 'andymass/vim-matchup'
Plug 'ap/vim-css-color'

Plug 'xolox/vim-misc'

Plug 'Lokaltog/vim-easymotion'

Plug 'junegunn/fzf', { 'do': { -> fzf#install() } }
Plug 'junegunn/fzf.vim'

Plug 'wellle/context.vim'

"--->FRAMEWORKS
" Plug 'scrooloose/syntastic'
Plug 'dense-analysis/ale'
Plug 'neoclide/coc.nvim', {'branch': 'release'}

"--->LANGUAGE SPECIFIC
Plug 'peterhoeg/vim-qml'

Plug 'pangloss/vim-javascript'
Plug 'mxw/vim-jsx'

Plug 'keith/swift.vim'

Plug 'leafgarland/typescript-vim'
Plug 'ianks/vim-tsx'

Plug 'jparise/vim-graphql'

Plug 'dart-lang/dart-vim-plugin'

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
set shortmess+=Ic "no intro
set display=lastline "show as much of last line as possible if it doesn't fit.
set helpheight=0 "no min window height for help window.
set cmdheight=2 "more space for commands.

"do not create backup files
set nobackup
set noswapfile
set undodir=~/.tmp/vim_undo
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

au BufRead,BufNewFile *.js,*.json,*.tsx,*.ts,*.yaml,*.swift,Jenkinsfile setlocal shiftwidth=2 tabstop=2 softtabstop=2

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

"scroll faster with c-e and c-y
nnoremap <C-e> 3<c-e>
nnoremap <C-y> 3<c-y>

"copy/paste to system clipboard
vnoremap <leader>y "+y
nnoremap <leader>y "+y
vnoremap <leader>p "+p
nnoremap <leader>p "+p

"Search/Replace word under cursor
nnoremap <leader>s :%s/<C-r><C-w>//gc<Left><Left><Left>

" New file
nnoremap <leader>n :e %:h/

" Open .vimrc
nnoremap <leader>~ :e ~/.vimrc<CR>

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
  nnoremap <leader><c-i> :wqall!<CR>

  "looks like on mac there's some weird window resizing going on at the start when diffing.
  au VimResized * wincmd =
endif

"--->COLORSCHEME
let &t_Co = 256
colo harlequin

"--->PLUGIN CONFIGURATION
" Ack
if executable('ag')
  let g:ackprg = 'ag --vimgrep'
endif

cnoreabbrev Ack Ack!
nnoremap <Leader>a :Ack!<Space>

" CoC
" Having longer updatetime (default is 4000 ms = 4 s) leads to noticeable
" delays and poor user experience.
set updatetime=300

" Always show the signcolumn, otherwise it would shift the text each time
" diagnostics appear/become resolved.
set signcolumn=yes

" Use tab for trigger completion with characters ahead and navigate.
" NOTE: There's always complete item selected by default, you may want to enable
" no select by `"suggest.noselect": true` in your configuration file.
" NOTE: Use command ':verbose imap <tab>' to make sure tab is not mapped by
" other plugin before putting this into your config.
inoremap <silent><expr> <TAB>
      \ coc#pum#visible() ? coc#pum#next(1):
      \ exists('b:_copilot.suggestions') ? copilot#Accept("\<CR>") :
      \ coc#expandableOrJumpable() ? "\<C-r>=coc#rpc#request('doKeymap', ['snippets-expand-jump',''])\<CR>" :
      \ CheckBackspace() ? "\<TAB>" :
      \ coc#refresh()
inoremap <expr><S-TAB> coc#pum#visible() ? coc#pum#prev(1) : "\<C-h>"

function! CheckBackspace() abort
  let col = col('.') - 1
  return !col || getline('.')[col - 1]  =~# '\s'
endfunction

let g:coc_snippet_next = '<tab>'

" Make <CR> to accept selected completion item or notify coc.nvim to format
" <C-g>u breaks current undo, please make your own choice.
inoremap <silent><expr> <CR> coc#pum#visible() ? coc#pum#confirm()
      \: "\<C-g>u\<CR>\<c-r>=coc#on_enter()\<CR>"

" Use <c-space> to trigger completion.
if has('nvim')
  inoremap <silent><expr> <c-space> coc#refresh()
else
  inoremap <silent><expr> <c-@> coc#refresh()
endif

" Use `[g` and `]g` to navigate diagnostics
" Use `:CocDiagnostics` to get all diagnostics of current buffer in location list.
nmap <silent> [g <Plug>(coc-diagnostic-prev)
nmap <silent> ]g <Plug>(coc-diagnostic-next)

" GoTo code navigation.
nmap <silent> gd <Plug>(coc-definition)
nmap <silent> gy <Plug>(coc-type-definition)
nmap <silent> gi <Plug>(coc-implementation)
nmap <silent> gr <Plug>(coc-references)

" Use <C-l> for trigger snippet expand.
imap <C-l> <Plug>(coc-snippets-expand)

" Use <C-j> for select text for visual placeholder of snippet.
vmap <C-j> <Plug>(coc-snippets-select)

" Use <C-j> for jump to next placeholder, it's default of coc.nvim
let g:coc_snippet_next = '<c-j>'

" Use <C-k> for jump to previous placeholder, it's default of coc.nvim
let g:coc_snippet_prev = '<c-k>'

" Use <C-j> for both expand and jump (make expand higher priority.)
imap <C-j> <Plug>(coc-snippets-expand-jump)

" Use <leader>x for convert visual selected code to snippet
xmap <leader>x  <Plug>(coc-convert-snippet)

" Use K to show documentation in preview window.
nnoremap <silent> K :call ShowDocumentation()<CR>

function! ShowDocumentation()
  if CocAction('hasProvider', 'hover')
    call CocActionAsync('doHover')
  else
    call feedkeys('K', 'in')
  endif
endfunction

" Highlight the symbol and its references when holding the cursor.
autocmd CursorHold * silent call CocActionAsync('highlight')

" Symbol renaming.
nmap <leader>rn <Plug>(coc-rename)

" Formatting selected code.
xmap <leader>f  <Plug>(coc-format-selected)
nmap <leader>f  <Plug>(coc-format-selected)

" augroup mygroup
"   autocmd!
"   " Setup formatexpr specified filetype(s).
"   autocmd FileType typescript,json setl formatexpr=CocAction('formatSelected')
"   " Update signature help on jump placeholder.
"   autocmd User CocJumpPlaceholder call CocActionAsync('showSignatureHelp')
" augroup end

" Applying codeAction to the selected region.
" Example: `<leader>aap` for current paragraph
" xmap <leader>a  <Plug>(coc-codeaction-selected)
" nmap <leader>a  <Plug>(coc-codeaction-selected)

" Remap keys for applying codeAction to the current buffer.
" nmap <leader>ac  <Plug>(coc-codeaction)
" Apply AutoFix to problem on the current line.
nmap <leader>qf  <Plug>(coc-fix-current)

" Run the Code Lens action on the current line.
nmap <leader>cl  <Plug>(coc-codelens-action)

" Map function and class text objects
" NOTE: Requires 'textDocument.documentSymbol' support from the language server.
xmap if <Plug>(coc-funcobj-i)
omap if <Plug>(coc-funcobj-i)
xmap af <Plug>(coc-funcobj-a)
omap af <Plug>(coc-funcobj-a)
xmap ic <Plug>(coc-classobj-i)
omap ic <Plug>(coc-classobj-i)
xmap ac <Plug>(coc-classobj-a)
omap ac <Plug>(coc-classobj-a)

" Remap <C-f> and <C-b> for scroll float windows/popups.
if has('nvim-0.4.0') || has('patch-8.2.0750')
  nnoremap <silent><nowait><expr> <C-f> coc#float#has_scroll() ? coc#float#scroll(1) : "\<C-f>"
  nnoremap <silent><nowait><expr> <C-b> coc#float#has_scroll() ? coc#float#scroll(0) : "\<C-b>"
  inoremap <silent><nowait><expr> <C-f> coc#float#has_scroll() ? "\<c-r>=coc#float#scroll(1)\<cr>" : "\<Right>"
  inoremap <silent><nowait><expr> <C-b> coc#float#has_scroll() ? "\<c-r>=coc#float#scroll(0)\<cr>" : "\<Left>"
  vnoremap <silent><nowait><expr> <C-f> coc#float#has_scroll() ? coc#float#scroll(1) : "\<C-f>"
  vnoremap <silent><nowait><expr> <C-b> coc#float#has_scroll() ? coc#float#scroll(0) : "\<C-b>"
endif

" Use CTRL-S for selections ranges.
" Requires 'textDocument/selectionRange' support of language server.
nmap <silent> <C-s> <Plug>(coc-range-select)
xmap <silent> <C-s> <Plug>(coc-range-select)

" Add `:Format` command to format current buffer.
command! -nargs=0 Format :call CocActionAsync('format')

" Add `:Fold` command to fold current buffer.
command! -nargs=? Fold :call     CocAction('fold', <f-args>)

" Add `:OR` command for organize imports of the current buffer.
command! -nargs=0 OR   :call     CocActionAsync('runCommand', 'editor.action.organizeImport')

" Add (Neo)Vim's native statusline support.
" NOTE: Please see `:h coc-status` for integrations with external plugins that
" provide custom statusline: lightline.vim, vim-airline.
set statusline^=%{coc#status()}%{get(b:,'coc_current_function','')}

" Mappings for CoCList
" Show all diagnostics.
nnoremap <silent><nowait> <space>a  :<C-u>CocList diagnostics<cr>
" Manage extensions.
nnoremap <silent><nowait> <space>e  :<C-u>CocList extensions<cr>
" Show commands.
nnoremap <silent><nowait> <space>c  :<C-u>CocList commands<cr>
" Find symbol of current document.
nnoremap <silent><nowait> <space>o  :<C-u>CocList outline<cr>
" Search workspace symbols.
nnoremap <silent><nowait> <space>s  :<C-u>CocList -I symbols<cr>
" Do default action for next item.
nnoremap <silent><nowait> <space>j  :<C-u>CocNext<CR>
" Do default action for previous item.
nnoremap <silent><nowait> <space>k  :<C-u>CocPrev<CR>
" Resume latest coc list.
nnoremap <silent><nowait> <space>p  :<C-u>CocListResume<CR>


" Typescript linting
let g:ale_linters = {'javascript': ['eslint_d', 'tsserver']}
let g:ale_linters_ignore = {'javascript': ['flow']}
let g:ale_fixers = {
      \ 'typescript.tsx': ['prettierd'],
      \ 'typescript': ['prettierd'],
      \ 'javascript': ['prettierd'],
      \}

let g:ale_python_pylint_options = '--rcfile ./pylintrc'

" configure vim-jsx to highlight in .js files (not just .jsx)
let g:jsx_ext_required = 0

" configure flow highlighting
let g:javascript_plugin_flow = 1

" configure autoformat
let g:autoformat_verbosemode=2

au FileType yaml let b:autoformat_autoindent=0

function! ToggleFormatOnWrite()
  if !exists('g:FormatOnWriteMarker')
    let g:FormatOnWriteMarker = 1
  endif

  " Enable if the group was previously disabled
  if (g:FormatOnWriteMarker == 1)
    let g:FormatOnWriteMarker = 0

    " actual augroup
    augroup format_on_write
      autocmd!
      au BufWrite * :Neoformat
    augroup END
  else    " Clear the group if it was previously enabled
    let g:FormatOnWriteMarker = 1

    " resetting the augroup
    augroup format_on_write
      autocmd!
    augroup END
  endif
endfunction

nnoremap <leader>f :call ToggleFormatOnWrite()<CR>

"configure fzf
set rtp+=/opt/homebrew/opt/fzf
nnoremap <C-G> :Files<CR>

"configure copilot
let g:copilot_enabled = 0

nnoremap <leader>cpe :Copilot enable<CR>
nnoremap <leader>cpd :Copilot disable<CR>

let g:copilot_no_tab_map = v:true

autocmd User EasyMotionPromptBegin :let b:coc_diagnostic_disable = 1
autocmd User EasyMotionPromptEnd :let b:coc_diagnostic_disable = 0

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

nm <leader><c-t> :echo "hi<" . synIDattr(synID(line("."),col("."),1),"name")
    \ . '> trans<' . synIDattr(synID(line("."),col("."),0),"name")
    \ . "> lo<" . synIDattr(synIDtrans(synID(line("."),col("."),1)),"name")
    \ . ">"<CR>
