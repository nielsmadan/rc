# Window placement

Monitor names and app rules live in the gitignored `local.lua`; copy
`local.lua.example` for a starting point. `init.lua` loads this config on reload.

For apps such as Mechabellum that use native macOS fullscreen, add a placement
and include the app's exact name in `fullscreen_apps`:

```lua
app_placements = { Mechabellum = h.fill },
fullscreen_apps = { "Mechabellum" },
```

`fullscreen_placement.lua` moves these windows by leaving fullscreen, moving to
the resolved monitor, and restoring fullscreen. Each step checks the window's
actual state and retries every 1.2 seconds. Startup placement waits at least
2.5 seconds before acting and observes the window for at least 15 seconds to
catch the game's own delayed monitor changes. Success requires three seconds
of stable placement; only then is the window marked as placed.

Attempts stop after 45 seconds, restore fullscreen if possible, and log the
failure in Hammerspoon's console. Repeated title/visibility events share one
attempt and cannot restart an exhausted attempt. F18+H, monitor changes, and
wake can start a fresh attempt. Closing the window cancels its pending work.
The target monitor is resolved again on each retry.

Mechabellum can still initially appear on a side monitor while loading. During
live diagnosis it briefly stopped responding to Accessibility calls, so a
single delayed move could fail before the game became ready.

Run the simulated timing and failure tests through Hammerspoon's Lua runtime:

```sh
hs -c 'return dofile(hs.configdir .. "/test_fullscreen_placement.lua")'
```

After a programmatic config edit, run `hs -c 'hs.reload()'` to load it. For a live
startup check, launch Mechabellum from Steam and verify that it reaches the
configured monitor with fullscreen restored, without calling `homeWindows()`
or manually moving it.

The controlled live test used `UnitySelectMonitor = 1`: the game appeared
fullscreen on LG Ultra HD at 11 seconds, moved to LG HDR 5K at 14 seconds, and
returned to fullscreen there at 15 seconds. No manual placement was used.
