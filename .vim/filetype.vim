if exists("did_load_filetypes")
    finish
endif

augroup filetypedetect
    au BufNewFile,BufRead *.xaml setf xml
augroup END
