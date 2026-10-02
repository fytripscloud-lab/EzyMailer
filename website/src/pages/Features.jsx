import { useState } from 'react';
import Container from '@mui/material/Container';
import Grid from '@mui/material/Grid';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Stack from '@mui/material/Stack';
import ToggleButton from '@mui/material/ToggleButton';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';
import { alpha } from '@mui/material/styles';
import PageHero from '../components/PageHero';
import GlassCard from '../components/GlassCard';
import Reveal from '../components/Reveal';
import DownloadButtons from '../components/DownloadButtons';
import { categories, features } from '../data/features';
import { neon } from '../theme';

export default function Features() {
  const [cat, setCat] = useState('All');
  const shown = cat === 'All' ? features : features.filter((f) => f.category === cat);

  return (
    <>
      <PageHero
        eyebrow={`${features.length} modules`}
        title="Everything inside"
        highlight="EzyMailer."
        subtitle="Sending engines, a content studio, personalisation, AI and full visibility — designed as one system."
      />
      <Container maxWidth="lg">
        <Box sx={{ display: 'flex', justifyContent: 'center', mb: 6, overflowX: 'auto', pb: 1 }}>
          <ToggleButtonGroup
            exclusive
            value={cat}
            onChange={(_, v) => v && setCat(v)}
            aria-label="Filter features by category"
            sx={{
              bgcolor: alpha('#0B1020', 0.6),
              border: `1px solid ${neon.line}`,
              borderRadius: 99,
              p: 0.5,
              '& .MuiToggleButton-root': {
                border: 0, borderRadius: '99px !important', px: 2.5, py: 0.9, textTransform: 'none', color: 'text.secondary', fontWeight: 500,
                '&.Mui-selected': { color: '#021018', bgcolor: neon.cyan, '&:hover': { bgcolor: neon.cyan } },
              },
            }}
          >
            {categories.map((c) => <ToggleButton key={c} value={c}>{c}</ToggleButton>)}
          </ToggleButtonGroup>
        </Box>

        <Grid container spacing={2.5}>
          {shown.map((f, i) => {
            const Icon = f.icon;
            return (
              <Grid key={f.id} id={f.id} size={{ xs: 12, md: 6 }} sx={{ scrollMarginTop: 100 }}>
                <Reveal delay={(i % 2) * 90} sx={{ height: '100%' }}>
                  <GlassCard glow={f.color} sx={{ overflow: 'hidden', p: { xs: 3, md: 4 } }}>
                    <Box aria-hidden sx={{ position: 'absolute', top: -90, right: -90, width: 240, height: 240, borderRadius: '50%', background: `radial-gradient(circle, ${alpha(f.color, 0.22)}, transparent 70%)` }} />
                    <Stack direction="row" spacing={2} sx={{ alignItems: 'center', mb: 2 }}>
                      <Box sx={{ width: 52, height: 52, flexShrink: 0, borderRadius: 3, display: 'grid', placeItems: 'center', bgcolor: alpha(f.color, 0.12), border: `1px solid ${alpha(f.color, 0.35)}`, color: f.color, boxShadow: `0 0 30px -8px ${f.color}` }}>
                        <Icon />
                      </Box>
                      <Box>
                        <Typography variant="overline" sx={{ color: f.color, lineHeight: 1.4, display: 'block' }}>{f.category}</Typography>
                        <Typography variant="h5" component="h2">{f.title}</Typography>
                      </Box>
                    </Stack>
                    <Typography color="text.secondary" sx={{ lineHeight: 1.7, mb: 2.5 }}>{f.short}</Typography>
                    <Stack spacing={1.1}>
                      {f.points.map((p) => (
                        <Box key={p} sx={{ display: 'flex', gap: 1.25, fontSize: 15, color: 'text.secondary', lineHeight: 1.55 }}>
                          <Box component="span" sx={{ mt: '7px', width: 6, height: 6, flexShrink: 0, borderRadius: '50%', bgcolor: f.color, boxShadow: `0 0 8px ${f.color}` }} />
                          {p}
                        </Box>
                      ))}
                    </Stack>
                  </GlassCard>
                </Reveal>
              </Grid>
            );
          })}
        </Grid>

        <Reveal sx={{ textAlign: 'center', mt: { xs: 8, md: 12 } }}>
          <Typography variant="h3" sx={{ fontSize: { xs: '1.8rem', md: '2.4rem' }, mb: 3 }}>See it on your own desktop.</Typography>
          <DownloadButtons justify="center" />
        </Reveal>
      </Container>
    </>
  );
}
