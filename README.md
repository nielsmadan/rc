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
