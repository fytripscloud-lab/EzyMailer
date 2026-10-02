import Box from '@mui/material/Box';
import { neon } from '../../theme';

// Circular gauge of licence time remaining.
export default function ValidityRing({ daysLeft, totalDays, size = 168 }) {
  const r = 70;
  const c = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(1, daysLeft / totalDays));
  return (
    <Box sx={{ position: 'relative', width: size, height: size, flexShrink: 0 }}>
      <svg viewBox="0 0 160 160" width={size} height={size} role="img" aria-label={`${daysLeft} of ${totalDays} days remaining`}>
        <defs>
          <linearGradient id="ringGrad" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor={neon.cyan} />
            <stop offset="100%" stopColor={neon.violet} />
          </linearGradient>
        </defs>
        <circle cx="80" cy="80" r={r} fill="none" stroke="rgba(255,255,255,.06)" strokeWidth="12" />
        <circle
          cx="80" cy="80" r={r} fill="none" stroke="url(#ringGrad)" strokeWidth="12" strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={c * (1 - pct)} transform="rotate(-90 80 80)"
          style={{ filter: `drop-shadow(0 0 8px ${neon.cyan})`, transition: 'stroke-dashoffset 1s ease' }}
        />
      </svg>
      <Box sx={{ position: 'absolute', inset: 0, display: 'grid', placeItems: 'center', textAlign: 'center' }}>
        <Box>
          <Box sx={{ fontFamily: '"Space Grotesk"', fontWeight: 700, fontSize: size * 0.24, lineHeight: 1 }}>{daysLeft}</Box>
          <Box sx={{ fontFamily: '"JetBrains Mono", monospace', fontSize: 11, color: 'text.secondary', letterSpacing: '0.15em', mt: 0.5 }}>DAYS LEFT</Box>
        </Box>
      </Box>
    </Box>
  );
}
