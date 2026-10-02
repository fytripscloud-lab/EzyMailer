import { useEffect, useState } from 'react';
import Box from '@mui/material/Box';
import { alpha } from '@mui/material/styles';
import { neon } from '../theme';

const TOTAL = 240;
const windows = ['Window 01', 'Window 02', 'Window 03', 'Window 04', 'Window 05'];
const names = ['ava', 'liam', 'noah', 'mia', 'zoe', 'ethan', 'ivy', 'leo', 'aria', 'kai', 'nora', 'eli'];
const mono = '"JetBrains Mono", monospace';

function makeLine(i) {
  const name = names[i % names.length];
  const win = (i % windows.length) + 1;
  const retry = i % 11 === 7;
  return {
    id: i,
    win: `W0${win}`,
    to: `${name}${(i * 37) % 900 + 100}@example.com`,
    status: retry ? 'RETRY' : 'SENT',
  };
}

// A purely visual, self-animating replica of the campaign dashboard.
export default function AppMockup() {
  const [tick, setTick] = useState(18);

  useEffect(() => {
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return undefined;
    const id = setInterval(() => setTick((t) => (t >= TOTAL ? 18 : t + 1)), 650);
    return () => clearInterval(id);
  }, []);

  const sent = tick;
  const pct = Math.min(100, (tick / TOTAL) * 100);
  const lines = Array.from({ length: 6 }, (_, k) => makeLine(tick - k));

  return (
    <Box
      role="img"
      aria-label="Preview of the EzyMailer campaign dashboard sending across five browser windows"
      sx={{
        position: 'relative',
        borderRadius: 4,
        p: '1px',
        background: `linear-gradient(140deg, ${alpha(neon.cyan, 0.7)}, ${alpha(neon.violet, 0.4)} 40%, ${alpha(neon.blue, 0.1)} 70%, ${alpha(neon.cyan, 0.5)})`,
        boxShadow: `0 40px 120px -30px ${alpha(neon.cyan, 0.45)}, 0 0 0 1px ${alpha('#fff', 0.02)}`,
        animation: 'floatY 8s ease-in-out infinite',
      }}
    >
      <Box sx={{ borderRadius: 'inherit', bgcolor: '#070B16', overflow: 'hidden', position: 'relative' }}>
        {/* scan line */}
        <Box sx={{ position: 'absolute', left: 0, right: 0, height: 80, background: `linear-gradient(180deg, transparent, ${alpha(neon.cyan, 0.07)}, transparent)`, animation: 'scan 5s linear infinite', pointerEvents: 'none', zIndex: 2 }} />

        {/* title bar */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, px: 2, py: 1.25, borderBottom: `1px solid ${neon.line}`, bgcolor: '#0A0F1E' }}>
          {['#FF5F57', '#FEBC2E', '#28C840'].map((c) => (
            <Box key={c} sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: c, opacity: 0.85 }} />
          ))}
          <Box sx={{ ml: 1.5, fontFamily: mono, fontSize: 11, color: 'text.secondary' }}>EzyMailer — Campaign</Box>
          <Box sx={{ ml: 'auto', display: 'flex', alignItems: 'center', gap: 0.75, fontFamily: mono, fontSize: 10, color: neon.green }}>
            <Box sx={{ width: 6, height: 6, borderRadius: '50%', bgcolor: neon.green, boxShadow: `0 0 8px ${neon.green}`, animation: 'pulseGlow 1.4s infinite' }} />
            LIVE
          </Box>
        </Box>

        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '170px 1fr' } }}>
          {/* sidebar: active sessions */}
          <Box sx={{ display: { xs: 'none', sm: 'block' }, borderRight: `1px solid ${neon.line}`, p: 1.5, bgcolor: '#080D1A' }}>
            <Box sx={{ fontFamily: mono, fontSize: 9.5, letterSpacing: '0.15em', color: 'text.secondary', mb: 1 }}>ACTIVE SESSIONS</Box>
            {windows.map((w, i) => {
              const active = tick % windows.length === i;
              return (
                <Box
                  key={w}
                  sx={{
                    display: 'flex', alignItems: 'center', gap: 1, px: 1, py: 0.8, mb: 0.5, borderRadius: 1.5,
                    fontSize: 12, color: active ? 'text.primary' : 'text.secondary',
                    bgcolor: active ? alpha(neon.cyan, 0.1) : 'transparent',
                    border: `1px solid ${active ? alpha(neon.cyan, 0.35) : 'transparent'}`,
                    transition: 'all .3s',
                  }}
                >
                  <Box sx={{ width: 7, height: 7, borderRadius: '50%', bgcolor: active ? neon.cyan : neon.green, boxShadow: active ? `0 0 10px ${neon.cyan}` : 'none' }} />
                  {w}
                  <Box sx={{ ml: 'auto', fontFamily: mono, fontSize: 9, opacity: 0.7 }}>{active ? 'SEND' : 'IDLE'}</Box>
                </Box>
              );
            })}
          </Box>

          {/* main */}
          <Box sx={{ p: { xs: 2, sm: 2.5 } }}>
            <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 1.25, mb: 2 }}>
              {[
                { k: 'SENT', v: sent.toLocaleString(), c: neon.cyan },
                { k: 'WINDOWS', v: '5', c: neon.violet },
                { k: 'RETRIES', v: Math.floor(sent / 11), c: neon.pink },
              ].map((s) => (
                <Box key={s.k} sx={{ p: 1.25, borderRadius: 2, bgcolor: alpha(s.c, 0.06), border: `1px solid ${alpha(s.c, 0.2)}` }}>
                  <Box sx={{ fontFamily: mono, fontSize: 9, letterSpacing: '0.15em', color: 'text.secondary' }}>{s.k}</Box>
                  <Box sx={{ fontFamily: '"Space Grotesk"', fontWeight: 700, fontSize: { xs: 18, sm: 22 }, color: s.c, textShadow: `0 0 18px ${alpha(s.c, 0.6)}` }}>{s.v}</Box>
                </Box>
              ))}
            </Box>

            <Box sx={{ display: 'flex', justifyContent: 'space-between', fontFamily: mono, fontSize: 10, color: 'text.secondary', mb: 0.75 }}>
              <span>CAMPAIGN PROGRESS</span>
              <span>{Math.round(pct)}%</span>
            </Box>
            <Box sx={{ height: 8, borderRadius: 99, bgcolor: alpha('#fff', 0.05), overflow: 'hidden', mb: 2.25 }}>
              <Box
                sx={{
                  height: '100%',
                  width: `${pct}%`,
                  borderRadius: 99,
                  background: `linear-gradient(90deg, ${neon.blue}, ${neon.cyan}, ${neon.violet}, ${neon.cyan})`,
                  backgroundSize: '200% auto',
                  animation: 'shimmer 2s linear infinite',
                  boxShadow: `0 0 16px ${alpha(neon.cyan, 0.7)}`,
                  transition: 'width .6s ease',
                }}
              />
            </Box>

            <Box sx={{ fontFamily: mono, fontSize: 9.5, letterSpacing: '0.15em', color: 'text.secondary', mb: 1 }}>SEND LOG</Box>
            <Box sx={{ borderRadius: 2, bgcolor: '#050811', border: `1px solid ${neon.line}`, p: 1.25, minHeight: 150 }}>
              {lines.map((l, i) => (
                <Box
                  key={l.id}
                  sx={{
                    display: 'flex', gap: 1.25, fontFamily: mono, fontSize: { xs: 10, sm: 11 }, py: 0.35,
                    opacity: 1 - i * 0.14, whiteSpace: 'nowrap', overflow: 'hidden',
                  }}
                >
                  <Box component="span" sx={{ color: neon.violet }}>{l.win}</Box>
                  <Box component="span" sx={{ color: 'text.secondary', overflow: 'hidden', textOverflow: 'ellipsis' }}>{l.to}</Box>
                  <Box component="span" sx={{ ml: 'auto', color: l.status === 'SENT' ? neon.green : '#FFB547' }}>{l.status}</Box>
                </Box>
              ))}
              <Box component="span" sx={{ fontFamily: mono, fontSize: 11, color: neon.cyan, animation: 'blink 1s steps(1) infinite' }}>▌</Box>
            </Box>
          </Box>
        </Box>
      </Box>
    </Box>
  );
}
