import Link from 'next/link';

export default function HomePage() {
  return (
    <div>
      <section className="cyber-grid-bg border-b border-line">
        <div className="mx-auto max-w-6xl px-4 py-16">
          <span className="font-mono text-xs uppercase tracking-[0.3em] text-cyan">ShadowSpark · BetForge</span>
          <h1 className="mt-3 max-w-3xl text-4xl font-bold leading-tight text-white md:text-6xl">
            Football value analytics, <span className="cyber-text-grad">paper-traded.</span>
          </h1>
          <p className="mt-4 max-w-xl text-muted">
            Over 1.5 &amp; BTTS prediction, backtesting with strict no-lookahead, value-signal
            detection and a fully simulated ₦ bankroll. Paper trading only — never risk real money here.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link href="/overview" className="rounded-lg bg-cyan px-6 py-3 font-semibold text-bg hover:shadow-glow">Open dashboard</Link>
            <Link href="/backtest" className="rounded-lg border border-line px-6 py-3 text-ink hover:border-cyan hover:text-cyan">Run a backtest</Link>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-12">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[
            ['Predict', 'Poisson + Dixon-Coles strength model for O1.5 / BTTS, with an ML + ensemble layer.'],
            ['Backtest', 'Event-driven engine — features only from matches strictly before kickoff (no lookahead).'],
            ['Signals', 'Value detection: model p vs de-vigged market, edge threshold, capped ₦ stake.'],
            ['Paper trade', '₦100k simulated bankroll, flat or quarter-Kelly stakes, hard caps, daily loss stop.'],
          ].map(([t, d]) => (
            <div key={t as string} className="glass rounded-2xl p-5">
              <div className="font-semibold text-ink">{t}</div>
              <p className="mt-1 text-sm text-muted">{d}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
