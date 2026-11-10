import { bfServer } from '@/lib/api';
import { Badge, Card, Th, Td } from '@/components/ui';

export const dynamic = 'force-dynamic';

type Sig = { fixture: string; market: string; model_p: number; implied_p: number; odds: number; edge_pct: number; stake_ngn: number; confidence: string; status: string };

export default async function SignalsPage() {
  let signals: Sig[] = [];
  try {
    signals = (await bfServer<{ signals: Sig[] }>('signals')).signals;
  } catch (e) {
    console.error(e);
  }
  const confTone: Record<string, 'green' | 'cyan' | 'dim'> = { HIGH: 'green', MEDIUM: 'cyan', LOW: 'dim' };
  return (
    <div>
      <h1 className="text-xl font-bold text-ink">Signals</h1>
      <p className="mt-0.5 text-sm text-muted">Value signals where model p &gt; de-vigged market implied (+ stake rec, capped).</p>
      <Card>
        <table className="w-full">
          <thead className="border-b border-white/10">
            <tr><Th>Fixture</Th><Th>Market</Th><Th>Model p</Th><Th>Implied p</Th><Th>Odds</Th><Th>Edge</Th><Th>Stake rec</Th><Th>Confidence</Th></tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {signals.map((s, i) => (
              <tr key={i}>
                <Td>{s.fixture}</Td>
                <Td><Badge tone="purple">{s.market}</Badge></Td>
                <Td className="font-mono">{(s.model_p * 100).toFixed(1)}%</Td>
                <Td className="font-mono">{(s.implied_p * 100).toFixed(1)}%</Td>
                <Td className="font-mono">{s.odds.toFixed(2)}</Td>
                <Td><Badge tone={s.edge_pct >= 10 ? 'green' : 'cyan'}>+{s.edge_pct.toFixed(1)}%</Badge></Td>
                <Td className="font-mono">₦{s.stake_ngn.toLocaleString('en-NG', { maximumFractionDigits: 0 })}</Td>
                <Td><Badge tone={confTone[s.confidence] ?? 'dim'}>{s.confidence}</Badge></Td>
              </tr>
            ))}
            {signals.length === 0 && <tr><Td>No signals above the edge threshold right now.</Td></tr>}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
