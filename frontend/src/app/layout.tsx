import type { Metadata } from "next";
import "./globals.css";
import { AppShell } from "@/components/AppShell";
export const metadata: Metadata = {
  title: "TradingAgents Research Office",
  description: "Local browser workflow for TradingAgents",
};
export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
