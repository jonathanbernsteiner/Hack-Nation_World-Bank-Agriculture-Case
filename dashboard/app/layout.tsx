import type { Metadata } from "next";
import "leaflet/dist/leaflet.css";
import "./globals.css";
import AppShell from "@/components/AppShell";

export const metadata: Metadata = {
  title: "Coffee hotline dashboard",
  description: "Where registered coffee farmers live, what they are paid, and unusual patterns. Uganda, synthetic data labelled.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="bg-white antialiased">
        {/* hasSynthetic: all current data is synthetic; make dynamic once real data lands. */}
        <AppShell hasSynthetic>{children}</AppShell>
      </body>
    </html>
  );
}
