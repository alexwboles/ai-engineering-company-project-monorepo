import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { AuthShell } from "@/app/auth-shell";
import { NavClient } from "@/app/nav-client";
import { TelemetryProvider } from "@/app/telemetry-provider";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "HealthCore Backoffice",
  description: "Internal operations dashboard for HealthCore teams.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <header className="sticky top-0 z-30 border-b border-slate-200/70 bg-white/85 backdrop-blur">
          <nav className="mx-auto flex w-full max-w-6xl items-center justify-between px-4 py-3 sm:px-6 lg:px-8">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-600">HealthCore Backoffice</p>
            <NavClient />
          </nav>
        </header>
        <TelemetryProvider />
        <AuthShell>{children}</AuthShell>
      </body>
    </html>
  );
}
