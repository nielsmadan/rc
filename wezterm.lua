-- WezTerm config — keybindings match kitty.conf and iterm2/dynamic-profile.json.
-- Update VIM_KEYBINDINGS sibling docs only if you also touch kitty; this file
-- mirrors that scheme.

local wezterm = require 'wezterm'
local act = wezterm.action
local config = wezterm.config_builder()

config.color_scheme = nil
config.colors = {
  -- P3 → sRGB hex (no color-space conversion; matches how the iTerm2 profile
  -- renders in practice on the same display).
  background = '#131414',
  foreground = '#d0be9c',
  cursor_bg  = '#ffffff',
  cursor_fg  = '#000000',
  cursor_border  = '#ffffff',
  selection_bg   = '#2b2b3d',
  selection_fg   = '#9cf881',
  ansi = {
    '#141617', -- black
    '#da713a', -- red
    '#c4cf5a', -- green
    '#e9d082', -- yellow
    '#79a1e6', -- blue
    '#ef9fbf', -- magenta
    '#f0a176', -- cyan
    '#ffffff', -- white
  },
  brights = {
    '#4c4c4c',
    '#c45e44',
    '#c4cf5a',
    '#e9d082',
    '#4784f6',
    '#ef9fbf',
    '#95a4da',
    '#ffffff',
  },
}

config.window_close_confirmation = 'NeverPrompt'
config.use_fancy_tab_bar = true
config.audible_bell = 'Disabled'

local keys = {
  -- Splits (kitty cmd+d / cmd+shift+d)
  { key = 'd', mods = 'CMD',       action = act.SplitPane { direction = 'Right', command = { domain = 'CurrentPaneDomain' } } },
  { key = 'd', mods = 'CMD|SHIFT', action = act.SplitPane { direction = 'Down',  command = { domain = 'CurrentPaneDomain' } } },

  -- Tabs / windows
  { key = 't', mods = 'CMD', action = act.SpawnTab 'CurrentPaneDomain' },
  { key = 'w', mods = 'CMD', action = act.CloseCurrentPane { confirm = false } },
  { key = 'n', mods = 'CMD', action = act.SpawnWindow },

  -- Pane navigation (ctrl+hjkl)
  { key = 'h', mods = 'CTRL', action = act.ActivatePaneDirection 'Left' },
  { key = 'j', mods = 'CTRL', action = act.ActivatePaneDirection 'Down' },
  { key = 'k', mods = 'CTRL', action = act.ActivatePaneDirection 'Up' },
  { key = 'l', mods = 'CTRL', action = act.ActivatePaneDirection 'Right' },

  -- Pane resize (cmd+shift+hjkl)
  { key = 'h', mods = 'CMD|SHIFT', action = act.AdjustPaneSize { 'Left',  2 } },
  { key = 'j', mods = 'CMD|SHIFT', action = act.AdjustPaneSize { 'Down',  2 } },
  { key = 'k', mods = 'CMD|SHIFT', action = act.AdjustPaneSize { 'Up',    2 } },
  { key = 'l', mods = 'CMD|SHIFT', action = act.AdjustPaneSize { 'Right', 2 } },

  -- Reload (cmd+shift+r)
  { key = 'r', mods = 'CMD|SHIFT', action = act.ReloadConfiguration },
}

for i = 1, 9 do
  table.insert(keys, { key = tostring(i), mods = 'CMD', action = act.ActivateTab(i - 1) })
end

config.keys = keys

return config
