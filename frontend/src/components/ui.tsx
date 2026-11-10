import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: Array<string | false | null | undefined>) {
  return twMerge(clsx(inputs));
}

export function Card({ title, children, action }: { title?: string; children: React.ReactNode; action?: React.ReactNode }) {
  return (
    <div className="glass rounded-2xl p-5">
      {title && (
        <div className="mb-3 flex items-center justify-between">
          <h3 className="font-semibold text-ink">{title}</h3>
          {action}
        </div>
      )}
      {children}
    </div>
  );
}

export function Stat({ label, value, hint }: { label: string; value: React.ReactNode; hint?: string }) {
  return (
    <div className="glass rounded-2xl p-5">
      <div className="text-xs uppercase tracking-widest text-muted">{label}</div>
      <div className="mt-1 font-mono text-2xl font-bold text-ink">{value}</div>
      {hint && <div className="mt-0.5 text-xs text-dim">{hint}</div>}
    </div>
  );
}

export function Badge({ children, tone = 'cyan' }: { children: React.ReactNode; tone?: 'cyan' | 'purple' | 'magenta' | 'amber' | 'green' | 'dim' }) {
  const map = {
    cyan: 'bg-cyan/15 text-cyan',
    purple: 'bg-purple/15 text-purple',
    magenta: 'bg-magenta/15 text-magenta',
    amber: 'bg-amber/15 text-amber',
    green: 'bg-emerald-500/15 text-emerald-400',
    dim: 'bg-white/5 text-muted',
  } as const;
  return <span className={cn('inline-flex items-center rounded-full px-2 py-0.5 font-mono text-[11px] font-semibold uppercase tracking-wider', map[tone])}>{children}</span>;
}

export function Th({ children, className }: { children: React.ReactNode; className?: string }) {
  return <th className={cn('px-3 py-2 text-left font-mono text-[11px] uppercase tracking-wider text-muted', className)}>{children}</th>;
}
export function Td({ children, className }: { children: React.ReactNode; className?: string }) {
  return <td className={cn('px-3 py-2 text-sm text-ink', className)}>{children}</td>;
}
