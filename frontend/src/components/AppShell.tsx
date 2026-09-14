import Link from "next/link";
import { BookOpen, History, PlusSquare } from "lucide-react";
import { ReactNode } from "react";
export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="app-shell">
      <header className="docket-rail">
        <Link href="/" className="wordmark">
          <BookOpen size={18} /> TradingAgents <span>Research Office</span>
        </Link>
        <nav aria-label="Docket navigation">
          <Link href="/">
            <PlusSquare size={16} /> New docket
          </Link>
          <Link href="/history">
            <History size={16} /> Index
          </Link>
        </nav>
        <span className="rail-note">Local analysis workspace</span>
      </header>
      <main>{children}</main>
    </div>
  );
}
