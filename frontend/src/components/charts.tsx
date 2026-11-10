'use client';

import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, BarChart, Bar, CartesianGrid } from 'recharts';

export function ProfitCurve({ data, height = 260 }: { data: number[]; height?: number }) {
  const rows = data.map((v, i) => ({ i, bankroll: Math.round(v) }));
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={rows} margin={{ top: 5, right: 10, bottom: 5, left: 5 }}>
        <CartesianGrid stroke="rgba(255,255,255,0.05)" />
        <XAxis dataKey="i" stroke="#64748b" fontSize={11} />
        <YAxis stroke="#64748b" fontSize={11} />
        <Tooltip contentStyle={{ background: '#0f1420', border: '1px solid #00f5d4', borderRadius: 8 }} />
        <Line type="monotone" dataKey="bankroll" stroke="#00f5d4" strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function BankrollCurve({ data }: { data: Array<{ ds: string; balance: number }> }) {
  const rows = data.map((r) => ({ ...r, balance: Math.round(r.balance) }));
  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={rows} margin={{ top: 5, right: 10, bottom: 5, left: 5 }}>
        <CartesianGrid stroke="rgba(255,255,255,0.05)" />
        <XAxis dataKey="ds" hide stroke="#64748b" />
        <YAxis stroke="#64748b" fontSize={11} />
        <Tooltip contentStyle={{ background: '#0f1420', border: '1px solid #a855f7', borderRadius: 8 }} />
        <Line type="monotone" dataKey="balance" stroke="#a855f7" strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function ResearchBar({ data }: { data: Array<[string, number]> }) {
  const rows = data.map(([bucket, count]) => ({ bucket, count }));
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={rows} margin={{ top: 5, right: 10, bottom: 5, left: 5 }}>
        <CartesianGrid stroke="rgba(255,255,255,0.05)" vertical={false} />
        <XAxis dataKey="bucket" stroke="#64748b" fontSize={10} />
        <YAxis stroke="#64748b" fontSize={11} />
        <Tooltip contentStyle={{ background: '#0f1420', border: '1px solid #00f5d4', borderRadius: 8 }} />
        <Bar dataKey="count" fill="#00f5d4" radius={[3, 3, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
