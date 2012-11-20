"set font
if has("gui_running")
  if has("gui_gtk2")
    let s:FontSize = 10
    exe "set guifont=Inconsolata\\ " . s:FontSize
  elseif has("gui_win32")
    let s:FontSize = 12
    exe "set guifont=Consolas:h" . s:FontSize . ":cANSI"
  endif
endif

map <leader>fu :call IncreaseFontSize()<CR>
map <leader>fd :call DecreaseFontSize()<CR>

function! IncreaseFontSize()
    let s:FontSize = s:FontSize + 1
    if has("gui_gtk2")
        exe "set guifont=Inconsolata\\ " . s:FontSize
    elseif has("gui_win32")
        exe "set guifont=Consolas:h" . s:FontSize . ":cANSI"
    endif
endfunction

function! DecreaseFontSize()
    let s:FontSize = s:FontSize - 1
    if has("gui_gtk2")
        exe "set guifont=Inconsolata\\ " . s:FontSize
    elseif has("gui_win32")
        exe "set guifont=Consolas:h" . s:FontSize . ":cANSI"
    endif
endfunction

winpos 0 0
set lines=50
set columns=999

set guioptions-=m  "remove menu bar
set guioptions-=T  "remove toolbar
set guioptions-=l  "no scroll bars (left and right)
set guioptions-=L
set guioptions-=r
set guioptions-=R
