function prinSyntaxUnderCursor()
  for _, i1 in ipairs(vim.fn.synstack(vim.fn.line('.'), vim.fn.col('.'))) do
    local i2 = vim.fn.synIDtrans(i1)
    local n1 = vim.fn.synIDattr(i1, 'name')
    local n2 = vim.fn.synIDattr(i2, 'name')

    print(n1, '->', n2)
  end
end


vim.keymap.set('n', '<leader>q', prinSyntaxUnderCursor)
