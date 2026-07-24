// finicky.ts — Finicky v4 link router (symlinked to ~/.finicky.ts).
//
// Set Finicky as the system default browser (it asks on first launch, or:
// System Settings → Desktop & Dock → Default web browser → Finicky).
// It then intercepts every clicked link and routes it to one of:
//
//   • Brave Browser — personal  (default / fallback)
//   • Chromium      — development
//   • LibreWolf     — client / customer work (per-client containers)
//
// All container routing (which would reveal client names) lives in the
// GITIGNORED finicky.local.ts (see finicky.local.ts.example for the format).
// This file holds only the routing engine and dev rules — so it is safe to
// commit. It's TypeScript (not .js) on purpose: finicky bundles .ts configs
// directly with esbuild, so the import below resolves against this repo dir;
// a .js config is Babel-staged elsewhere first and the import would break.

// ── Development → Chromium ──────────────────────────────────────────────
// URLs matching any of these open in Chromium. Globs: "*" matches anything.
const DEV_MATCHERS = [
  "localhost*",
  "127.0.0.1*",
  "0.0.0.0*",
  "*.local/*",
  "*.test/*",
  "news.ycombinator.com*",
  // Add your dev/staging hosts here, e.g.:
  // "staging.example.com/*",
];

// All container routing — clients and own projects alike — lives in the
// gitignored finicky.local.ts (empty stub on a fresh box). First match wins.
import { LOCAL } from "./finicky.local";

// ── Routing engine (rarely edited) ──────────────────────────────────────

// Full URL string, working with both a WHATWG URL and finicky's url object.
function fullUrl(url) {
  if (typeof url === "string") return url;
  if (url.href) return url.href;
  const proto = (url.protocol || "https").replace(/:$/, "");
  return `${proto}://${url.host || ""}${url.pathname || ""}${url.search || ""}${url.hash || ""}`;
}

function globToRegex(glob) {
  const escaped = glob.replace(/[.+?^${}()|[\]\\]/g, "\\$&").replace(/\*/g, ".*");
  return new RegExp(escaped, "i");
}

function matchesAny(href, patterns) {
  return patterns.some((p) => globToRegex(p).test(href));
}

// First entry whose patterns match, else null.
function containerFor(href) {
  for (const entry of LOCAL) {
    if (matchesAny(href, entry.match)) return entry.container;
  }
  return null;
}

// Build the ext+container: URL the LibreWolf add-on understands.
function containerUrl(name, href) {
  return `ext+container:name=${encodeURIComponent(name)}&url=${encodeURIComponent(href)}`;
}

export default {
  // Anything not matched by a handler below goes here: personal browsing.
  defaultBrowser: "Brave Browser",

  // One guarded rewrite: turn a matched URL into the container scheme so the
  // LibreWolf add-on drops it in the right container. Guarded against
  // re-rewriting an already-rewritten URL, so rules can never chain.
  rewrite: [
    {
      match: (url) => {
        const href = fullUrl(url);
        return !href.startsWith("ext+container:") && containerFor(href) !== null;
      },
      url: (url) => {
        const href = fullUrl(url);
        return containerUrl(containerFor(href), href);
      },
    },
  ],

  handlers: [
    // Client links (rewritten to ext+container:) → LibreWolf.
    { match: "ext+container:*", browser: "LibreWolf" },

    // Development → Chromium.
    { match: DEV_MATCHERS, browser: "Chromium" },

    // (Everything else falls through to defaultBrowser: Brave.)
  ],
};
