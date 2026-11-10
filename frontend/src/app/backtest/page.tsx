'use client';

import * as React from 'react';
import { bf } from '@/lib/api';
import { Badge } from '@/components/ui';
import { ProfitCurve } from '@/components/charts';

type Metrics = { total_bets: number; win_rate: number; roi: number; net_profit_ngn: number; avg_odds: number; max_drawdown_pct: number; longest_losing_streak: number; sharpe: number; calmar: number };
type BetRow = { home: string; away: string; date: string | null; market: string; model_p: number; odds: number; edge_pct: number; stake_ngn: number; status: string; profit_ngn: number };

export default function BacktestPage() {
  const [market, setMarket] = React.useState('O1.5');
  const [edge, setEdge] = React.useState('5');
  const [plan, setPlan] = React.useState('flat');
  const [sample, setSample] = React.useState('1500');
  const [busy, setBusy] = React.useState(false);
  const [metrics, setMetrics] = React.useState<Metrics | null>(null);
  const [curve, setCurve] = React.useState<number[]>([]);
  const [bets, setBets] = React.useState<BetRow[]>([]);
  const [srcNote, setSrcNote] = React.useState('');
  const [err, setErr] = React.useState('');

  const run = async () => {
    setBusy(true);
    setErr('');
    try {
      const res = await bf<{ metrics: Metrics; profit_curve: number[]; bets: BetRow[]; market_source?: string }>('backtest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ market, edge_threshold_pct: Number(edge), stake_plan: plan, sample: Number(sample) }),
      });
      setMetrics(res.metrics);
      setCurve(res.profit_curve ?? []);
      setBets(res.bets ?? []);
      setSrcNote(res.market_source ?? '');
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy(false);
    }
  };

  const input = 'h-10 rounded-lg border border-line bg-surface/70 px-3 text-sm text-ink outline-none focus:border-cyan';

  return (
    <div>
      <h1 className="text-xl font-bold text-ink">Backtest</h1>
      <p className="mt-0.5 text-sm text-muted">Event-driven, strict no-lookahead (features from matches strictly before kickoff).</p>

      <div className="mt-4 flex flex-wrap items-end gap-3 rounded-2xl border border-line bg-surface/40 p-4">
        <label className="text-sm text-muted">Market
          <select value={market} onChange={(e) => setMarket(e.target.value)} className={`${input} mt-1 block`}>
            <option value="O1.5">Over 1.5</option>
            <option value="O2.5">Over 2.5 · real line</option>
            <option value="BTTS">BTTS</option>
          </select>
        </label>
        <label className="text-sm text-muted">Edge ≥ %
          <input value={edge} onChange={(e) => setEdge(e.target.value)} className={`${input} mt-1 block w-20`} type="number" step="0.5" />
        </label>
        <label className="text-sm text-muted">Staking
          <select value={plan} onChange={(e) => setPlan(e.target.value)} className={`${input} mt-1 block`}>
            <option value="flat">Flat (1% cap)</option>
            <option value="kelly">Quarter-Kelly</option>
          </select>
        </label>
        <label className="text-sm text-muted">Sample
          <select value={sample} onChange={(e) => setSample(e.target.value)} className={`${input} mt-1 block`}>
            <option value="800">800</option>
            <option value="1500">1,500</option>
            <option value="2500">2,500</option>
          </select>
        </label>
        <button onClick={run} disabled={busy} className="h-10 rounded-lg bg-cyan px-5 font-semibold text-bg hover:shadow-glow disabled:opacity-50">
          {busy ? 'Running…' : 'Run backtest'}
        </button>
        {err && <span className="text-xs text-magenta">{err}</span>}
      </div>

      {metrics && (
        <>
          {srcNote && (
            <div className="mt-4 rounded-xl border border-amber/40 bg-amber/10 px-3 py-2 text-xs text-amber">
              ⚠ {srcNote}
            </div>
          )}
          <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Metric label="Total bets" value={metrics.total_bets} />
          <Metric label="Win rate" value={`${(metrics.win_rate * 100).toFixed(1)}%`} />
          <Metric label="ROI" value={`${(metrics.roi * 100).toFixed(1)}%`} tone={metrics.roi >= 0 ? 'green' : 'magenta'} />
          <Metric label="Net P&L" value={`₦${metrics.net_profit_ngn.toLocaleString('en-NG')}`} />
          <Metric label="Max drawdown" value={`${(metrics.max_drawdown_pct * 100).toFixed(1)}%`} />
          <Metric label="Longest loss streak" value={metrics.longest_losing_streak} />
          <Metric label="Sharpe" value={metrics.sharpe.toFixed(2)} />
          <Metric label="Calmar" value={metrics.calmar.toFixed(2)} />
        </div>
        </>
      )}

      {curve.length > 0 && (
        <div className="mt-5 rounded-2xl border border-line bg-surface/40 p-4">
          <div className="mb-2 text-sm text-muted">Paper bankroll curve (₦)</div>
          <ProfitCurve data={curve} />
        </div>
      )}

      {bets.length > 0 && (
        <div className="mt-5 overflow-x-auto rounded-2xl border border-line bg-surface/40 p-4">
          <div className="mb-2 text-sm text-muted">Simulated bets (first 100)</div>
          <table className="w-full">
            <thead>
              <tr className="text-left font-mono text-[11px] uppercase tracking-wider text-muted">
                <th className="py-1 pr-3">Fixture</th><th className="pr-3">Date</th><th className="pr-3">Market</th><th className="pr-3">p</th><th className="pr-3">Odds</th><th className="pr-3">Edge</th><th className="pr-3">Stake</th><th className="pr-3">Status</th><th>P&L</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {bets.map((b, i) => (
                <tr key={i} className="text-sm text-ink">
                  <td className="py-2 pr-3">{b.home} vs {b.away}</td>
                  <td className="pr-3 text-xs text-dim">{b.date ?? '—'}</td>
                  <td className="pr-3">{b.market}</td>
                  <td className="pr-3 font-mono">{(b.model_p * 100).toFixed(0)}%</td>
                  <td className="pr-3 font-mono">{b.odds.toFixed(2)}</td>
                  <td className="pr-3 font-mono text-cyan">+{b.edge_pct.toFixed(1)}%</td>
                  <td className="pr-3 font-mono">₦{b.stake_ngn}</td>
                  <td className="pr-3"><Badge tone={b.status === 'WON' ? 'green' : b.status === 'LOST' ? 'magenta' : 'dim'}>{b.status}</Badge></td>
                  <td className={`font-mono ${b.profit_ngn >= 0 ? 'text-emerald-400' : 'text-magenta'}`}>{b.profit_ngn >= 0 ? '+' : ''}{b.profit_ngn.toFixed(0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function Metric({ label, value, tone }: { label: string; value: React.ReactNode; tone?: 'green' | 'magenta' }) {
  return (
    <div className="glass rounded-2xl p-4">
      <div className="text-xs uppercase tracking-widest text-muted">{label}</div>
      <div className={`mt-1 font-mono text-2xl font-bold ${tone === 'green' ? 'text-emerald-400' : tone === 'magenta' ? 'text-magenta' : 'text-ink'}`}>{value}</div>
    </div>
  );
}
