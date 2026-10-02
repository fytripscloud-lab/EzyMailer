import Container from '@mui/material/Container';
import Grid from '@mui/material/Grid';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import { alpha } from '@mui/material/styles';
import SpeedRounded from '@mui/icons-material/SpeedRounded';
import VisibilityRounded from '@mui/icons-material/VisibilityRounded';
import LockRounded from '@mui/icons-material/LockRounded';
import VerifiedUserRounded from '@mui/icons-material/VerifiedUserRounded';
import PageHero from '../components/PageHero';
import GlassCard from '../components/GlassCard';
import Reveal from '../components/Reveal';
import { neon } from '../theme';

const values = [
  { icon: SpeedRounded, c: neon.cyan, t: 'Fast, but never sloppy', d: 'Every click and page load is confirmed before the next step. Speed comes from smart engineering, not from skipping checks.' },
  { icon: VisibilityRounded, c: neon.violet, t: 'Nothing hidden', d: 'A live dashboard, a send log and an activity log show exactly what the app is doing at every moment.' },
  { icon: LockRounded, c: neon.green, t: 'Your data, your machine', d: 'Gmail sessions, credentials, lists and content stay on your computer. We only run accounts and licensing.' },
  { icon: VerifiedUserRounded, c: neon.pink, t: 'Built for permission-based email', d: 'EzyMailer is a tool for people who have earned their recipients’ attention. Our Acceptable Use Policy is part of the product.' },
];

export default function About() {
  return (
    <>
      <PageHero
        eyebrow="About"
        title="We build the cockpit for"
        highlight="email that matters."
        subtitle="EzyMailer started with a simple frustration: sending personalised Gmail campaigns meant juggling spreadsheets, scripts, document tools and a dozen browser tabs. So we put the whole workflow in one fast, focused desktop app."
      />
      <Container maxWidth="lg">
        <Grid container spacing={2.5}>
          {values.map((v, i) => {
            const Icon = v.icon;
            return (
              <Grid key={v.t} size={{ xs: 12, sm: 6 }}>
                <Reveal delay={(i % 2) * 100} sx={{ height: '100%' }}>
                  <GlassCard glow={v.c}>
                    <Box sx={{ width: 48, height: 48, borderRadius: 3, display: 'grid', placeItems: 'center', bgcolor: alpha(v.c, 0.12), border: `1px solid ${alpha(v.c, 0.35)}`, color: v.c, mb: 2 }}>
                      <Icon />
                    </Box>
                    <Typography variant="h5" sx={{ mb: 1 }}>{v.t}</Typography>
                    <Typography color="text.secondary" sx={{ lineHeight: 1.7 }}>{v.d}</Typography>
                  </GlassCard>
                </Reveal>
              </Grid>
            );
          })}
        </Grid>
      </Container>
    </>
  );
}
