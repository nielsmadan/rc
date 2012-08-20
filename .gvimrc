"set font
if has("gui_running")
  if has("gui_gtk2")
    set guifont=Inconsolata\ 10
  elseif has("gui_win32")
    set guifont=Consolas:h12:cANSI
  endif
endif

winpos 0 0
set lines=50
set columns=999

set guioptions-=m  "remove menu bar
set guioptions-=T  "remove toolbar
set guioptions-=l  "no scroll bars (left and right)
set guioptions-=L
set guioptions-=r
set guioptions-=R
