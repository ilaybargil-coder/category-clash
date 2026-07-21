import type { Metadata, Viewport } from "next";
import { Rubik } from "next/font/google";
import BackendWarmup from "@/components/BackendWarmup";
import OnboardingTutorial from "@/components/OnboardingTutorial";
import "./globals.css";

const rubik = Rubik({
  subsets: ["hebrew", "latin"],
  weight: ["400", "500", "700", "900"],
  variable: "--font-rubik",
  display: "swap",
});

export const metadata: Metadata = {
  title: "קרב קטגוריות",
  description: "משחק טריוויה תחרותי בזמן אמת — מי עונה אחרון, מנצח",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  interactiveWidget: "resizes-content",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="he" dir="rtl">
      <body className={`${rubik.variable} min-h-dvh bg-[#050a10] text-slate-100 antialiased`}>
        <BackendWarmup />
        {children}
        <OnboardingTutorial />
      </body>
    </html>
  );
}
