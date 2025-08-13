// web/src/components/BlockDrawer.tsx
"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { apiFetch } from "@/lib/api";
import { wsUrl } from "@/lib/ws";
import type { BlockDetail, BlockWsMsg } from "@/types";
import Runner from "./Runner";

type Props = { blockId: number; label: string; onClose: () => void };

export default function BlockDrawer({ blockId, label, onClose }: Props) {
  const [detail, setDetail] = useState<BlockDetail | null>(null);
  const [tested, setTested] = useState<number | null>(null);
  const [total, setTotal] = useState<number | null>(null);
  const [selectedP, setSelectedP] = useState<number | null>(null);
  const [starting, setStarting] = useState(false);
  const [currentP, setCurrentP] = useState<number | null>(null); // ← NEW
  const [currentPct, setCurrentPct] = useState<number>(0); // ← NEW
  const [sortPrimeFirst, setSortPrimeFirst] = useState<boolean>(false); // ← NEW
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let alive = true;
    apiFetch<BlockDetail>(`/blocks/${blockId}`).then((d) => {
      if (!alive) return;
      setDetail(d);
      setTested(d.block.tested_count);
      setTotal(d.block.candidate_count);
      if (d.exponents.length) setSelectedP(d.exponents[0].p);
    });
    return () => {
      alive = false;
    };
  }, [blockId]);

  useEffect(() => {
    const ws = new WebSocket(wsUrl(`/ws/blocks/${blockId}`));
    wsRef.current = ws;
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data as string) as BlockWsMsg;
        if (msg.total != null) setTotal(msg.total);
        if (msg.tested != null) setTested(msg.tested);
        if (msg.p != null && msg.pct != null) {
          // ← per-exponent progress
          setCurrentP(msg.p);
          setCurrentPct(msg.pct);
        }
      } catch {}
    };
    return () => {
      ws.close();
    };
  }, [blockId]);

  const coveragePct = useMemo(() => {
    if (tested == null || total == null || total === 0) return 0;
    return Math.round((tested / total) * 100);
  }, [tested, total]);

  // simple client-side sort: prime rows first (1), then unknown (null), then non-prime (0)
  const expsSorted = useMemo(() => {
    const rows = detail?.exponents ?? [];
    if (!sortPrimeFirst) return rows.slice(0, 200);
    return rows.slice(0, 200).sort((a, b) => {
      const rank = (v: 0 | 1 | null) => (v === 1 ? 2 : v === null ? 1 : 0);
      const rdiff = rank(b.is_prime) - rank(a.is_prime);
      return rdiff || a.p - b.p;
    });
  }, [detail, sortPrimeFirst]);

  async function startBlock() {
    try {
      setStarting(true);
      await apiFetch(`/blocks/${blockId}/start?concurrency=1`, {
        method: "POST",
      });
    } finally {
      setStarting(false);
    }
  }

  return (
    <div
      className="fixed inset-0 bg-black/20 flex justify-end"
      onClick={onClose}
    >
      <div
        className="w-full max-w-3xl h-full bg-white border-l border-slate-200 p-6 overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-3">
          <div className="text-lg font-semibold">
            Block {label}{" "}
            <span className="text-sm text-slate-500">
              {detail
                ? `[ ${detail.block.start} … ${detail.block.end_excl} )`
                : ""}
            </span>
          </div>
          <button
            onClick={startBlock}
            disabled={starting}
            className="ml-auto px-3 py-1.5 rounded bg-slate-900 text-white hover:bg-slate-800 disabled:opacity-50"
          >
            {starting ? "Starting…" : "Start block"}
          </button>
          <button
            onClick={onClose}
            className="text-slate-600 hover:text-slate-900"
          >
            ✕
          </button>
        </div>

        {/* Overall progress */}
        <div className="mt-4 space-y-3">
          <div className="text-sm">
            Coverage: <b>{coveragePct}%</b>{" "}
            <span className="text-slate-500">
              ({tested ?? 0}/{total ?? 0} candidates)
            </span>
          </div>
          <div className="w-full bg-slate-100 rounded h-2 overflow-hidden border border-slate-200">
            <div
              className="h-full bg-slate-900 transition-all"
              style={{ width: `${coveragePct}%` }}
            />
          </div>
        </div>

        {/* Current exponent progress */}
        <div className="mt-4">
          <div className="text-sm">
            {currentP != null ? (
              <>
                Currently testing <b>p={currentP}</b> — <b>{currentPct}%</b>
              </>
            ) : (
              <span className="text-slate-500">No exponent running yet…</span>
            )}
          </div>
          <div className="mt-2 w-full bg-slate-100 rounded h-2 overflow-hidden border border-slate-200">
            <div
              className="h-full bg-emerald-600 transition-all"
              style={{ width: `${currentPct}%` }}
            />
          </div>
        </div>

        {/* Table + Runner */}
        <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <div className="flex items-center justify-between">
              <div className="text-sm font-medium mb-2">Exponents</div>
              <label className="text-xs mb-2 flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={sortPrimeFirst}
                  onChange={(e) => setSortPrimeFirst(e.target.checked)}
                />
                prime first
              </label>
            </div>
            <div className="border border-slate-200 rounded">
              <table className="w-full text-sm">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="text-left px-3 py-2">p</th>
                    <th className="text-left px-3 py-2">status</th>
                    <th
                      className="text-left px-3 py-2 cursor-pointer"
                      onClick={() => setSortPrimeFirst((s) => !s)}
                    >
                      prime? {sortPrimeFirst ? "↓" : ""}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {expsSorted.map((e) => (
                    <tr
                      key={e.p}
                      className={`border-t hover:bg-slate-50 cursor-pointer ${selectedP === e.p ? "bg-emerald-50" : ""}`}
                      onClick={() => setSelectedP(e.p)}
                    >
                      <td className="px-3 py-1.5 font-mono">{e.p}</td>
                      <td className="px-3 py-1.5">{e.status}</td>
                      <td className="px-3 py-1.5">
                        {e.is_prime == null ? "—" : e.is_prime ? "yes" : "no"}
                      </td>
                    </tr>
                  ))}
                  {!detail && (
                    <tr>
                      <td className="px-3 py-2 text-slate-500" colSpan={3}>
                        Loading…
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            <div className="mt-2 text-xs text-slate-500">
              Showing first 200.
            </div>
          </div>

          <div>
            <div className="text-sm font-medium mb-2">Runner</div>
            {selectedP != null ? (
              <Runner initialP={selectedP} />
            ) : (
              <div className="text-sm text-slate-500">Pick an exponent.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
