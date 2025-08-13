# api/app/_llcore.py
# ruff: noqa: E402
import os
import sys
import pathlib

# Allow manual override: export LLCORE_PATH=/abs/path/to/build/bindings/python
override = os.environ.get("LLCORE_PATH")
candidates: list[str] = []
if override:
    candidates.append(override)

# repo root = ../../ from this file
root = pathlib.Path(__file__).resolve().parents[2]
candidates += [
    str(root / "build" / "bindings" / "python"),
    str(root / "cpp" / "build" / "bindings" / "python"),  # if you ever build there
]

# Add first existing dir to sys.path
added = False
for d in candidates:
    if d and pathlib.Path(d).exists():
        if d not in sys.path:
            sys.path.append(d)
        added = True
        break

if not added:
    # Helpful error with hints
    hint = (
        "llcore extension not found. Build it with:\n"
        "  cmake -S cpp -B build -DCMAKE_BUILD_TYPE=Release -DBUILD_PY=ON\n"
        "  cmake --build build -j\n"
        "or set LLCORE_PATH to the directory containing llcore*.so"
    )
    raise ImportError(hint)
