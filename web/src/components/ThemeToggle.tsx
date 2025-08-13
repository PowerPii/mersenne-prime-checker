"use client";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";

export default function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  if (!mounted) return null; // avoid hydration mismatch

  const isDark = resolvedTheme === "dark";
  return (
    <button
      onClick={() => setTheme(isDark ? "light" : "dark")}
      className="px-3 py-1.5 rounded-md text-sm bg-slate-200 dark:bg-slate-800"
    >
      {isDark ? "Light" : "Dark"}
    </button>
  );
}
