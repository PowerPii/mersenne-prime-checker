// web/src/components/FloatingRunner.tsx
"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { apiFetch } from "@/lib/api";
import { wsUrl } from "@/lib/ws";
import { getActiveBlock, clearActiveBlock, ACTIVE_EVENT } from "@/lib/active";
import type { BlockWsMsg } from "@/types";

export default function FloatingRunner() {
  const [blockId, setBlockId] = useState<number | null>(null);
  const [tested, setTested] = useState<number | null>(null);
  const [total, setTotal] = useState<number | null>(null);
  const [p, setP] = useState<number | null>(null);
  const [pctP, setPctP] = useState<number>(0);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const refresh = () => setBlockId(getActiveBlock());
    refresh();
    window.addEventListener(ACTIVE_EVENT, refresh as EventListener);
    return () =>
      window.removeEventListener(ACTIVE_EVENT, refresh as EventListener);
  }, []);

  useEffect(() => {
    if (blockId == null) return; // ← allow 0
    const ws = new WebSocket(wsUrl(`/ws/blocks/${blockId}`));
    wsRef.current = ws;
    ws.onmessage = (ev) => {
      try {
        const m = JSON.parse(ev.data as string) as BlockWsMsg;
        if (m.total != null) setTotal(m.total);
        if (m.tested != null) setTested(m.tested);
        if (m.p != null && m.pct != null) {
          setP(m.p);
          setPctP(m.pct);
        }
        if (m.done) handleHide();
      } catch {}
    };
    return () => ws.close();
  }, [blockId]);

  function handleHide() {
    clearActiveBlock();
    setBlockId(null);
    setTested(null);
    setTotal(null);
    setP(null);
    setPctP(0);
  }

  async function stop() {
    if (blockId == null) return; // ← allow 0
    await apiFetch(`/blocks/${blockId}/stop`, { method: "POST" });
    handleHide();
  }

  const cov = useMemo(() => {
    if (total == null || total === 0) return 0; // ← don’t treat tested=0 as “no data”
    if (tested == null) return 0;
    return Math.min(100, Math.round((tested / total) * 100));
  }, [tested, total]);

  if (blockId == null) return null; // ← allow 0

  return (
    <div className="fixed bottom-4 right-4 w-80 rounded-xl bg-white border border-slate-200 shadow-xl p-4">
      <div className="flex items-center justify-between">
        <div className="font-medium">
          Block {blockId}-{blockId + 1}M Status
        </div>
        <button
          onClick={stop}
          className="px-2 py-1 text-xs rounded bg-rose-600 text-white hover:bg-rose-500"
        >
          Stop
        </button>
      </div>
      <div className="mt-2 text-xs text-slate-600">
        Coverage: <b>{cov}%</b>{" "}
        {tested != null && total != null ? `(${tested}/${total})` : ""}
      </div>
      <div className="h-2 bg-slate-100 rounded overflow-hidden border border-slate-200 mt-1">
        <div className="h-full bg-slate-900" style={{ width: `${cov}%` }} />
      </div>
      <div className="mt-3 text-xs">
        {p != null ? (
          <>
            Currently testing: <b>M{p}</b> — <b>{pctP}%</b>
          </>
        ) : (
          <span className="text-slate-500">Waiting…</span>
        )}
      </div>
      <div className="mt-2 h-2 bg-slate-100 rounded overflow-hidden border border-slate-200">
        <div className="h-full bg-emerald-600" style={{ width: `${pctP}%` }} />
      </div>
      <div className="mt-3 flex justify-end">
        <button
          onClick={handleHide}
          className="text-xs text-slate-500 hover:text-slate-700"
        >
          Hide
        </button>
      </div>
    </div>
  );
}
