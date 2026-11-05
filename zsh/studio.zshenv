# The Mac Studio shared user's ~/.zshenv (install.sh links it), which install.sh and
# studio-deploy also source: `ssh studio <cmd>` and non-login shells start with only
# /usr/bin:/bin:/usr/sbin:/sbin. POSIX sh, for those bash scripts.
for _d in /opt/homebrew/sbin /opt/homebrew/bin "${MISE_SYSTEM_DATA_DIR:-/usr/local/share/mise}/shims" "$HOME/.local/bin"; do
  case ":$PATH:" in
    *":$_d:"*) ;;
    *) if [ -d "$_d" ]; then PATH="$_d:$PATH"; fi ;;
  esac
done
unset _d
export PATH
# ~/.colima/default/colima.yaml links to the deploy-owned copy, which `colima start` would rewrite.
export COLIMA_SAVE_CONFIG=0
