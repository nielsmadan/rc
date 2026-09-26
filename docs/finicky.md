# Finicky

[Finicky](https://github.com/johnste/finicky) (Homebrew cask, **not** mise — it's a GUI `.app`) is set as the system default browser and routes every clicked link: personal → Brave, dev hosts → Chromium, client/customer URLs → LibreWolf (each in its own container).

The config is **split** to keep client identities out of the repo, mirroring the `hammerspoon/local.lua` / `hidutil.local.sh` pattern:

- **`finicky/finicky.ts`** (committed, symlinked to `~/.finicky.ts`) — the routing engine, `DEV_MATCHERS`, and `defaultBrowser`. Names no client. It `import`s `LOCAL` from `./finicky.local`.
- **`finicky/finicky.local.ts`** (**gitignored**) — `export const LOCAL`, an array of `{ container, match: [globs] }` entries holding all the identifiable routing (clients *and* the own `mathfiend` product). `install.sh` writes an empty `export const LOCAL = []` stub if missing so the import never fails on a fresh box; `finicky/finicky.local.ts.example` is the committed template.

**It must be `.ts`, not `.js`.** finicky resolves the `~/.finicky.ts` symlink to its real repo path, then bundles with esbuild — so the relative `import "./finicky.local"` resolves against `finicky/`. A `.js` config is Babel-staged into a cache dir *first* and esbuild bundles from there, which breaks the relative import.

Routing mechanics: a single guarded `rewrite` rule turns a matched URL into the `ext+container:name=<container>&url=<href>` scheme (read by LibreWolf's [Open external links in a container](https://addons.mozilla.org/firefox/addon/open-url-in-container/) add-on), and a handler sends `ext+container:*` to LibreWolf. The rewrite is guarded against re-rewriting an already-rewritten URL so rules can't chain; `containerFor()` returns the first matching entry. Shared services (GitHub, App Store Connect, AWS, Firebase, …) are scoped by path/ID/org/region so they don't collide across containers or hijack personal browsing. **Container names are case-sensitive** and must match those created in LibreWolf exactly.
