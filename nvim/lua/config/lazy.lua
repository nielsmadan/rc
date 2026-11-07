-- Bootstrap lazy.nvim
local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"

if not (vim.uv or vim.loop).fs_stat(lazypath) then
  local lazyrepo = "https://github.com/folke/lazy.nvim.git"
  local out = vim.fn.system({ "git", "clone", "--filter=blob:none", "--branch=stable", lazyrepo, lazypath })
  if vim.v.shell_error ~= 0 then
    vim.api.nvim_echo({
      { "Failed to clone lazy.nvim:\n", "ErrorMsg" },
      { out, "WarningMsg" },
      { "\nPress any key to exit..." },
    }, true, {})
    vim.fn.getchar()
    os.exit(1)
  end
end
vim.opt.rtp:prepend(lazypath)

vim.opt.rtp:prepend(lazypath)

-- Make sure to setup `mapleader` and `maplocalleader` before
-- loading lazy.nvim so that mappings are correct.
-- This is also a good place to setup other settings (vim.opt)
vim.g.mapleader = ","
vim.g.maplocalleader = "\\"

require("/config/gui")
require("/config/opt")
require("/config/cmd")
require("/config/diff")

-- The lockfile lives beside this config, unless that is a read-only checkout (/opt/rc on the Studio).
local config_dir = vim.fn.stdpath("config")
local lockfile = vim.fn.filewritable(config_dir) == 2 and config_dir .. "/lazy-lock.json"
  or vim.fn.stdpath("state") .. "/lazy-lock.json"

-- Setup lazy.nvim
require("lazy").setup({
  lockfile = lockfile,
  spec = {
    -- import your plugins
    { import = "plugins" },
  },
  -- Configure any other settings here. See the documentation for more details.
  -- colorscheme that will be used when installing plugins.
  install = { colorscheme = { "habamax" } },
  -- dev = true plugins load from a checkout here, or from GitHub on a machine without one.
  dev = { path = "~/wrksp/all", fallback = true },
  -- automatically check for plugin updates
  checker = { enabled = true },
})
