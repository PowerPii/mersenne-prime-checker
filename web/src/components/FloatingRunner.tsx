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
  const [wsErr, setWsErr] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const refresh = () => setBlockId(getActiveBlock());
    refresh();
    window.addEventListener(ACTIVE_EVENT, refresh as EventListener);
    return () =>
      window.removeEventListener(ACTIVE_EVENT, refresh as EventListener);
  }, []);

  useEffect(() => {
    if (blockId == null) return; // allow 0 as a valid id

    const url = wsUrl(`/ws/blocks/${blockId}`);
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log("[WS] open", url);
    };

    ws.onmessage = (ev) => {
      try {
        const m = JSON.parse(ev.data as string) as BlockWsMsg;
        if (m.total != null) setTotal(m.total);
        if (m.tested != null) setTested(m.tested);
        if (m.p != null && m.pct != null) {
          setP(m.p);
          setPctP(m.pct);
        }
        if (m.done) handleHide(); // this triggers cleanup → close(1000) below
      } catch (e) {
        console.warn("[WS] bad message", e, ev.data);
      }
    };

    ws.onerror = (ev) => {
      console.error("[WS] error", ev);
    };

    ws.onclose = (ev) => {
      console.warn("[WS] close", {
        code: ev.code,
        reason: ev.reason,
        clean: ev.wasClean,
      });
    };

    // IMPORTANT: close with an explicit normal code so the browser doesn't show 1006
    return () => {
      try {
        ws.close(1000, "component cleanup");
      } catch {}
    };
  }, [blockId]);

  function handleHide() {
    clearActiveBlock();
    setBlockId(null);
    setTested(null);
    setTotal(null);
    setP(null);
    setPctP(0);
    // close socket explicitly
    if (wsRef.current) {
      try {
        wsRef.current.close();
      } catch {}
      wsRef.current = null;
    }
  }

  async function stop() {
    if (blockId == null) return;
    await apiFetch(`/blocks/${blockId}/stop`, { method: "POST" });
    handleHide();
  }

  const cov = useMemo(() => {
    if (total == null || total === 0) return 0;
    if (tested == null) return 0;
    return Math.min(100, Math.round((tested / total) * 100));
  }, [tested, total]);

  if (blockId == null) return null;

  return (
    <div className="fixed bottom-4 right-4 w-80 rounded-xl bg-white dark:bg-black border border-slate-200 dark:border-slate-800 shadow-xl p-4">
      <div className="flex items-center justify-between">
        <div className="font-medium">
          Block {blockId}-{blockId + 1}M Status
        </div>
        <button
          onClick={stop}
          className="px-2 py-1 text-xs rounded bg-rose-500 text-white hover:bg-rose-600"
        >
          Stop
        </button>
      </div>

      {wsErr && <div className="mt-2 text-xs text-rose-600">{wsErr}</div>}

      <div className="mt-2 text-xs text-slate-500">
        Coverage: <b>{cov}%</b>{" "}
        {tested != null && total != null ? `(${tested}/${total})` : ""}
      </div>
      <div className="h-2 bg-slate-100 dark:bg-slate-900 rounded overflow-hidden border border-slate-200 dark:border-slate-800 mt-1">
        <div
          className="h-full bg-slate-900 dark:bg-slate-100"
          style={{ width: `${cov}%` }}
        />
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
      <div className="mt-2 h-2 bg-slate-100 dark:bg-slate-900 rounded overflow-hidden border border-slate-200 dark:border-slate-800">
        <div
          className="h-full bg-emerald-600 dark:bg-emerald-400"
          style={{ width: `${pctP}%` }}
        />
      </div>
      <div className="mt-3 flex justify-end">
        <button
          onClick={handleHide}
          className="text-xs text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
        >
          Hide
        </button>
      </div>
    </div>
  );
}
