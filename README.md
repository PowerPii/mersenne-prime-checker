# Mersenne Prime Checker

A modern, local‑first **Mersenne prime** hunter. It combines a highly optimized **C++ Lucas–Lehmer (LL) core** (GMP‑backed), a **FastAPI** backend with WebSocket progress streaming, and a **Next.js** frontend that visualizes 1M‑exponent blocks, live progress, and verified hits. Everything runs on your machine—no GIMPS dependency.

---

## Table of contents

* [Architecture](#architecture)
* [Requirements](#requirements)
* [Quick start](#quick-start)
* [Build the C++ core](#build-the-c-core)
* [API (FastAPI)](#api-fastapi)
* [Web (Next.js + Tailwind)](#web-nextjs--tailwind)
* [Python module usage (pybind11)](#python-module-usage-pybind11)
* [Development (lint/format)](#development-lintformat)
* [Repository layout](#repository-layout)
* [License](#license)

---

## Architecture

* **C++ LL core** (`cpp/`): Implements Lucas–Lehmer for $M_p = 2^p-1$ with constant‑time **Mersenne folding** (shift/add + up to two conditional subtracts). Uses **GMP** big integers and exposes progress digests for trustable telemetry.
* **Python API** (`api/`): FastAPI service for jobs, block orchestration, primes feed, and digit export. Streams progress via WebSockets. Stores metadata in **SQLite** (WAL enabled) and artifacts on disk.
* **Web UI** (`web/`): Next.js App Router + Tailwind. Renders 1M blocks (0–1M, 1–2M, …), shows a floating runner for live status, and lists verified primes with one‑click full‑digits download.

---

## Requirements

* **Toolchain:** CMake ≥ 3.20, C++17 compiler (clang/gcc), **GMP**.
* **Python:** 3.10+ (3.13 OK).
* **Node:** 18+ for Next.js.

On macOS (Homebrew):

```bash
brew install cmake gmp python node
```

---

## Quick start

Spin up everything (build C++ + API + Web):

```bash
./scripts/dev_up.sh
```

* API: [http://127.0.0.1:8000](http://127.0.0.1:8000)
* Web: [http://127.0.0.1:3000](http://127.0.0.1:3000)

> `dev_up.sh` builds the pybind11 extension and exports `PYTHONPATH` so the API can import `llcore`.

---

## Build the C++ core

```bash
cmake -S cpp -B build -DCMAKE_BUILD_TYPE=Release -DBUILD_PY=ON
cmake --build build -j

# CLI smoke
./build/ll_cli 31

# Python smoke
PYTHONPATH="$(pwd)/build/bindings/python" python3 tests/smoke_llcore.py
```

**Notes:**

* Release builds enable `-O3 -march=native` and LTO (IPO) via CMake.
* The LL loop performs exactly `p-2` squarings; progress digests are computed from residue limbs (no large transfers).

---

## API (FastAPI)

Run the API alone:

```bash
cd api
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH="$(git rev-parse --show-toplevel)/build/bindings/python" \
  uvicorn app.main:app --reload
```

### Key endpoints

* `POST /jobs` — run a single LL test: `{ "p": 44497 }` → job id.
* `GET /jobs/{id}` — job status/result.
* `WS  /ws/jobs/{id}` — per‑iteration digests.
* `GET /blocks` — list block cards (0–1M, 1–2M, …) with candidate/tested counts.
* `GET /blocks/{block_id}` — block details + exponent rows.
* `POST /blocks/{block_id}/start?concurrency=K` — schedule remaining primes; stream via `WS /ws/blocks/{block_id}`.
* `POST /blocks/{block_id}/stop` — request cancellation between exponents.
* `GET /primes?limit=N` — newest verified Mersenne primes with metadata.
* `POST /digits` → `GET /digits/{id}` → `GET /digits/{id}/download` — export/download decimal digits of **Mₚ**.

**Storage:** SQLite at `api/data/app.db` and artifacts under `api/data/artifacts/<job-id>/`.

---

## Web (Next.js + Tailwind)

```bash
cd web
npm install
npm run dev
```

* API base is configured as `http://127.0.0.1:8000` (see `web/src/lib/api.ts`).
* **Run** page: block grid with start/stop buttons, floating runner for current exponent.
* **Lists** page: verified primes with **Generate digits** → **Download** actions.

---

## Python module usage (pybind11)

Use the core directly from Python:

```python
import llcore  # ensure PYTHONPATH points to build/bindings/python
print(llcore.ll_test(44497))
# {'p': 44497, 'is_prime': True, 'iterations': 44495, ...}

llcore.write_mersenne_decimal(31, "/tmp/M_31.txt")
```

`ll_test(p, progress_stride=0, callback=fn)` calls `fn(iter:int, digest:bytes)` at an auto stride when `progress_stride=0` (or every N iterations if `>0`).

---

## Development (lint/format)

Install **pre-commit** and set up hooks:

```bash
pre-commit install
pre-commit run --all-files
```

Included hooks:

* **C++**: `clang-format`
* **Python**: `ruff` (lint + format) and `black`
* **Web**: `prettier`

Scripts:

```bash
./scripts/fmt.sh   # run formatters
./scripts/lint.sh  # run linters
./scripts/build_all.sh
```

---

## Repository layout

```
cpp/         # C++ LL core (+ pybind11 module, tests, CLI)
api/         # FastAPI service (jobs, blocks, primes, digits, websockets)
web/         # Next.js UI (blocks grid, floating runner, lists)
scripts/     # dev_up.sh, build_all.sh, fmt.sh, lint.sh
```

---

## License

This project is licensed under the **MIT License**. See [`LICENSE`](./LICENSE).
