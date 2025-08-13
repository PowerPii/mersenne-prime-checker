# scripts/fmt.sh
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> Format C++ (clang-format)"
if command -v clang-format >/dev/null 2>&1; then
  find "$ROOT/cpp" \( -name "*.hpp" -o -name "*.h" -o -name "*.cpp" \) -not -path "*/build/*" -print0 | xargs -0 clang-format -i
else
  echo "clang-format not found (brew install clang-format)"; fi

echo "==> Format Python (black)"
if command -v black >/dev/null 2>&1; then
  black "$ROOT/api" "$ROOT/tests"
else
  echo "black not found (pip install black)"; fi

echo "==> Format web (prettier)"
cd "$ROOT/web"
if npx --yes --quiet prettier --version >/dev/null 2>&1; then
  npx --yes prettier --write "src/**/*.{ts,tsx,js,jsx,json,css,md}"
else
  echo "prettier not found (npm i -D prettier)"; fi

echo "✅ Formatting done."
