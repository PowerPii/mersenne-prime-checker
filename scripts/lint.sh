# scripts/lint.sh
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> Lint C++ (clang-tidy if available)"
if command -v clang-tidy >/dev/null 2>&1; then
  cmake -S "$ROOT/cpp" -B "$ROOT/build" -DCMAKE_BUILD_TYPE=Debug -DCMAKE_EXPORT_COMPILE_COMMANDS=ON >/dev/null
  clang-tidy -p "$ROOT/build" $(find "$ROOT/cpp/src" -name "*.cpp" -not -path "*/build/*") || true
else
  echo "clang-tidy not found (brew install llvm)"; fi

echo "==> Lint Python (ruff)"
if command -v ruff >/dev/null 2>&1; then
  ruff check "$ROOT/api"
else
  echo "ruff not found (pip install ruff)"; fi

echo "==> Lint web (eslint)"
cd "$ROOT/web"
if npx --yes --quiet eslint --version >/dev/null 2>&1; then
  npx --yes eslint "src/**/*.{ts,tsx,js,jsx}"
else
  echo "eslint not found (npm i -D eslint)"; fi

echo "✅ Linting done."
