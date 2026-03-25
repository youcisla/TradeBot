import type { Metadata } from "next";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { redirect } from "next/navigation";
import "./globals.css";

export const metadata: Metadata = {
  title: "Trading Bot",
  description: "Real-time trading bot dashboard",
};

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body style={{
        minHeight: "100vh",
        background: "#080808",
        color: "#00ff88",
        fontFamily: "'JetBrains Mono', monospace",
        margin: 0,
        padding: 0,
      }}>
        {children}
      </body>
    </html>
  );
}
