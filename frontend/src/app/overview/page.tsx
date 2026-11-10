import { bfServer } from '@/lib/api';
import { Card, Stat, Badge } from '@/components/ui';

export const dynamic = 'force-dynamic';

export default async function OverviewPage() {
  let paper: { balance_ngn: number; starting_ngn: number; profit_loss_ngn: number; ledger: unknown[]; max_drawdown_pct: number } | null = null;
  let signals = { count: 0 };
  let acc = { brier_over15: 0, brier_base_rate: 0, honest_note: '' };
  try {
    paper = await bfServer('paper');
    signals = await bfServer('signals');
    acc = await bfServer('accuracy');
  } catch (e) {
    console.error('backend unreachable:', e);
  }

  const roi = paper && paper.starting_ngn > 0 ? (paper.profit_loss_ngn / paper.starting_ngn) * 100 : 0;

  return (
    <div>
      <h1 className="text-xl font-bold text-ink">Overview</h1>
      <p className="mt-0.5 text-sm text-muted">Paper-only dashboard · {signals.count} active value signals.</p>

      <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Signals today" value={signals.count} hint={signals.count ? 'with edge ≥ threshold' : 'none above threshold'} />
        <Stat label="Paper bankroll" value={paper ? `₦${paper.balance_ngn.toLocaleString('en-NG')}` : '—'} hint="paper money only" />
        <Stat label="Paper P&L" value={paper ? `₦${paper.profit_loss_ngn.toLocaleString('en-NG')}` : '—'} hint={`ROI ${roi.toFixed(1)}%`} />
        <Stat label="Max drawdown" value={paper ? `${(paper.max_drawdown_pct * 100).toFixed(1)}%` : '—'} hint="paper ledger" />
      </div>

      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <Card title="Model calibration (honest)">
          <div className="font-mono text-3xl font-bold text-cyan">Brier {acc.brier_over15 ?? '—'}</div>
          <p className="mt-1 text-sm text-muted">vs base rate {acc.brier_base_rate ?? '—'} (O1.5, pooled).</p>
          <p className="mt-2 text-xs text-dim">{acc.honest_note}</p>
          <div className="mt-2"><Badge tone="amber">Not financial advice</Badge></div>
        </Card>
        <Card title="Quick actions">
          <div className="grid gap-2">
            <a href="/backtest" className="rounded-lg border border-line px-3 py-2 text-sm text-ink hover:border-cyan hover:text-cyan">Run a backtest</a>
            <a href="/research" className="rounded-lg border border-line px-3 py-2 text-sm text-ink hover:border-cyan hover:text-cyan">Minute-7 research</a>
            <a href="/settings" className="rounded-lg border border-line px-3 py-2 text-sm text-ink hover:border-cyan hover:text-cyan">Responsible-use limits</a>
          </div>
        </Card>
      </div>
    </div>
  );
}
