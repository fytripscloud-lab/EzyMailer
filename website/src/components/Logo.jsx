import Box from '@mui/material/Box';
import { Link as RouterLink } from 'react-router-dom';
import { neon } from '../theme';

export default function Logo({ size = 34 }) {
  return (
    <Box component={RouterLink} to="/" aria-label="EzyMailer home" sx={{ display: 'inline-flex', alignItems: 'center', gap: 1.25, textDecoration: 'none', color: 'text.primary' }}>
      <Box component="img" src="/logo.png" alt="" width={size} height={size} sx={{ filter: `drop-shadow(0 0 10px ${neon.cyan}66)` }} />
      <Box component="span" sx={{ fontFamily: '"Space Grotesk", sans-serif', fontWeight: 700, fontSize: 20, letterSpacing: '-0.02em' }}>
        Ezy<Box component="span" sx={{ color: neon.cyan }}>Mailer</Box>
      </Box>
    </Box>
  );
}
