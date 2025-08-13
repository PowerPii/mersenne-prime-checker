// web/src/app/page.tsx
import Link from "next/link";
import type { PrimeRow } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE!;

async function fetchCount(): Promise<number> {
  const res = await fetch(`${API_BASE}/primes/count`, { cache: "no-store" });
  if (!res.ok) return 0;
  const j = await res.json();
  return j.count ?? 0;
}
async function fetchRecent(): Promise<PrimeRow[]> {
  const res = await fetch(`${API_BASE}/primes?limit=6`, { cache: "no-store" });
  if (!res.ok) return [];
  return res.json();
}

export default async function Home() {
  const [count, recent] = await Promise.all([fetchCount(), fetchRecent()]);
  return (
    <div>
      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-slate-50 to-white" />
        <div className="relative mx-auto max-w-6xl px-4 py-14">
          <h1 className="text-3xl md:text-4xl font-semibold tracking-tight">
            Local Mersenne search, verified.
          </h1>
          <p className="mt-2 text-slate-600">
            We’ve found <span className="font-bold">{count.toLocaleString()}</span> Mersenne primes so far. Launch new runs, watch live progress, and export full digits.
          </p>
          <div className="mt-6 flex gap-3">
            <Link href="/run" className="px-4 py-2 rounded-md bg-slate-900 text-white hover:bg-slate-800 text-sm">Start a run</Link>
            <Link href="/lists" className="px-4 py-2 rounded-md border border-slate-200 hover:bg-slate-50 text-sm">View all primes</Link>
          </div>
        </div>
      </section>

      {/* Biggest primes */}
      <section className="mx-auto max-w-6xl p-12">
        <h2 className="text-2xl font-bold mb-6">Current Biggest Prime</h2>
        {recent.length === 0 ? (
          <div className="text-sm text-slate-500">No primes yet. Kick off a block on the Run page.</div>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {recent.map(r => (
              <div key={r.p} className="rounded-xl border border-slate-200 bg-white p-4">
                <div className="flex items-center justify-between">
                  <div className="text-lg font-bold">M{r.p}</div>
                  <div className="text-xs text-slate-500">block {r.block_id}-{r.block_id+1}M</div>
                </div>
                <div className="text-sm">digits: <b>{r.digits.toLocaleString()}</b></div>
                <div className="text-xs text-slate-500 mt-1">
                  {r.finished_at ? new Date(r.finished_at * 1000).toLocaleString() : "—"}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
