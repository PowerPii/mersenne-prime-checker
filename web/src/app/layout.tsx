// web/src/app/layout.tsx  (server component)
import "./globals.css";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import FloatingRunnerHost from "@/components/FloatingRunnerHost";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-white text-slate-900">
        <Navbar />
        <main>{children}</main>
        <Footer />
        <FloatingRunnerHost /> {/* persistent bottom-right */}
      </body>
    </html>
  );
}
