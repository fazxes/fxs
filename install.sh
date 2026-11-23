#!/usr/bin/env sh
set -eu

REPO="${FXS_REPO:-fazxes/fxs}"
BRANCH="${FXS_BRANCH:-main}"
INSTALL_DIR="${FXS_INSTALL_DIR:-$HOME/.local/bin}"
DEST="$INSTALL_DIR/fxs"
RUN_INIT=1

for arg in "$@"; do
  case "$arg" in
    --no-init) RUN_INIT=0 ;;
    -h|--help)
      echo "usage: install.sh [--no-init]"
      exit 0
      ;;
  esac
done

mkdir -p "$INSTALL_DIR"

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" 2>/dev/null && pwd || true)"
if [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/fxs" ]; then
  cp "$SCRIPT_DIR/fxs" "$DEST"
else
  URL="https://raw.githubusercontent.com/$REPO/$BRANCH/fxs"
  echo "Downloading fxs from $URL..."
  curl -fsSL "$URL" -o "$DEST"
fi

chmod +x "$DEST"
echo "Installed fxs to $DEST"

case ":$PATH:" in
  *":$INSTALL_DIR:"*) ;;
  *)
    echo ""
    echo "Add $INSTALL_DIR to your PATH:"
    echo "  export PATH=\"$INSTALL_DIR:\$PATH\""
    ;;
esac

if [ "$RUN_INIT" = "1" ] && [ -t 0 ]; then
  echo ""
  exec "$DEST" init
elif [ "$RUN_INIT" = "1" ]; then
  echo ""
  echo "Next step: run 'fxs init' (or 'fxs init --yes --team <team> --project <project>' for non-interactive setup)."
fi
