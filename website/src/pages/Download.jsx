import { useState } from 'react';
import Container from '@mui/material/Container';
import Grid from '@mui/material/Grid';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Stack from '@mui/material/Stack';
import Chip from '@mui/material/Chip';
import IconButton from '@mui/material/IconButton';
import Tooltip from '@mui/material/Tooltip';
import { alpha } from '@mui/material/styles';
import Apple from '@mui/icons-material/Apple';
import Microsoft from '@mui/icons-material/Microsoft';
import DownloadRounded from '@mui/icons-material/DownloadRounded';
import ContentCopyRounded from '@mui/icons-material/ContentCopyRounded';
import CheckRounded from '@mui/icons-material/CheckRounded';
import { Link as RouterLink } from 'react-router-dom';
import PageHero from '../components/PageHero';
import GlassCard from '../components/GlassCard';
import Reveal from '../components/Reveal';
import useOS from '../components/useOS';
import { site } from '../config/site';
import { neon } from '../theme';

const mono = '"JetBrains Mono", monospace';

const install = {
  windows: [
    'Download EzyMailer-Windows.exe.',
    'Run the installer. If SmartScreen appears, choose “More info” → “Run anyway”.',
    'On first launch, EzyMailer downloads its browser components — keep the window open until it finishes.',
    'Sign in with your EzyMailer account.',
  ],
  mac: [
    'Download EzyMailer-macOS.dmg.',
    'Open the disk image and drag EzyMailer into Applications.',
    'First launch only: Control-click EzyMailer → Open → Open.',
    'Sign in with your EzyMailer account.',
  ],
};

function Checksum({ value }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      /* clipboard unavailable — the value is still visible to select */
    }
  };
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 1, p: 1.25, borderRadius: 2, bgcolor: '#050811', border: `1px solid ${neon.line}` }}>
      <Box sx={{ fontFamily: mono, fontSize: 11.5, color: 'text.secondary', wordBreak: 'break-all', flex: 1 }}>{value}</Box>
      <Tooltip title={copied ? 'Copied' : 'Copy'}>
        <IconButton size="small" onClick={copy} aria-label="Copy SHA-256 checksum">
          {copied ? <CheckRounded fontSize="small" sx={{ color: neon.green }} /> : <ContentCopyRounded fontSize="small" />}
        </IconButton>
      </Tooltip>
    </Box>
  );
}

function PlatformCard({ id, icon: Icon, recommended, color }) {
  const p = site.downloads[id];
  return (
    <GlassCard glow={color} hover={false} sx={{ p: { xs: 3, md: 4.5 }, borderColor: recommended ? alpha(color, 0.5) : neon.line, boxShadow: recommended ? `0 30px 80px -30px ${alpha(color, 0.6)}` : 'none' }}>
      <Stack direction="row" spacing={2} sx={{ alignItems: 'center', mb: 3 }}>
        <Box sx={{ width: 64, height: 64, borderRadius: 3.5, display: 'grid', placeItems: 'center', bgcolor: alpha(color, 0.12), border: `1px solid ${alpha(color, 0.4)}`, color }}>
          <Icon sx={{ fontSize: 34 }} />
        </Box>
        <Box>
          <Typography variant="h4" component="h2">{p.label}</Typography>
          <Typography sx={{ fontFamily: mono, fontSize: 13, color: 'text.secondary' }}>v{site.version} · {p.size}</Typography>
        </Box>
        {recommended && <Chip label="Your system" size="small" sx={{ ml: 'auto !important', bgcolor: alpha(color, 0.15), color, border: `1px solid ${alpha(color, 0.4)}` }} />}
      </Stack>

      <Button href={p.url} download={p.fileName} fullWidth size="large" variant={recommended ? 'contained' : 'outlined'} startIcon={<DownloadRounded />}>
        Download for {p.label}
      </Button>

      <Typography variant="overline" sx={{ display: 'block', mt: 4, color: 'text.secondary' }}>Install</Typography>
      <Box component="ol" sx={{ pl: 2.5, m: 0, mt: 1, color: 'text.secondary', '& li': { mb: 1, lineHeight: 1.6 }, '& li::marker': { color, fontFamily: mono } }}>
        {install[id].map((s) => <li key={s}>{s}</li>)}
      </Box>

      <Typography variant="overline" sx={{ display: 'block', mt: 3, color: 'text.secondary' }}>Requirements</Typography>
      <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1, mt: 1 }}>
        {p.requirements.map((r) => <Chip key={r} label={r} size="small" variant="outlined" sx={{ borderColor: neon.line }} />)}
      </Stack>

      <Typography variant="overline" sx={{ display: 'block', mt: 3, color: 'text.secondary' }}>SHA-256 · {p.fileName}</Typography>
      <Checksum value={p.sha256} />
    </GlassCard>
  );
}

export default function Download() {
  const os = useOS();
  const cards = [
    { id: 'windows', icon: Microsoft, color: neon.cyan },
    { id: 'mac', icon: Apple, color: neon.violet },
  ];
  if (os === 'mac') cards.reverse();

  return (
    <>
      <PageHero
        eyebrow={`Version ${site.version} · Released ${site.releaseDate}`}
        title="Download"
        highlight="EzyMailer."
        subtitle="Native desktop apps for Windows and macOS. Each build ships with its own browser runtime, so you are ready to send right after sign-in."
      />
      <Container maxWidth="lg">
        <Grid container spacing={3} id="requirements" sx={{ scrollMarginTop: 100 }}>
          {cards.map((c, i) => (
            <Grid key={c.id} size={{ xs: 12, md: 6 }}>
              <Reveal delay={i * 120} sx={{ height: '100%' }}>
                <PlatformCard {...c} recommended={c.id === os} />
              </Reveal>
            </Grid>
          ))}
        </Grid>

        <Reveal sx={{ mt: 6 }}>
          <GlassCard hover={false} sx={{ display: 'flex', flexDirection: { xs: 'column', sm: 'row' }, gap: 3, alignItems: { sm: 'center' } }}>
            <Box sx={{ flex: 1 }}>
              <Typography variant="h6">You will need an EzyMailer account</Typography>
              <Typography color="text.secondary" sx={{ mt: 0.5 }}>
                The app asks you to sign in on first launch. Accounts are licensed per device. Contact us if you need one.
              </Typography>
            </Box>
            <Button component={RouterLink} to="/contact" variant="outlined">Contact sales</Button>
          </GlassCard>
        </Reveal>

        <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', mt: 4 }}>
          By downloading you agree to the{' '}
          <Box component={RouterLink} to="/terms" sx={{ color: neon.cyan }}>Terms of Service</Box>,{' '}
          <Box component={RouterLink} to="/eula" sx={{ color: neon.cyan }}>EULA</Box> and{' '}
          <Box component={RouterLink} to="/acceptable-use" sx={{ color: neon.cyan }}>Acceptable Use Policy</Box>.
        </Typography>
      </Container>
    </>
  );
}
