import { Link as RouterLink } from 'react-router-dom';
import Box from '@mui/material/Box';
import Container from '@mui/material/Container';
import Grid from '@mui/material/Grid';
import Typography from '@mui/material/Typography';
import Link from '@mui/material/Link';
import Stack from '@mui/material/Stack';
import Logo from './Logo';
import { legalLinks } from '../data/legal';
import { site } from '../config/site';
import { neon } from '../theme';

const columns = [
  {
    title: 'Product',
    links: [
      { to: '/features', label: 'Features' },
      { to: '/download', label: 'Download' },
      { to: '/download#requirements', label: 'System requirements' },
      { to: '/faq', label: 'FAQ' },
    ],
  },
  {
    title: 'Company',
    links: [
      { to: '/about', label: 'About' },
      { to: '/contact', label: 'Contact' },
      { to: '/login', label: 'Log in' },
      { to: '/register', label: 'Register' },
    ],
  },
  { title: 'Legal', links: legalLinks },
];

export default function Footer() {
  return (
    <Box component="footer" sx={{ borderTop: `1px solid ${neon.line}`, mt: { xs: 10, md: 16 }, pt: { xs: 6, md: 8 }, pb: 4, bgcolor: 'rgba(5,7,15,.6)', backdropFilter: 'blur(10px)' }}>
      <Container maxWidth="lg">
        <Grid container spacing={{ xs: 5, md: 4 }}>
          <Grid size={{ xs: 12, md: 4 }}>
            <Logo />
            <Typography color="text.secondary" sx={{ mt: 2, maxWidth: 320, lineHeight: 1.7 }}>
              The desktop command center for personalised Gmail campaigns — on Windows and macOS.
            </Typography>
            <Link href={`mailto:${site.supportEmail}`} sx={{ display: 'inline-block', mt: 2, color: neon.cyan, fontFamily: '"JetBrains Mono", monospace', fontSize: 14 }} underline="hover">
              {site.supportEmail}
            </Link>
          </Grid>
          {columns.map((col) => (
            <Grid key={col.title} size={{ xs: 6, sm: 4, md: col.title === 'Legal' ? 4 : 2 }}>
              <Typography variant="overline" sx={{ color: 'text.secondary' }}>{col.title}</Typography>
              <Stack spacing={1.25} sx={{ mt: 1.5 }}>
                {col.links.map((l) => (
                  <Link key={l.to} component={RouterLink} to={l.to} underline="none" sx={{ color: 'text.primary', opacity: 0.8, '&:hover': { opacity: 1, color: neon.cyan } }}>
                    {l.label}
                  </Link>
                ))}
              </Stack>
            </Grid>
          ))}
        </Grid>
        <Box sx={{ mt: 6, pt: 3, borderTop: `1px solid ${neon.line}`, display: 'flex', flexWrap: 'wrap', gap: 2, justifyContent: 'space-between' }}>
          <Typography variant="body2" color="text.secondary">
            © {new Date().getFullYear()} {site.companyName}. All rights reserved.
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Not affiliated with Google LLC. Gmail is a trademark of Google LLC.
          </Typography>
        </Box>
      </Container>
    </Box>
  );
}
