vim.opt.shortmess:append { c = true } -- no intro
vim.opt.shortmess:append { I = true } -- no intro

vim.opt.number=true

vim.opt.helpheight=0 -- no min window height for help window.
vim.opt.cmdheight=2 -- more space for commands.

vim.opt.swapfile=false
vim.opt.undodir="~/.tmp/nvim_undo"

vim.opt.autowriteall=true

vim.opt.textwidth=119
vim.opt.formatoptions="cqn1"

-- indent options
vim.opt.tabstop=2
vim.opt.expandtab=true
vim.opt.shiftwidth=2
vim.opt.softtabstop=2

-- search options
vim.opt.ignorecase=true
vim.opt.smartcase=true

-- scrolloffs
vim.opt.scrolloff=5
vim.opt.sidescrolloff=7

-- command line completion
vim.opt.wildmode="list:longest,full"

-- show menu and preview for completion
vim.opt.completeopt="menu"

-- allow increment for characters
vim.opt.nrformats="octal,hex,alpha"
