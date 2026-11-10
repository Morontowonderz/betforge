import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#080c14',
        surface: '#0d1424',
        panel: 'rgba(17, 26, 46, 0.72)',
        line: 'rgba(0, 245, 212, 0.18)',
        cyan: '#00f5d4',
        purple: '#a855f7',
        magenta: '#f72585',
        amber: '#ffb703',
        ink: '#e6f1ff',
        muted: '#8a9bb8',
        dim: '#5b6b8c',
      },
      fontFamily: {
        sans: ['var(--font-sans)', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['var(--font-mono)', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      backgroundImage: {
        'cyber-grid':
          'linear-gradient(rgba(0,245,212,0.06) 1px, transparent 1px), linear-gradient(90deg, rgba(0,245,212,0.06) 1px, transparent 1px)',
        'cyber-grad': 'linear-gradient(135deg, #00f5d4 0%, #a855f7 100%)',
      },
      boxShadow: {
        glow: '0 0 22px rgba(0,245,212,0.35)',
        'glow-purple': '0 0 22px rgba(168,85,247,0.35)',
      },
      animation: {
        'pulse-glow': 'pulseGlow 2.4s ease-in-out infinite',
        'typing-dot': 'typingDot 1.2s ease-in-out infinite',
      },
      keyframes: {
        pulseGlow: {
          '0%, 100%': { boxShadow: '0 0 12px rgba(0,245,212,0.3)' },
          '50%': { boxShadow: '0 0 28px rgba(0,245,212,0.65)' },
        },
        typingDot: {
          '0%, 60%, 100%': { opacity: '0.25', transform: 'translateY(0)' },
          '30%': { opacity: '1', transform: 'translateY(-3px)' },
        },
      },
    },
  },
  plugins: [],
};
export default config;
