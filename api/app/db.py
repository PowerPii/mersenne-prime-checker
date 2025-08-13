# api/app/db.py
from __future__ import annotations

import sqlite3
import pathlib
import time

DB_PATH = pathlib.Path(__file__).resolve().parents[1] / "data" / "app.db"


# ---------- connect ----------
def connect(db_path: pathlib.Path = DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    with conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        # Consider: conn.execute("PRAGMA synchronous=NORMAL;")
    _ensure_core_schema(conn)
    _ensure_blocks_schema(conn)
    return conn


# ---------- core (jobs/artifacts) ----------
def _ensure_core_schema(conn: sqlite3.Connection):
    with conn:
        conn.executescript(
            """
        CREATE TABLE IF NOT EXISTS jobs(
          id TEXT PRIMARY KEY,
          kind TEXT NOT NULL,          -- 'll' | 'digits'
          p INTEGER NOT NULL,
          status TEXT NOT NULL,        -- queued | running | done | error
          created_at INTEGER NOT NULL,
          started_at INTEGER,
          finished_at INTEGER,
          error TEXT,
          engine_info TEXT
        );

        CREATE TABLE IF NOT EXISTS artifacts(
          job_id TEXT PRIMARY KEY,
          filename TEXT NOT NULL,
          path TEXT NOT NULL,
          digits INTEGER NOT NULL,
          size_bytes INTEGER NOT NULL,
          sha256 TEXT NOT NULL,
          FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
        );
        """
        )


def job_insert(
    c: sqlite3.Connection, id: str, kind: str, p: int, status: str = "queued"
):
    with c:
        c.execute(
            "INSERT INTO jobs(id,kind,p,status,created_at) VALUES(?,?,?,?,?)",
            (id, kind, int(p), status, int(time.time())),
        )


def job_start(c: sqlite3.Connection, id: str):
    with c:
        c.execute(
            "UPDATE jobs SET status='running', started_at=? WHERE id=?",
            (int(time.time()), id),
        )


def job_finish_ok(c: sqlite3.Connection, id: str, engine: str | None = None):
    with c:
        c.execute(
            "UPDATE jobs SET status='done', finished_at=?, engine_info=? WHERE id=?",
            (int(time.time()), engine, id),
        )


def job_fail(c: sqlite3.Connection, id: str, err: str):
    with c:
        c.execute(
            "UPDATE jobs SET status='error', finished_at=?, error=? WHERE id=?",
            (int(time.time()), err, id),
        )


def job_get(c: sqlite3.Connection, id: str):
    return c.execute("SELECT * FROM jobs WHERE id=?", (id,)).fetchone()


def artifact_insert(
    c: sqlite3.Connection,
    job_id: str,
    filename: str,
    path: str,
    digits: int,
    size_bytes: int,
    sha256: str,
):
    with c:
        c.execute(
            "INSERT INTO artifacts(job_id,filename,path,digits,size_bytes,sha256) VALUES(?,?,?,?,?,?)",
            (job_id, filename, path, int(digits), int(size_bytes), sha256),
        )


def artifact_get_by_job(c: sqlite3.Connection, job_id: str):
    return c.execute("SELECT * FROM artifacts WHERE job_id=?", (job_id,)).fetchone()


# ---------- blocks/exponents ----------
def _ensure_blocks_schema(conn: sqlite3.Connection):
    with conn:
        conn.executescript(
            """
        PRAGMA journal_mode=WAL;
        PRAGMA foreign_keys=ON;

        CREATE TABLE IF NOT EXISTS blocks(
          id INTEGER PRIMARY KEY,
          start_p INTEGER NOT NULL,
          end_p_excl INTEGER NOT NULL,
          candidate_count INTEGER NOT NULL DEFAULT 0,
          tested_count INTEGER NOT NULL DEFAULT 0,
          verified_count INTEGER NOT NULL DEFAULT 0,
          status TEXT NOT NULL DEFAULT 'idle',
          created_at INTEGER NOT NULL,
          started_at INTEGER,
          finished_at INTEGER
        );

        CREATE TABLE IF NOT EXISTS exponents(
          p INTEGER PRIMARY KEY,
          block_id INTEGER NOT NULL,
          status TEXT NOT NULL DEFAULT 'queued',   -- queued|running|done|error
          is_prime INTEGER,                        -- 0/1
          ns_elapsed INTEGER,
          engine_info TEXT,
          error TEXT,
          job_started_at INTEGER,
          job_finished_at INTEGER,
          FOREIGN KEY(block_id) REFERENCES blocks(id) ON DELETE CASCADE
        );

        -- Backfill legacy rows: derive block_id from p when it is NULL
        UPDATE exponents
           SET block_id = CAST(p / 1000000 AS INTEGER)
         WHERE block_id IS NULL;

        -- Ensure minimal blocks rows for any referenced block_id
        INSERT INTO blocks(id, start_p, end_p_excl, candidate_count, status, created_at)
        SELECT bid,
               bid*1000000,
               bid*1000000 + 1000000,
               0,
               'idle',
               CAST(strftime('%s','now') AS INTEGER)
          FROM (SELECT DISTINCT CAST(p / 1000000 AS INTEGER) AS bid
                  FROM exponents)
         WHERE NOT EXISTS (SELECT 1 FROM blocks b WHERE b.id = bid);

        -- Helpful indexes
        CREATE INDEX IF NOT EXISTS idx_exponents_block    ON exponents(block_id);
        CREATE INDEX IF NOT EXISTS idx_exponents_status   ON exponents(status);
        CREATE INDEX IF NOT EXISTS idx_exponents_prime_ok ON exponents(is_prime, status);
        """
        )


def block_upsert(
    conn: sqlite3.Connection,
    block_id: int,
    start: int,
    end_excl: int,
    candidate_count: int,
):
    with conn:
        conn.execute(
            """
        INSERT INTO blocks(id,start_p,end_p_excl,candidate_count,created_at)
        VALUES(?,?,?,?,?)
        ON CONFLICT(id) DO UPDATE SET
          start_p=excluded.start_p,
          end_p_excl=excluded.end_p_excl,
          candidate_count=excluded.candidate_count
        """,
            (
                int(block_id),
                int(start),
                int(end_excl),
                int(candidate_count),
                int(time.time()),
            ),
        )


def block_get(conn: sqlite3.Connection, block_id: int):
    return conn.execute("SELECT * FROM blocks WHERE id=?", (int(block_id),)).fetchone()


def block_list(conn: sqlite3.Connection, limit: int = 12):
    return conn.execute(
        "SELECT * FROM blocks ORDER BY id LIMIT ?", (int(limit),)
    ).fetchall()


def block_counts_bump(conn: sqlite3.Connection, block_id: int, tested_inc: int):
    with conn:
        conn.execute(
            "UPDATE blocks SET tested_count=tested_count+? WHERE id=?",
            (int(tested_inc), int(block_id)),
        )


def block_verified_bump(conn: sqlite3.Connection, block_id: int, inc: int = 1):
    with conn:
        conn.execute(
            "UPDATE blocks SET verified_count=verified_count+? WHERE id=?",
            (int(inc), int(block_id)),
        )


def exponent_seed(conn: sqlite3.Connection, block_id: int, primes: list[int]):
    with conn:
        conn.executemany(
            "INSERT OR IGNORE INTO exponents(p,block_id) VALUES(?,?)",
            [(int(p), int(block_id)) for p in primes],
        )


def exponents_by_block(conn: sqlite3.Connection, block_id: int):
    return conn.execute(
        "SELECT * FROM exponents WHERE block_id=? ORDER BY p", (int(block_id),)
    ).fetchall()


def exponents_unfinished(conn: sqlite3.Connection, block_id: int):
    # Skip done and currently running; scheduler will only pick queued/error/paused
    return conn.execute(
        "SELECT p FROM exponents WHERE block_id=? AND status!='done' AND status!='running' ORDER BY p",
        (int(block_id),),
    ).fetchall()


def exponent_start(conn: sqlite3.Connection, p: int):
    with conn:
        conn.execute(
            "UPDATE exponents SET status='running', job_started_at=? WHERE p=?",
            (int(time.time()), int(p)),
        )


def exponent_finish_ok(
    conn: sqlite3.Connection,
    p: int,
    is_prime: int,
    ns_elapsed: int,
    engine_info: str | None,
):
    with conn:
        conn.execute(
            """
            UPDATE exponents
            SET status='done', is_prime=?, ns_elapsed=?, engine_info=?, job_finished_at=?
            WHERE p=?
        """,
            (int(is_prime), int(ns_elapsed), engine_info, int(time.time()), int(p)),
        )
        if is_prime:
            conn.execute(
                """
                UPDATE blocks SET verified_count = verified_count + 1
                WHERE id = (SELECT block_id FROM exponents WHERE p=?)
            """,
                (int(p),),
            )


def exponent_fail(conn: sqlite3.Connection, p: int, err: str):
    with conn:
        conn.execute(
            "UPDATE exponents SET status='error', error=?, job_finished_at=? WHERE p=?",
            (err, int(time.time()), int(p)),
        )


def exponent_reset(conn, p: int):
    """Reset a running/cancelled exponent to 'queued' so it can be resumed later."""
    with conn:
        conn.execute(
            "UPDATE exponents SET status='queued', job_started_at=NULL, job_finished_at=NULL, error=NULL WHERE p=?",
            (int(p),),
        )


def primes_recent(conn: sqlite3.Connection, limit: int = 20):
    # Sorted with known finished times first, then nulls, newest first
    return conn.execute(
        """
        SELECT p, block_id, job_finished_at AS finished_at, engine_info, ns_elapsed
        FROM exponents
        WHERE is_prime = 1 AND status = 'done'
        ORDER BY (finished_at IS NULL), finished_at DESC
        LIMIT ?
    """,
        (int(limit),),
    ).fetchall()
