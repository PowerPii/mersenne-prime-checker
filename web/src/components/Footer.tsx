// web/src/components/Footer.tsx
export default function Footer() {
  return (
    <footer className="mt-16 border-t border-slate-200 dark:border-slate-800">
      <div className="mx-auto max-w-6xl px-4 py-8 text-sm text-slate-500">
        <div className="flex items-center justify-between">
          <div>© {new Date().getFullYear()} Mersenne Lab</div>
          <div>Built with GMP · FastAPI · Next.js</div>
        </div>
      </div>
    </footer>
  );
}
