import { useState } from 'react';
import Container from '@mui/material/Container';
import Grid from '@mui/material/Grid';
import Typography from '@mui/material/Typography';
import TextField from '@mui/material/TextField';
import MenuItem from '@mui/material/MenuItem';
import Button from '@mui/material/Button';
import Stack from '@mui/material/Stack';
import Box from '@mui/material/Box';
import Link from '@mui/material/Link';
import { alpha } from '@mui/material/styles';
import SendRounded from '@mui/icons-material/SendRounded';
import SupportAgentRounded from '@mui/icons-material/SupportAgentRounded';
import GavelRounded from '@mui/icons-material/GavelRounded';
import PrivacyTipRounded from '@mui/icons-material/PrivacyTipRounded';
import Telegram from '@mui/icons-material/Telegram';
import PageHero from '../components/PageHero';
import GlassCard from '../components/GlassCard';
import Reveal from '../components/Reveal';
import { site } from '../config/site';
import { neon } from '../theme';

const topics = ['Sales & accounts', 'Technical support', 'Billing', 'Privacy request', 'Report abuse', 'Other'];

const channels = [
  { icon: SupportAgentRounded, label: 'Support', email: site.supportEmail, c: neon.cyan },
  { icon: PrivacyTipRounded, label: 'Privacy', email: site.privacyEmail, c: neon.violet },
  { icon: GavelRounded, label: 'Legal', email: site.legalEmail, c: neon.pink },
];

// Frontend-only: the form composes a message in the visitor's mail client.
export default function Contact() {
  const [form, setForm] = useState({ name: '', email: '', topic: topics[0], message: '' });
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = (e) => {
    e.preventDefault();
    const to = form.topic === 'Privacy request' ? site.privacyEmail : site.supportEmail;
    const subject = `[${form.topic}] ${form.name}`;
    const body = `${form.message}\n\n— ${form.name} <${form.email}>`;
    window.location.href = `mailto:${to}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
  };

  return (
    <>
      <PageHero eyebrow="Contact" title="Let’s" highlight="talk." subtitle="Accounts, support, billing or feedback — we read every message." />
      <Container maxWidth="lg">
        <Grid container spacing={3}>
          <Grid size={{ xs: 12, md: 5 }}>
            <Stack spacing={2}>
              <Reveal>
                <GlassCard glow="#29A9EB" sx={{ p: 3, borderColor: alpha('#29A9EB', 0.4), background: `linear-gradient(160deg, ${alpha('#29A9EB', 0.16)}, rgba(7,11,24,.75))` }}>
                  <Stack direction="row" spacing={2} sx={{ alignItems: 'center', mb: 2 }}>
                    <Box sx={{ width: 46, height: 46, borderRadius: 3, display: 'grid', placeItems: 'center', bgcolor: '#29A9EB', color: '#fff', boxShadow: '0 0 30px -4px #29A9EB' }}>
                      <Telegram />
                    </Box>
                    <Box>
                      <Typography sx={{ fontWeight: 600 }}>Live chat on Telegram</Typography>
                      <Typography variant="body2" color="text.secondary">Fastest way to reach the team</Typography>
                    </Box>
                  </Stack>
                  <Button fullWidth href={site.telegramUrl} target="_blank" rel="noopener noreferrer" variant="contained" startIcon={<Telegram />} sx={{ background: '#29A9EB !important', color: '#fff' }}>
                    Open chat
                  </Button>
                </GlassCard>
              </Reveal>
              {channels.map((c, i) => {
                const Icon = c.icon;
                return (
                  <Reveal key={c.label} delay={i * 80}>
                    <GlassCard glow={c.c} sx={{ display: 'flex', alignItems: 'center', gap: 2, p: 2.5 }}>
                      <Box sx={{ width: 46, height: 46, borderRadius: 3, display: 'grid', placeItems: 'center', bgcolor: alpha(c.c, 0.12), color: c.c, border: `1px solid ${alpha(c.c, 0.35)}` }}>
                        <Icon />
                      </Box>
                      <Box sx={{ minWidth: 0 }}>
                        <Typography sx={{ fontWeight: 600 }}>{c.label}</Typography>
                        <Link href={`mailto:${c.email}`} underline="hover" sx={{ color: 'text.secondary', fontFamily: '"JetBrains Mono", monospace', fontSize: 14, wordBreak: 'break-all' }}>
                          {c.email}
                        </Link>
                      </Box>
                    </GlassCard>
                  </Reveal>
                );
              })}
            </Stack>
          </Grid>
          <Grid size={{ xs: 12, md: 7 }}>
            <Reveal>
              <GlassCard hover={false} component="form" onSubmit={submit} sx={{ p: { xs: 3, md: 4 } }}>
                <Grid container spacing={2}>
                  <Grid size={{ xs: 12, sm: 6 }}>
                    <TextField label="Your name" required value={form.name} onChange={set('name')} autoComplete="name" />
                  </Grid>
                  <Grid size={{ xs: 12, sm: 6 }}>
                    <TextField label="Email" type="email" required value={form.email} onChange={set('email')} autoComplete="email" />
                  </Grid>
                  <Grid size={12}>
                    <TextField select label="Topic" value={form.topic} onChange={set('topic')}>
                      {topics.map((t) => <MenuItem key={t} value={t}>{t}</MenuItem>)}
                    </TextField>
                  </Grid>
                  <Grid size={12}>
                    <TextField label="Message" required multiline minRows={5} value={form.message} onChange={set('message')} />
                  </Grid>
                  <Grid size={12}>
                    <Button type="submit" variant="contained" size="large" endIcon={<SendRounded />}>Send message</Button>
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 1.5 }}>
                      Opens your email app with the message ready to send.
                    </Typography>
                  </Grid>
                </Grid>
              </GlassCard>
            </Reveal>
          </Grid>
        </Grid>
      </Container>
    </>
  );
}
