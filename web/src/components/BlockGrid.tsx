// web/src/components/BlockGrid.tsx
"use client";
import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import type { BlockSummary } from "@/types";
import { setActiveBlock } from "@/lib/active";

export default function BlockGrid() {
  const [blocks, setBlocks] = useState<BlockSummary[]>([]);

  useEffect(() => {
    let alive = true,
      inflight = false;
    const load = async () => {
      if (inflight) return;
      inflight = true;
      try {
        const data = await apiFetch<BlockSummary[]>("/blocks?limit=6");
        if (alive) setBlocks(data);
      } finally {
        inflight = false;
      }
    };
    load();
    const t = setInterval(load, 1500);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, []);

  async function start(id: number) {
    await apiFetch(`/blocks/${id}/start?concurrency=1`, { method: "POST" });
    setActiveBlock(id); // triggers the runner via custom event
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3 max-w-5xl">
      {blocks.map((b) => {
        const pct = b.candidate_count
          ? Math.round((b.tested_count / b.candidate_count) * 100)
          : 0;
        return (
          <div
            key={b.id}
            className="rounded-xl bg-white border border-slate-200 p-4"
          >
            <div className="flex items-center justify-between">
              <div className="text-lg font-medium">{b.label}</div>
              <button
                onClick={() => start(b.id)}
                title="Start block"
                className="p-1.5 rounded-md border border-slate-200 hover:bg-slate-50"
              >
                {/* simple play icon */}
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                >
                  <path d="M8 5v14l11-7z" />
                </svg>
              </button>
            </div>
            <div className="text-xs text-slate-600">
              range [{b.start.toLocaleString()} …{" "}
              {(b.end_excl - 1).toLocaleString()} )
            </div>
            <div className="mt-2 h-2 rounded bg-slate-100 overflow-hidden">
              <div
                className="h-full bg-slate-900 transition-all"
                style={{ width: `${pct}%` }}
              />
            </div>
            <div className="mt-1 text-xs text-slate-500">
              coverage {pct}% • {b.tested_count}/{b.candidate_count}
            </div>
          </div>
        );
      })}
      {!blocks.length && <div className="text-sm text-slate-500">Loading…</div>}
    </div>
  );
}
