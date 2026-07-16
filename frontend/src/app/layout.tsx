import type { Metadata, Viewport } from "next";
import BackendWarmup from "@/components/BackendWarmup";
import "./globals.css";

export const metadata: Metadata = {
  title: "קרב קטגוריות",
  description: "משחק טריוויה תחרותי בזמן אמת — מי עונה אחרון, מנצח",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="he" dir="rtl">
      <body className="min-h-dvh bg-slate-100 font-sans text-slate-900 antialiased">
        <BackendWarmup />
        {children}
      </body>
    </html>
  );
}
