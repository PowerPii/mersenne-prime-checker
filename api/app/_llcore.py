# api/app/_llcore.py
# ruff: noqa: E402
from __future__ import annotations
import sys
import os
import pathlib
import importlib


def _candidate_paths():
    # repo root = api/.. ; primary build is <root>/build/bindings/python
    root = pathlib.Path(__file__).resolve().parents[2]
    yield root / "build" / "bindings" / "python"
    # fallback: sometimes people build inside cpp/
    yield root / "cpp" / "build" / "bindings" / "python"
    # last resort: current working directory build
    yield pathlib.Path.cwd() / "build" / "bindings" / "python"
    # also honor PYTHONPATH if already set
    for part in os.environ.get("PYTHONPATH", "").split(os.pathsep):
        if part:
            yield pathlib.Path(part)


def _ensure_on_path():
    for p in _candidate_paths():
        if p.exists():
            sp = str(p.resolve())
            if sp not in sys.path:
                sys.path.insert(0, sp)
            return


_ensure_on_path()

# Import the compiled extension and export it as `llcore`
llcore = importlib.import_module("llcore")
__all__ = ["llcore"]
