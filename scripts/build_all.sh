# scripts/build_all.sh
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> Build C++ core (+pybind11) & tests"
cmake -S "$ROOT/cpp" -B "$ROOT/build" -DCMAKE_BUILD_TYPE=Release -DBUILD_PY=ON -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
cmake --build "$ROOT/build" -j
ctest --test-dir "$ROOT/build" --output-on-failure || true

echo "==> API deps"
cd "$ROOT/api"
if [[ ! -d .venv ]]; then python3 -m venv .venv; fi
source .venv/bin/activate
pip install -U pip >/dev/null
if [[ -f requirements.txt ]]; then pip install -r requirements.txt; fi
deactivate

echo "==> Web deps"
cd "$ROOT/web"
if command -v pnpm >/dev/null 2>&1; then
  pnpm install
else
  npm install
fi

echo "✅ build_all done."
