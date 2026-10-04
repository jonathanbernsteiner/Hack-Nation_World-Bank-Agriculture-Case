import type { Metadata } from "next";
import { DM_Sans, JetBrains_Mono } from "next/font/google";
import "leaflet/dist/leaflet.css";
import "./globals.css";
import AppShell from "@/components/AppShell";

const fontSans = DM_Sans({ subsets: ["latin"], variable: "--font-sans", display: "swap" });
const fontMono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono", display: "swap" });

export const metadata: Metadata = {
  title: "Coffee hotline dashboard",
  description: "Where registered coffee farmers live, what they are paid, and unusual patterns. Uganda.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${fontSans.variable} ${fontMono.variable}`}>
      <body className="bg-white antialiased">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
