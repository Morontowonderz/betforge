import { bfServer } from '@/lib/api';
import { Badge, Card, Th, Td } from '@/components/ui';

export const dynamic = 'force-dynamic';

type Row = {
  fixture: string; date: string | null;
  odds: { home: number | null; draw: number | null; away: number | null };
  model: { p_over15: number; p_btts: number };
  edge: { o15_pct: number; btts_pct: number };
};

export default async function MatchesPage() {
  let matches: Row[] = [];
  try {
    matches = (await bfServer<{ matches: Row[] }>('matches')).matches;
  } catch (e) {
    console.error(e);
  }
  const edgeTone = (e: number) => (e >= 5 ? ('green' as const) : e >= 2 ? ('cyan' as const) : ('dim' as const));
  return (
    <div>
      <h1 className="text-xl font-bold text-ink">Matches</h1>
      <Card>
        <table className="w-full">
          <thead className="border-b border-white/10">
            <tr><Th>Fixture</Th><Th>Kickoff</Th><Th>Odds 1×2</Th><Th>P(O1.5)</Th><Th>P(BTTS)</Th><Th>Edge O1.5</Th><Th>Edge BTTS</Th></tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {matches.map((m, i) => (
              <tr key={i}>
                <Td>{m.fixture}</Td>
                <Td className="text-xs text-dim">{m.date ?? '—'}</Td>
                <Td className="font-mono text-xs">{m.odds?.home ?? '-'} / {m.odds?.draw ?? '-'} / {m.odds?.away ?? '-'}</Td>
                <Td className="font-mono">{(m.model?.p_over15 * 100).toFixed(0)}%</Td>
                <Td className="font-mono">{(m.model?.p_btts * 100).toFixed(0)}%</Td>
                <Td><Badge tone={edgeTone(m.edge.o15_pct)}>{m.edge.o15_pct >= 0 ? '+' : ''}{m.edge.o15_pct.toFixed(1)}%</Badge></Td>
                <Td><Badge tone={edgeTone(m.edge.btts_pct)}>{m.edge.btts_pct >= 0 ? '+' : ''}{m.edge.btts_pct.toFixed(1)}%</Badge></Td>
              </tr>
            ))}
            {matches.length === 0 && (
              <tr><Td>No matches data (is the FastAPI backend running on :8000 and seeded?)</Td></tr>
            )}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
