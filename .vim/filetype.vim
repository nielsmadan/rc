if exists("did_load_filetypes")
    finish
endif

augroup filetypedetect
    au BufNewFile,BufRead *.xaml setf xml
    au! BufRead    *.svn-base execute 'doautocmd filetypedetect BufRead ' . expand('%:r')
    au! BufNewFile *.svn-base execute 'doautocmd filetypedetect BufNewFile ' . expand('%:r')
augroup END
