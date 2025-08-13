# tests/smoke_llcore.py
import sys, math, pathlib, tempfile, os

# Make the compiled extension importable (repo_root/build/bindings/python)
HERE = pathlib.Path(__file__).resolve()
REPO = HERE.parents[1]                 # repo root (…/tests/..)
EXT  = REPO / "build" / "bindings" / "python"
if EXT.exists() and str(EXT) not in sys.path:
    sys.path.append(str(EXT))

import llcore # type: ignore

def expected_calls(p: int, stride: int) -> int:
    total = max(0, p - 2)
    s = stride if stride else max(1, total // 100)   # 0 => auto (~1%)
    return 0 if total == 0 else math.ceil(total / s)

def test_auto_stride():
    p = 31
    calls = 0
    def cb(i, d):
        nonlocal calls; calls += 1
    res = llcore.ll_test(p, progress_stride=0, callback=cb)
    assert res["is_prime"] is True
    assert calls == expected_calls(p, 0)
    print(f"[auto stride] p={p} calls={calls}")

def test_explicit_stride():
    p, stride = 31, 10
    calls = 0
    def cb(i, d):
        nonlocal calls; calls += 1
    res = llcore.ll_test(p, progress_stride=stride, callback=cb)
    assert res["is_prime"] is True
    assert calls == expected_calls(p, stride)
    print(f"[explicit stride] p={p} stride={stride} calls={calls}")

def test_decimal_writer():
    p = 31
    out = os.path.join(tempfile.gettempdir(), f"M_{p}.txt")
    meta = llcore.write_mersenne_decimal(p, out)
    text = open(out, "r").read().strip()
    assert meta["digits"] == len(text)
    assert text == "2147483647"
    print(f"[writer] p={p} digits={meta['digits']} path={out}")

if __name__ == "__main__":
    test_auto_stride()
    test_explicit_stride()
    test_decimal_writer()
    print("OK")
