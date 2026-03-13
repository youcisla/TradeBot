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
    <html lang="en" className="dark">
      <body className="min-h-screen bg-terminal text-matrix font-mono antialiased">
        {children}
      </body>
    </html>
  );
}
