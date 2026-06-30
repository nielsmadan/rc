#!/usr/bin/env bash
# reload.sh — force Finicky to rebuild its config bundle and restart.
#
# Why this exists: Finicky compiles ~/.finicky.ts (TypeScript) into a cached
# JS bundle via esbuild and keys the cache on the *top-level* config's mtime
# only. Our config is split — finicky.ts imports the gitignored
# finicky.local.ts — so editing finicky.local.ts leaves finicky.ts's mtime
# untouched, and Finicky keeps serving the stale bundle even across a restart.
#
# This script bumps finicky.ts's mtime, wipes the bundle/config caches, and
# relaunches Finicky so the next link uses the freshly compiled config.
# Run it after editing finicky.local.ts (or finicky.ts).

set -euo pipefail

CONFIG="$HOME/.finicky.ts"
CACHE_DIR="$HOME/Library/Caches/Finicky"

# Bump the top-level config mtime so Finicky's cache key invalidates even if
# only an imported file changed.
[ -e "$CONFIG" ] && touch -h "$CONFIG" && touch "$(readlink "$CONFIG" 2>/dev/null || echo "$CONFIG")"

# Wipe the compiled bundle and its cache pointer.
if [ -d "$CACHE_DIR" ]; then
  rm -f "$CACHE_DIR"/finicky_bundle_*.js "$CACHE_DIR"/config_cache_*.json
  echo "cleared Finicky bundle cache"
fi

# Restart Finicky so it recompiles on launch.
osascript -e 'quit app "Finicky"' 2>/dev/null || true
sleep 1
open -a Finicky
echo "relaunched Finicky — config recompiled"
