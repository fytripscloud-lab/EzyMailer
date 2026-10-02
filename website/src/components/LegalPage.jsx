import { Link as RouterLink, useLocation } from 'react-router-dom';
import Container from '@mui/material/Container';
import Grid from '@mui/material/Grid';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Link from '@mui/material/Link';
import Stack from '@mui/material/Stack';
import Chip from '@mui/material/Chip';
import PageHero from './PageHero';
import GlassCard from './GlassCard';
import { legalLinks } from '../data/legal';
import { site } from '../config/site';
import { neon } from '../theme';

const slug = (s) => s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');

export default function LegalPage({ doc }) {
  const { pathname } = useLocation();

  return (
    <>
      <PageHero eyebrow="Legal" title={doc.title} subtitle={doc.summary} />
      <Container maxWidth="lg">
        <Box sx={{ display: 'flex', justifyContent: 'center', mb: 6 }}>
          <Chip label={`Effective ${site.legalEffectiveDate}`} variant="outlined" sx={{ borderColor: neon.line, color: 'text.secondary' }} />
        </Box>
        <Grid container spacing={4}>
          <Grid size={{ xs: 12, md: 4 }}>
            <Box sx={{ position: { md: 'sticky' }, top: 100 }}>
              <GlassCard hover={false} sx={{ p: 2.5 }}>
                <Typography variant="overline" color="text.secondary">On this page</Typography>
                <Stack component="ol" spacing={1} sx={{ mt: 1, pl: 2.5, mb: 0, color: 'text.secondary', fontSize: 14 }}>
                  {doc.sections.map((s) => (
                    <li key={s.h}>
                      <Link href={`#${slug(s.h)}`} underline="hover" sx={{ color: 'text.secondary', '&:hover': { color: neon.cyan } }}>
                        {s.h}
                      </Link>
                    </li>
                  ))}
                </Stack>
              </GlassCard>
              <GlassCard hover={false} sx={{ p: 2.5, mt: 2, display: { xs: 'none', md: 'block' } }}>
                <Typography variant="overline" color="text.secondary">Other policies</Typography>
                <Stack spacing={1} sx={{ mt: 1 }}>
                  {legalLinks.map((l) => (
                    <Link
                      key={l.to}
                      component={RouterLink}
                      to={l.to}
                      underline="none"
                      sx={{ fontSize: 14, color: pathname === l.to ? neon.cyan : 'text.secondary', '&:hover': { color: neon.cyan } }}
                    >
                      {l.label}
                    </Link>
                  ))}
                </Stack>
              </GlassCard>
            </Box>
          </Grid>
          <Grid size={{ xs: 12, md: 8 }}>
            <GlassCard hover={false} sx={{ p: { xs: 3, md: 5 } }}>
              {doc.sections.map((s, i) => (
                <Box key={s.h} id={slug(s.h)} component="section" sx={{ scrollMarginTop: 100, '&:not(:last-of-type)': { mb: 5 } }}>
                  <Typography variant="h5" component="h2" sx={{ mb: 1.5, display: 'flex', gap: 1.5, alignItems: 'baseline' }}>
                    <Box component="span" sx={{ fontFamily: '"JetBrains Mono", monospace', fontSize: 14, color: neon.cyan }}>
                      {String(i + 1).padStart(2, '0')}
                    </Box>
                    {s.h}
                  </Typography>
                  {s.p?.map((para) => (
                    <Typography key={para.slice(0, 40)} color="text.secondary" sx={{ lineHeight: 1.8, mb: 1.5 }}>
                      {para}
                    </Typography>
                  ))}
                  {s.list && (
                    <Box component="ul" sx={{ pl: 2.5, m: 0, color: 'text.secondary', '& li': { lineHeight: 1.8, mb: 0.75 }, '& li::marker': { color: neon.cyan } }}>
                      {s.list.map((item) => <li key={item}>{item}</li>)}
                    </Box>
                  )}
                </Box>
              ))}
            </GlassCard>
          </Grid>
        </Grid>
      </Container>
    </>
  );
}
