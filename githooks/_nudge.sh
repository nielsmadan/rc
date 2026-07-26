#!/bin/sh
# Shared body for the post-* hooks. Runs install.sh in check mode and prints its
# report if anything went stale; never re-links anything, never fails the git
# operation that triggered it.

repo="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
[ -x "$repo/install.sh" ] || exit 0

out="$("$repo/install.sh" --check --quiet 2>&1)" && exit 0

echo
printf '%s\n' "$out"
exit 0
