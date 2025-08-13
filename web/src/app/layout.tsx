import "./globals.css";
import Providers from "./providers";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import FloatingRunnerHost from "@/components/FloatingRunnerHost";

export const metadata = {
  title: "Mersenne Lab",
  description: "Local-first Mersenne prime checker",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen bg-slate-50 text-slate-900 antialiased dark:bg-slate-950 dark:text-slate-100">
        <Providers>
          <Navbar />
          <main className="mx-auto max-w-6xl px-4 py-6">{children}</main>
          <Footer />
          <FloatingRunnerHost />
        </Providers>
      </body>
    </html>
  );
}
