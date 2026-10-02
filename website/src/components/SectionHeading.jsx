import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import { gradientText, neon } from '../theme';
import Reveal from './Reveal';

export default function SectionHeading({ eyebrow, title, highlight, subtitle, align = 'center', as = 'h2' }) {
  return (
    <Reveal sx={{ textAlign: align, maxWidth: align === 'center' ? 760 : 'none', mx: align === 'center' ? 'auto' : 0, mb: { xs: 5, md: 7 } }}>
      {eyebrow && (
        <Typography
          variant="overline"
          sx={{ display: 'inline-flex', alignItems: 'center', gap: 1, color: neon.cyan, mb: 1.5 }}
        >
          <Box component="span" sx={{ width: 18, height: 2, bgcolor: neon.cyan, boxShadow: `0 0 10px ${neon.cyan}` }} />
          {eyebrow}
        </Typography>
      )}
      <Typography component={as} variant="h2" sx={{ fontSize: { xs: '2.1rem', sm: '2.6rem', md: '3.2rem' } }}>
        {title}{' '}
        {highlight && <Box component="span" sx={gradientText}>{highlight}</Box>}
      </Typography>
      {subtitle && (
        <Typography color="text.secondary" sx={{ mt: 2, fontSize: { xs: '1rem', md: '1.125rem' }, lineHeight: 1.7 }}>
          {subtitle}
        </Typography>
      )}
    </Reveal>
  );
}
