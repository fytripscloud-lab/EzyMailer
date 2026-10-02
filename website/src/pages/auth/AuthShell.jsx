import { Link as RouterLink } from 'react-router-dom';
import Box from '@mui/material/Box';
import Container from '@mui/material/Container';
import Grid from '@mui/material/Grid';
import Typography from '@mui/material/Typography';
import Stack from '@mui/material/Stack';
import { alpha } from '@mui/material/styles';
import CheckCircleRounded from '@mui/icons-material/CheckCircleRounded';
import GlassCard from '../../components/GlassCard';
import Reveal from '../../components/Reveal';
import { gradientText, neon } from '../../theme';

const perks = [
  'Track your licence and validity at a glance',
  'Extend your licence in a couple of clicks',
  'App releases, rules and Google updates in one feed',
  'Full login and renewal history',
];

// Two-column layout for login / register / reset: brand pitch left, form card right.
export default function AuthShell({ title, subtitle, children, footer }) {
  return (
    <Container maxWidth="lg" sx={{ py: { xs: 6, md: 10 } }}>
      <Grid container spacing={{ xs: 5, md: 8 }} sx={{ alignItems: 'center' }}>
        <Grid size={{ xs: 12, md: 6 }} sx={{ display: { xs: 'none', md: 'block' } }}>
          <Reveal>
            <Typography variant="overline" sx={{ color: neon.cyan }}>Account portal</Typography>
            <Typography variant="h2" sx={{ fontSize: '3rem', mt: 1 }}>
              Your EzyMailer <Box component="span" sx={gradientText}>mission control.</Box>
            </Typography>
            <Stack spacing={1.75} sx={{ mt: 4 }}>
              {perks.map((p) => (
                <Box key={p} sx={{ display: 'flex', gap: 1.5, alignItems: 'center', color: 'text.secondary' }}>
                  <CheckCircleRounded sx={{ color: neon.cyan, fontSize: 20 }} /> {p}
                </Box>
              ))}
            </Stack>
            <Box sx={{ mt: 6, display: 'flex', gap: 2, alignItems: 'center' }}>
              <Box component="img" src="/logo.png" alt="" sx={{ width: 64, filter: `drop-shadow(0 0 20px ${neon.cyan})`, animation: 'floatY 6s ease-in-out infinite' }} />
              <Typography color="text.secondary" variant="body2">One account for the desktop app<br />and this portal.</Typography>
            </Box>
          </Reveal>
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <Reveal delay={100}>
            <GlassCard hover={false} sx={{ p: { xs: 3, sm: 5 }, maxWidth: 480, mx: 'auto', borderColor: alpha(neon.cyan, 0.25), boxShadow: `0 40px 100px -40px ${alpha(neon.cyan, 0.5)}` }}>
              <Typography variant="h4" component="h1">{title}</Typography>
              {subtitle && <Typography color="text.secondary" sx={{ mt: 1, mb: 3.5 }}>{subtitle}</Typography>}
              {children}
              {footer && <Box sx={{ mt: 3, textAlign: 'center', color: 'text.secondary', fontSize: 14 }}>{footer}</Box>}
            </GlassCard>
          </Reveal>
        </Grid>
      </Grid>
    </Container>
  );
}

export const authLink = (to, label) => (
  <Box component={RouterLink} to={to} sx={{ color: neon.cyan, fontWeight: 600, textDecoration: 'none', '&:hover': { textDecoration: 'underline' } }}>
    {label}
  </Box>
);
