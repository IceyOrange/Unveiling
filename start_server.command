#!/usr/bin/env zsh
# Start the Unveiling Flask dev server locally.
# On macOS: double-click this file in Finder to open a Terminal window.

# Resolve this script's directory (project root)
cd "$(dirname "$0")" || exit 1

PROJECT_ROOT=$(pwd)
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"
APP_ENTRY="$PROJECT_ROOT/src/frontend/app.py"
PORT=5001
URL="http://127.0.0.1:$PORT"

echo "==================================="
echo "  Unveiling Local Server Starter"
echo "==================================="
echo "Project root: $PROJECT_ROOT"
echo "Python:       $VENV_PYTHON"
echo "App entry:    $APP_ENTRY"
echo "URL:          $URL"
echo ""

if [ ! -f "$VENV_PYTHON" ]; then
    echo "❌ Virtual environment not found at $VENV_PYTHON"
    echo "   Please create it first, e.g.: python3 -m venv .venv"
    read -rs -k "?Press any key to exit..."
    exit 1
fi

if [ ! -f "$APP_ENTRY" ]; then
    echo "❌ Flask app entry not found at $APP_ENTRY"
    read -rs -k "?Press any key to exit..."
    exit 1
fi

# Optional: open browser after a short delay
(
    sleep 2
    if command -v open >/dev/null 2>&1; then
        open "$URL"
    fi
) &

echo "🚀 Starting Flask server on $URL ..."
echo "   Press Ctrl+C to stop."
echo ""

exec "$VENV_PYTHON" "$APP_ENTRY"
