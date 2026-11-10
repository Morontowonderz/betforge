import { bfServer } from '@/lib/api';
import { Badge, Card, Stat } from '@/components/ui';
import { ResearchBar } from '@/components/charts';

export const dynamic = 'force-dynamic';

export default async function ResearchPage() {
  let report: Record<string, unknown> | null = null;
  let dist: Record<string, number> = {};
  try {
    const data = await bfServer<{ report: Record<string, unknown>; goal_minute_distribution: Record<string, number> }>('research/minute7');
    report = data.report;
    dist = data.goal_minute_distribution;
  } catch (e) {
    console.error(e);
  }
  const rows = Object.entries(dist).sort((a, b) => Number(a[0].split('-')[0]) - Number(b[0].split('-')[0]));

  const conclTone: Record<string, 'green' | 'amber' | 'dim'> = { SUPPORTED: 'green', 'SUPPORTED (simulated)': 'green', INCONCLUSIVE: 'amber', 'NOT SUPPORTED': 'dim' };

  return (
    <div>
      <h1 className="text-xl font-bold text-ink">Minute-7 Research</h1>
      <p className="mt-0.5 text-sm text-muted">Hypothesis, tested on mock live data ({report?.sample as number ?? 0} simulated matches). Not real-market evidence.</p>

      <Card title="Hypothesis under test">
        <p className="text-sm text-ink">
          <b>H1:</b> Matches with at least one goal by minute 7 are more likely to finish
          Over 1.5 than matches without an early goal. <b>Null:</b> no difference in the
          Over-1.5 outcome probability between the early-goal and no-early-goal groups.
        </p>
        <p className="mt-2 text-xs text-dim">Data: minute-by-minute mock generator from Poisson goal rates with realistic goal minutes.</p>
      </Card>

      <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Conclusion" value={report ? <Badge tone={conclTone[String(report.conclusion)] ?? 'dim'}>{String(report.conclusion)}</Badge> : '—'} />
        <Stat label="p-value" value={report ? String(report.p_value) : '—'} hint="two-proportion z-test" />
        <Stat label="Effect size" value={report ? String(report.effect_size) : '—'} hint="early minus no-early" />
        <Stat label="95% CI" value={report ? `${((report.ci_95 as [number, number] | undefined)?.[0]) ?? ''}…${((report.ci_95 as [number, number] | undefined)?.[1]) ?? ''}` : '—'} />
      </div>

      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <Card title="Over-1.5 finish rate by group">
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div><Badge tone="green">Early goal (≤7′)</Badge><div className="mt-1 font-mono text-2xl text-ink">{report ? (report.over15_early_pct as number).toFixed(1) : '—'}%</div></div>
            <div><Badge tone="dim">No early goal</Badge><div className="mt-1 font-mono text-2xl text-ink">{report ? (report.over15_no_early_pct as number).toFixed(1) : '—'}%</div></div>
          </div>
        </Card>
        <Card title="Goal-minute distribution (all goals)">
          <ResearchBar data={rows} />
        </Card>
      </div>

      <p className="mt-3 text-xs text-dim">simulated: {report?.simulated ? 'true' : '—'} · This is research-grade mock evidence; if a follow-up were to add an &ldquo;experimental&rdquo; tactic it would be stake-capped at 0.5% of bankroll and clearly labelled.</p>
    </div>
  );
}
