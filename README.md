Welcome to my dotfiles and small scripts!

## Updating tools

`bin/update-tools` updates global mise CLI tools, Homebrew packages and GUI apps,
uv tools, standalone pipx tools, and agent-browser's Chrome download. It also
updates mise and uv themselves. `install.sh` links it as `update-tools` on PATH.

```sh
update-tools --check          # preview commands without running updates
update-tools                  # run updates
update-tools --bump-runtimes   # also advance language runtime pins
```

The script runs from your home directory so a project's mise config or Python
environment does not select the tools being updated. Mise CLI pins are advanced
with `--bump`, preserving exact versions for npm tools. Language runtimes keep
their configured versions/ranges by default; `node = "24"`, for example, stays
on Node 24. Vault always keeps its explicit pin because its latest-tag resolver
has selected releases without macOS builds.

`--check` prints the planned commands; it does not query available releases or
run installers. It reads mise's current tool list, which requires Python 3.
Missing package managers are skipped. Failed steps are reported at the end with
exit status 1, while independent updates continue. A failed Homebrew metadata
refresh skips its package upgrades. Package-manager prompts remain interactive.

macOS, App Store apps, project dependencies, unmanaged pip/npm installations,
and git checkouts are outside the script's scope. Mise-managed Python tools are
updated through mise; `pipx upgrade-all` covers separate pipx installations.
After updating, open a new terminal and restart long-running agent sessions to
pick up new executable paths.

Run the script's checks with `python3 bin/test_update_tools.py`.

## Checking runtime versions

`check-runtimes` reports new stable releases for globally configured mise language
runtimes, including releases beyond existing pins. It only queries metadata;
it never installs runtimes or changes configuration. Requires Python 3.9+, mise,
and curl. `install.sh` links it onto PATH.

```sh
check-runtimes                # check all global language runtimes
check-runtimes node java      # check selected runtimes
```

The table shows the configured request, installed version, latest stable release,
and latest LTS release where tracked. `NEW` marks versions newer than the installed
one; `[LTS]` is highlighted in terminals. Set `NO_COLOR` to disable colors. An LTS
version older than your installed version is shown without `NEW`.

The status describes the installed runtime:

| With LTS | Color | Without LTS | Color |
| --- | --- | --- | --- |
| latest lts | green | up to date | green |
| older lts | yellow | patch behind | light green |
| off lts | yellow | minor behind | yellow |
| | | major behind | red |

`latest lts` means the newest LTS release line, even when a patch behind;
`older lts` means an earlier LTS line. Node and Java use major release lines;
Deno and .NET use major.minor lines. Deno's installed `--version` channel must
also be `lts`; stable-channel builds are `off lts` even on the same version line.
Missing installations and failed lookups show `not installed` or `unknown`.

Java checks keep the configured distribution (for example, Zulu) while looking
across major versions. LTS sources are
[Node's release index](https://nodejs.org/dist/index.json),
[Adoptium's Java release metadata](https://api.adoptium.net/v3/info/available_releases),
[Deno's LTS channel](https://dl.deno.land/release-lts-latest.txt), and
[Microsoft's .NET release index](https://builds.dotnet.microsoft.com/dotnet/release-metadata/releases-index.json).
Deno LTS is a separate release channel. `—` means LTS is not tracked for that
runtime; `unknown` means a lookup failed.

The command runs its queries from your home directory, independently of the
current project's config. Mise's release metadata cache may refresh. Exit status
is 0 for a complete check, including when updates exist, 1 for lookup failures,
and 2 for invalid arguments. Successful lookups are still shown if others fail.

Run the checks with `python3 bin/test_check_runtimes.py`.
