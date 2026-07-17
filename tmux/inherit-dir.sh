#!/bin/sh
# Called from tmux hooks (after-split-window / after-new-window) with the new
# pane's id as $1. iTerm2's tmux integration issues split-window/new-window
# WITHOUT -c, so new panes open in the session's start dir (remote $HOME) rather
# than the directory of the pane you split from. This puts them back in sync:
# cd the new pane into the working directory of the pane it was split from
# ({last} = the previously-active pane in the same window).
new_pane="$1"
src_dir=$(tmux display-message -pt '{last}' '#{pane_current_path}' 2>/dev/null)
[ -n "$src_dir" ] && [ -d "$src_dir" ] && \
  tmux send-keys -t "$new_pane" " cd \"$src_dir\"" Enter
