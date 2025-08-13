// web/src/app/run/page.tsx
"use client";

import BlockGrid from "@/components/BlockGrid";
import FloatingRunner from "@/components/FloatingRunner";

export default function RunPage() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <h1 className="text-2xl font-semibold mb-4">Run search</h1>
      <p className="text-slate-600 mb-6">
        Start block runs, monitor coverage, and drill down into individual
        exponents.
      </p>
      <BlockGrid />
      <FloatingRunner />
    </div>
  );
}
