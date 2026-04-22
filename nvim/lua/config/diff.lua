-- Diff-mode keybindings. Works for both nvim started with -d (git difftool /
-- mergetool) and dynamically-created diff buffers (diffview.nvim).
local augroup = vim.api.nvim_create_augroup("DiffModeKeymaps", { clear = true })

local function apply_diff_mappings()
  local opts = { buffer = 0, silent = true }

  -- Arrow nav: up/down jump hunks, left/right pull/push.
  vim.keymap.set("n", "<Down>", "]c", opts)
  vim.keymap.set("n", "<Up>", "[c", opts)
  vim.keymap.set("n", "<Left>", "do", opts)
  vim.keymap.set("n", "<Right>", "dp", opts)

  vim.keymap.set("n", "<M-r>", ":diffupdate<CR>", opts)
  vim.keymap.set("n", "<M-d>", "]c", opts)
  vim.keymap.set("n", "<M-u>", "[c", opts)

  -- Get from buffer N (for 3-way merges).
  vim.keymap.set("n", "<M-1>", ":diffget 1<CR>", opts)
  vim.keymap.set("n", "<M-2>", ":diffget 2<CR>", opts)
  vim.keymap.set("n", "<M-3>", ":diffget 3<CR>", opts)
  vim.keymap.set("n", "<M-g>", ":diffget<CR>", opts)

  vim.keymap.set("n", "<M-p>1", ":diffput 1<CR>", opts)
  vim.keymap.set("n", "<M-p>2", ":diffput 2<CR>", opts)
  vim.keymap.set("n", "<M-p>3", ":diffput 3<CR>", opts)
  vim.keymap.set("n", "<M-p><M-p>", ":diffput<CR>", opts)

  vim.keymap.set("n", "<leader><C-i>", ":wqall!<CR>", opts)
end

-- Reapply whenever a window/buffer with diff mode becomes active.
vim.api.nvim_create_autocmd({ "BufWinEnter", "WinEnter" }, {
  group = augroup,
  callback = function()
    if vim.wo.diff then
      apply_diff_mappings()
    end
  end,
})

-- git difftool / mergetool case: nvim launched with -d.
if vim.o.diff then
  vim.opt.wrap = true
  vim.opt.linebreak = true
  apply_diff_mappings()
  vim.api.nvim_create_autocmd("VimResized", {
    group = augroup,
    command = "wincmd =",
  })
end
