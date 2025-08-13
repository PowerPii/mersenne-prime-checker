"use client";
import { useEffect, useMemo, useState } from "react";
import { apiFetch, API_BASE } from "@/lib/api";
import type { PrimeRow, DigitsCreateResp, DigitsJob } from "@/types";

type Generating = { [p: number]: { jobId: string; downloadUrl?: string } };

export default function PrimeHits() {
  const [rows, setRows] = useState<PrimeRow[]>([]);
  const [gen, setGen] = useState<Generating>({});
  const [asc, setAsc] = useState(true);

  useEffect(() => {
    let alive = true,
      inflight = false;
    const load = async () => {
      if (inflight) return;
      inflight = true;
      try {
        const data = await apiFetch<PrimeRow[]>("/primes?limit=200"); // grab more, we'll dedupe
        if (alive) setRows(data);
      } finally {
        inflight = false;
      }
    };
    load();
    const t = setInterval(load, 2000);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, []);

  // De-duplicate by p (keep the newest finished_at)
  const unique = useMemo(() => {
    const m = new Map<number, PrimeRow>();
    for (const r of rows) {
      const prev = m.get(r.p);
      if (!prev || (r.finished_at ?? 0) > (prev.finished_at ?? 0)) {
        m.set(r.p, r);
      }
    }
    return Array.from(m.values());
  }, [rows]);

  // Sort ascending/descending by p
  const sorted = useMemo(() => {
    const s = [...unique].sort((a, b) => (asc ? a.p - b.p : b.p - a.p));
    return s;
  }, [unique, asc]);

  async function generateDigits(p: number) {
    const { id } = await apiFetch<DigitsCreateResp>("/digits", {
      method: "POST",
      body: JSON.stringify({ p }),
    });
    setGen((g) => ({ ...g, [p]: { jobId: id } }));

    const poll = async () => {
      const j = await apiFetch<DigitsJob>(`/digits/${id}`);
      if (j.status === "done" && j.artifact) {
        setGen((g) => ({
          ...g,
          [p]: { jobId: id, downloadUrl: `${API_BASE}/digits/${id}/download` },
        }));
      } else {
        setTimeout(poll, 800);
      }
    };
    poll();
  }

  return (
    <div className="mt-10 max-w-5xl">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-2xl font-semibold text-black dark:text-white">
          Found Mersenne Primes
        </h2>
        <button
          onClick={() => setAsc((v) => !v)}
          className="px-3 py-1.5 rounded border border-slate-200 dark:border-slate-800 text-sm hover:bg-slate-50 dark:hover:bg-slate-900"
        >
          Sort: {asc ? "Ascending" : "Descending"}
        </button>
      </div>

      {sorted.length === 0 ? (
        <div className="text-sm text-slate-500">
          No primes yet—start a block to begin testing.
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {sorted.map((r) => {
            const g = gen[r.p];
            // composite key prevents collisions even if a duplicate row briefly appears
            const key = `p-${r.p}-${r.finished_at ?? 0}`;
            return (
              <div
                key={key}
                className="w-full rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-black p-4 flex items-center justify-between gap-4"
              >
                {/* left side details */}
                <div className="min-w-0">
                  <div className="flex items-center gap-3">
                    <div className="text-lg font-bold">M{r.p}</div>
                    <div className="text-xs text-slate-500">
                      block {r.block_id}-{(r.block_id ?? 0) + 1}M
                    </div>
                  </div>
                  <div className="text-sm text-slate-700 dark:text-slate-300 mt-1">
                    digits: <b>{r.digits.toLocaleString()}</b>
                  </div>
                  <div className="text-xs text-slate-500">
                    {r.finished_at
                      ? new Date(r.finished_at * 1000).toLocaleString()
                      : "finished time unknown"}
                  </div>
                  {r.engine_info ? (
                    <div className="text-xs text-slate-500">
                      {r.engine_info}
                    </div>
                  ) : null}
                </div>

                {/* right side actions */}
                <div className="shrink-0">
                  {!g?.downloadUrl ? (
                    <button
                      onClick={() => generateDigits(r.p)}
                      disabled={!!g?.jobId}
                      className="px-3 py-1.5 rounded bg-emerald-600 text-white hover:bg-emerald-500 disabled:opacity-50"
                    >
                      {g?.jobId ? "Preparing…" : "Generate digits"}
                    </button>
                  ) : (
                    <a
                      href={g.downloadUrl}
                      className="px-3 py-1.5 rounded bg-emerald-600 text-white hover:bg-emerald-500"
                      target="_blank"
                    >
                      Download digits
                    </a>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
