// web/src/components/Navbar.tsx
"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const tabs = [
  { href: "/", label: "Home" },
  { href: "/run", label: "Run" },
  { href: "/lists", label: "Lists" },
];

export default function Navbar() {
  const path = usePathname();
  return (
    <header className="sticky top-0 z-40 bg-white/80 backdrop-blur border-b border-slate-200">
      <div className="mx-auto max-w-6xl px-4 h-14 flex items-center justify-between">
        <Link href="/" className="font-semibold tracking-tight">Mersenne Lab</Link>
        <nav className="flex items-center gap-1">
          {tabs.map(t => {
            const active = path === t.href;
            return (
              <Link
                key={t.href}
                href={t.href}
                className={`px-3 py-1.5 rounded-md text-sm ${active
                  ? "bg-slate-900 text-white"
                  : "text-slate-700 hover:bg-slate-100"}`}
              >
                {t.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
