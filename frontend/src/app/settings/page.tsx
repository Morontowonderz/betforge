import { bfServer } from '@/lib/api';
import { Badge, Card } from '@/components/ui';

export const dynamic = 'force-dynamic';

export default async function SettingsPage() {
  let s: Record<string, unknown> | null = null;
  try {
    s = await bfServer('settings');
  } catch (e) {
    console.error(e);
  }
  return (
    <div>
      <h1 className="text-xl font-bold text-ink">Settings</h1>
      <p className="mt-0.5 text-sm text-muted">Responsible-use policy + model knobs. All limits are enforced at the backend.</p>

      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <Card title="Responsible-use hard caps">
          <div className="space-y-3 text-sm">
            <Row k="Paper bankroll" v={s ? `₦${(s.starting_bankroll_ngn as number).toLocaleString('en-NG')}` : '—'} />
            <Row k="Default stake cap" v={s ? `${(Number(s.stake_cap_frac) * 100).toFixed(0)}% of bankroll` : '—'} />
            <Row k="Hard max stake" v={s ? `${(Number(s.hard_max_stake_frac) * 100).toFixed(0)}%` : '—'} />
            <Row k="Daily loss cap" v={s ? `₦${(s.daily_loss_cap_ngn as number).toLocaleString('en-NG')}` : '—'} />
            <Row k="Stake plan" v={String(s?.stake_plan ?? 'flat')} />
            <Row k="Edge threshold" v={s ? `${s.edge_threshold_pct}%` : '—'} />
            <Row k="Auto paper trade" v={s ? (s.auto_paper_trade ? 'ON' : 'OFF') : '—'} />
            <Row k="Notice" v={String(s?.responsible_notice ?? '')} />
          </div>
          <div className="mt-4"><Badge tone="amber">No real-money path exists — paper only.</Badge></div>
        </Card>

        <Card title="Tuning (env-driven)">
          <p className="text-sm text-muted">
            Production knobs are read from <span className="font-mono text-cyan">BETFORGE_*</span> environment variables:
          </p>
          <ul className="mt-3 space-y-1 font-mono text-xs text-dim">
            <li>BETFORGE_BANKROLL_NGN (default 100000)</li>
            <li>BETFORGE_STAKE_CAP_FRAC (0.01)</li>
            <li>BETFORGE_HARD_MAX_STAKE_FRAC (0.05)</li>
            <li>BETFORGE_DAILY_LOSS_CAP_NGN (20000)</li>
            <li>BETFORGE_STAKE_PLAN (flat | kelly)</li>
            <li>BETFORGE_EDGE_THRESHOLD_PCT (5.0)</li>
            <li>BETFORGE_AUTO_PAPER_TRADE (1)</li>
          </ul>
          <p className="mt-3 text-xs text-dim">The backtest page lets you try stake plan / edge interactively; policy caps here are always enforced.</p>
        </Card>
      </div>
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex items-center justify-between border-b border-white/5 pb-2">
      <span className="text-muted">{k}</span>
      <span className="font-mono text-ink">{v}</span>
    </div>
  );
}
