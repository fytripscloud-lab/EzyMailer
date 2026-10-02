import Box from '@mui/material/Box';
import { neon } from '../theme';

// Fixed, decorative backdrop: perspective grid floor plus drifting glow orbs.
export default function Background() {
  const orb = (color, size, pos, duration) => ({
    position: 'absolute',
    width: size,
    height: size,
    borderRadius: '50%',
    background: `radial-gradient(circle, ${color} 0%, transparent 70%)`,
    filter: 'blur(40px)',
    opacity: 0.35,
    animation: `floatY ${duration}s ease-in-out infinite`,
    ...pos,
  });

  return (
    <Box aria-hidden sx={{ position: 'fixed', inset: 0, zIndex: -1, overflow: 'hidden', pointerEvents: 'none' }}>
      <Box
        sx={{
          position: 'absolute',
          inset: 0,
          backgroundImage: `linear-gradient(${neon.line} 1px, transparent 1px), linear-gradient(90deg, ${neon.line} 1px, transparent 1px)`,
          backgroundSize: '64px 64px',
          maskImage: 'radial-gradient(ellipse 80% 60% at 50% 0%, #000 30%, transparent 75%)',
          WebkitMaskImage: 'radial-gradient(ellipse 80% 60% at 50% 0%, #000 30%, transparent 75%)',
          animation: 'gridMove 6s linear infinite',
          opacity: 0.55,
        }}
      />
      <Box sx={orb(neon.blue, 620, { top: -200, left: -160 }, 14)} />
      <Box sx={orb(neon.violet, 520, { top: 260, right: -200 }, 18)} />
      <Box sx={orb(neon.cyan, 380, { bottom: -120, left: '30%' }, 16)} />
      <Box
        sx={{
          position: 'absolute',
          inset: 0,
          background: 'radial-gradient(ellipse at 50% 120%, rgba(5,7,15,0) 0%, #05070F 70%)',
        }}
      />
    </Box>
  );
}
