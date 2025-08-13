# scripts/dev_up.sh
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-3000}"

cleanup() {
  echo
  echo "==> Shutting down dev processes..."
  [[ -n "${API_PID:-}" ]] && kill "${API_PID}" 2>/dev/null || true
  [[ -n "${WEB_PID:-}" ]] && kill "${WEB_PID}" 2>/dev/null || true
}
trap cleanup INT TERM EXIT

echo "==> Starting API (http://127.0.0.1:${API_PORT})"
cd "$ROOT/api"
source .venv/bin/activate
PYTHONPATH="${PYTHONPATH:-}:$ROOT/build/bindings/python" \
  uvicorn app.main:app --reload --port "${API_PORT}" &
API_PID=$!
deactivate

echo "==> Starting Web (http://127.0.0.1:${WEB_PORT})"
cd "$ROOT/web"
if command -v pnpm >/dev/null 2>&1; then
  pnpm dev --port "${WEB_PORT}" &
else
  npm run dev -- --port "${WEB_PORT}" &
fi
WEB_PID=$!

echo "🟢 Dev up. Ctrl-C to stop."
wait
