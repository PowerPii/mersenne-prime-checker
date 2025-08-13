"use client";
import { useEffect, useMemo, useState } from "react";
import { apiFetch, API_BASE } from "@/lib/api";
import type { PrimeRow, DigitsCreateResp, DigitsJob } from "@/types";

type Generating = { [p: number]: { jobId: string; downloadUrl?: string } };

export default function PrimeHits() {
  const [rows, setRows] = useState<PrimeRow[]>([]);
  const [gen, setGen] = useState<Generating>({});
  const [sortAsc, setSortAsc] = useState<boolean>(true);

  useEffect(() => {
    let alive = true, inflight = false;
    const load = async () => {
      if (inflight) return;
      inflight = true;
      try {
        const data = await apiFetch<PrimeRow[]>("/primes?limit=20");
        if (alive) setRows(data);
      } finally { inflight = false; }
    };
    load();
    const t = setInterval(load, 2000);
    return () => { alive = false; clearInterval(t); };
  }, []);

  const sorted = useMemo(() => {
    const copy = [...rows];
    copy.sort((a, b) => (sortAsc ? a.p - b.p : b.p - a.p));
    return copy;
  }, [rows, sortAsc]);

  async function generateDigits(p: number) {
    // kick off digits job for this p
    const { id } = await apiFetch<DigitsCreateResp>("/digits", {
      method: "POST",
      body: JSON.stringify({ p }),
    });
    setGen((g) => ({ ...g, [p]: { jobId: id } }));
    // poll until artifact ready
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
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-2xl font-semibold text-black">Found Mersenne Primes</h2>
        <button
          onClick={() => setSortAsc((s) => !s)}
          className="text-sm px-3 py-1.5 rounded border border-slate-300 hover:bg-slate-50"
          aria-label="Toggle sort order"
        >
          Sort: <b>{sortAsc ? "Ascending" : "Descending"}</b>
        </button>
      </div>

      {sorted.length === 0 ? (
        <div className="text-sm text-slate-500">
          No primes yet—start a block to begin testing.
        </div>
      ) : (
        <div className="space-y-3">
          {sorted.map((r) => {
            const g = gen[r.p];
            return (
              <div
                key={r.p}
                className="w-full rounded-xl border border-slate-200 bg-white p-4 flex items-center justify-between gap-4"
              >
                {/* Left: details */}
                <div className="min-w-0">
                  <div className="flex items-center gap-3">
                    <div className="text-lg text-black font-bold truncate">M{r.p}</div>
                    <div className="text-xs text-slate-500">
                      block {r.block_id}–{r.block_id + 1}M
                    </div>
                  </div>
                  <div className="mt-1 text-sm text-slate-700">
                    digits: <b>{r.digits.toLocaleString()}</b>
                  </div>
                  <div className="text-xs text-slate-500">
                    {r.finished_at
                      ? `finished at ${new Date(r.finished_at * 1000).toLocaleString()}`
                      : "finished time unknown"}
                  </div>
                  {r.engine_info ? (
                    <div className="text-xs text-slate-500">
                      engine {r.engine_info}
                    </div>
                  ) : null}
                </div>

                {/* Right: actions */}
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
                      rel="noopener noreferrer"
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
