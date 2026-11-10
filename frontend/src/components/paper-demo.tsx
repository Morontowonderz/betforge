'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { bf } from '@/lib/api';

export function PaperDemo() {
  const router = useRouter();
  const [busy, setBusy] = React.useState(false);
  const act = async (kind: 'place' | 'won' | 'lost') => {
    setBusy(true);
    try {
      if (kind === 'place') {
        await bf('paper/place', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ key: `demo-${Date.now()}`, market: 'O1.5', odds: 2.0, p: 0.6 }) });
      } else {
        await bf('paper/settle', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ key: 'demo', won: kind === 'won' }) });
      }
      router.refresh();
    } catch (e) {
      console.error(e);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="flex flex-wrap gap-2">
      <button onClick={() => act('place')} disabled={busy} className="h-9 rounded-lg bg-cyan px-3 text-sm font-semibold text-bg disabled:opacity-50">Place paper bet</button>
      <button onClick={() => act('won')} disabled={busy} className="h-9 rounded-lg border border-emerald-500/50 px-3 text-sm text-emerald-400 disabled:opacity-50">Settle WON</button>
      <button onClick={() => act('lost')} disabled={busy} className="h-9 rounded-lg border border-magenta/50 px-3 text-sm text-magenta disabled:opacity-50">Settle LOST</button>
    </div>
  );
}
