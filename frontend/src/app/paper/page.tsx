import { bfServer } from '@/lib/api';
import { Badge, Card, Stat, Th, Td } from '@/components/ui';
import { BankrollCurve } from '@/components/charts';
import { PaperDemo } from '@/components/paper-demo';

export const dynamic = 'force-dynamic';

export default async function PaperPage() {
  let data: { balance_ngn: number; starting_ngn: number; profit_loss_ngn: number; auto_paper_trade: boolean; daily_loss_today: number; max_drawdown_pct: number; ledger: Array<{ signal_key: string; market: string; odds: number; stake_ngn: number; status: string; profit_ngn: number }>; curve: Array<{ ds: string; balance: number }> } | null = null;
  try {
    data = await bfServer('paper');
  } catch (e) {
    console.error(e);
  }
  return (
    <div>
      <h1 className="text-xl font-bold text-ink">Paper Trading</h1>
      <p className="mt-0.5 text-sm text-muted">₦ simulated bankroll · auto-paper-trade {data?.auto_paper_trade ? 'ON' : 'OFF'} · {data && <Badge tone="amber">stakes capped, daily loss stop</Badge>}</p>

      <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Balance" value={data ? `₦${data.balance_ngn.toLocaleString('en-NG')}` : '—'} />
        <Stat label="Starting" value={data ? `₦${data.starting_ngn.toLocaleString('en-NG')}` : '—'} />
        <Stat label="P&L" value={data ? `₦${data.profit_loss_ngn.toLocaleString('en-NG')}` : '—'} />
        <Stat label="Daily loss today" value={data ? `₦${data.daily_loss_today.toLocaleString('en-NG')}` : '—'} />
      </div>

      {data && data.curve.length > 0 && (
        <Card title="Bankroll curve">
          <BankrollCurve data={data.curve} />
        </Card>
      )}

      <div className="mt-4"><PaperDemo /></div>

      <Card title="Ledger" action={<span className="text-xs text-dim">paper only</span>}>
        <table className="w-full">
          <thead className="border-b border-white/10"><tr><Th>Signal</Th><Th>Market</Th><Th>Odds</Th><Th>Stake</Th><Th>Status</Th><Th>P&amp;L</Th></tr></thead>
          <tbody className="divide-y divide-white/5">
            {(data?.ledger ?? []).map((e, i) => (
              <tr key={i}>
                <Td>{e.signal_key}</Td>
                <Td><Badge tone="purple">{e.market}</Badge></Td>
                <Td className="font-mono">{e.odds}</Td>
                <Td className="font-mono">₦{e.stake_ngn.toLocaleString('en-NG')}</Td>
                <Td><Badge tone={e.status === 'WON' ? 'green' : 'magenta'}>{e.status}</Badge></Td>
                <Td className={`font-mono ${e.profit_ngn >= 0 ? 'text-emerald-400' : 'text-magenta'}`}>{e.profit_ngn >= 0 ? '+' : ''}{e.profit_ngn.toLocaleString('en-NG')}</Td>
              </tr>
            ))}
            {(data?.ledger ?? []).length === 0 && <tr><Td>No paper bets yet.</Td></tr>}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
