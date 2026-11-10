import type { Metadata } from 'next';
import Link from 'next/link';
import '@/styles/globals.css';

export const metadata: Metadata = {
  title: 'BETFORGE — Paper-Trading Football Analytics',
  description: 'Football prediction + backtesting engine. Paper trading only — not financial advice.',
};

const NAV: Array<[string, string]> = [
  ['/overview', 'Overview'],
  ['/matches', 'Matches'],
  ['/signals', 'Signals'],
  ['/backtest', 'Backtest'],
  ['/paper', 'Paper'],
  ['/research', 'Research'],
  ['/settings', 'Settings'],
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet" />
      </head>
      <body className="flex min-h-screen flex-col">
        <div className="border-b border-amber/40 bg-amber/10 px-3 py-1.5 text-center font-mono text-xs font-semibold text-amber">
          ⚠ Paper Trading Mode — Not Financial Advice. No real-money bets are placed or enabled.
        </div>
        <header className="sticky top-0 z-30 border-b border-line bg-bg/85 backdrop-blur-md">
          <div className="mx-auto flex max-w-6xl items-center gap-5 px-4 py-3">
            <Link href="/" className="font-mono text-lg font-bold cyber-text-grad">ss//betforge</Link>
            <nav className="ml-auto flex flex-wrap items-center gap-1">
              {NAV.map(([href, label]) => (
                <Link key={href} href={href} className="rounded-lg px-2.5 py-1.5 text-sm text-muted hover:bg-white/5 hover:text-cyan">{label}</Link>
              ))}
            </nav>
          </div>
        </header>
        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">{children}</main>
        <footer className="border-t border-line py-4">
          <div className="mx-auto max-w-6xl px-4 text-center text-xs text-dim">
            BETFORGE is a research &amp; paper-trading tool. It does not place real bets and is not financial advice.
            Stake limits are configurable (default 1% of paper bankroll, hard max 5%); a daily loss cap is enforced. Gambling can be harmful — only ever risk what you can afford to lose, and this tool risks nothing real.
          </div>
        </footer>
      </body>
    </html>
  );
}
