"use client";
import { useEffect, useRef, useState } from "react";
import { apiFetch, API_BASE } from "@/lib/api";
import { wsUrl } from "@/lib/ws";
import type {
  JobProgress,
  JobStatus,
  DigitsCreateResp,
  DigitsJob,
} from "@/types";

type Props = { initialP: number };

export default function Runner({ initialP }: Props) {
  const [p, setP] = useState(initialP);
  const [jobId, setJobId] = useState<string | null>(null);
  const [pct, setPct] = useState(0);
  const [digest, setDigest] = useState<string | null>(null);
  const [result, setResult] = useState<JobStatus | null>(null);
  const [digitsJob, setDigitsJob] = useState<string | null>(null);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(
    () => () => {
      wsRef.current?.close();
    },
    [],
  );

  async function start() {
    setJobId(null);
    setPct(0);
    setDigest(null);
    setResult(null);
    setDownloadUrl(null);
    setDigitsJob(null);
    const { id } = await apiFetch<{ id: string }>("/jobs", {
      method: "POST",
      body: JSON.stringify({ p }),
    });
    setJobId(id);
    const ws = new WebSocket(wsUrl(`/ws/jobs/${id}`));
    wsRef.current = ws;
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data as string) as JobProgress;
        setPct(msg.pct ?? 0);
        setDigest(msg.digest ?? null);
      } catch {}
    };
    ws.onclose = async () => {
      try {
        setResult(await apiFetch<JobStatus>(`/jobs/${id}`));
      } catch {}
    };
  }

  async function generateDigits() {
    const { id } = await apiFetch<DigitsCreateResp>("/digits", {
      method: "POST",
      body: JSON.stringify({ p }),
    });
    setDigitsJob(id);
    const poll = async () => {
      const j = await apiFetch<DigitsJob>(`/digits/${id}`);
      if (j.status === "done" && j.artifact) {
        setDownloadUrl(`${API_BASE}/digits/${id}/download`);
      } else {
        setTimeout(poll, 800);
      }
    };
    poll();
  }

  return (
    <div className="space-y-4">
      <div className="flex items-end gap-3">
        <label className="text-sm">
          Exponent p
          <input
            type="number"
            value={p}
            onChange={(e) => setP(parseInt(e.target.value || "0", 10))}
            className="ml-2 border border-slate-300 rounded px-2 py-1 w-40"
          />
        </label>
        <button
          onClick={start}
          className="px-4 py-2 rounded bg-slate-900 text-white hover:bg-slate-800"
        >
          Run LL
        </button>
      </div>

      <div className="w-full bg-slate-100 rounded h-3 overflow-hidden border border-slate-200">
        <div
          className="h-full bg-slate-900 transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="text-sm text-slate-700">
        {jobId ? (
          <>
            job: <code>{jobId}</code> • {pct}%
          </>
        ) : (
          "no job running"
        )}
        {digest && (
          <div className="mt-1 font-mono break-all text-xs">
            digest: {digest}
          </div>
        )}
      </div>

      {result && (
        <div className="text-sm bg-slate-50 border border-slate-200 rounded p-3">
          <div>
            p=<b>{result.result?.p ?? p}</b> →{" "}
            <b>{result.result?.is_prime ? "PRIME" : "composite"}</b>
          </div>
          {result.result && (
            <div className="text-xs text-slate-600">
              iters={result.result.iterations} • ns={result.result.ns_elapsed} •
              engine={result.result.engine_info}
            </div>
          )}
          {result.result?.is_prime && (
            <div className="mt-3 flex items-center gap-3">
              {!downloadUrl ? (
                <button
                  onClick={generateDigits}
                  className="px-3 py-1.5 rounded bg-emerald-600 text-white hover:bg-emerald-500"
                >
                  Generate digits
                </button>
              ) : (
                <a
                  href={downloadUrl}
                  className="px-3 py-1.5 rounded bg-emerald-600 text-white"
                  target="_blank"
                >
                  Download digits
                </a>
              )}
              {digitsJob && !downloadUrl && (
                <span className="text-xs text-slate-600">preparing…</span>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
