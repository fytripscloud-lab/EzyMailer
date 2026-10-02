import { useState } from 'react';
import Grid from '@mui/material/Grid';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Stack from '@mui/material/Stack';
import IconButton from '@mui/material/IconButton';
import Tooltip from '@mui/material/Tooltip';
import LinearProgress from '@mui/material/LinearProgress';
import { alpha } from '@mui/material/styles';
import ContentCopyRounded from '@mui/icons-material/ContentCopyRounded';
import CheckRounded from '@mui/icons-material/CheckRounded';
import LaptopMacRounded from '@mui/icons-material/LaptopMacRounded';
import Telegram from '@mui/icons-material/Telegram';
import GlassCard from '../../components/GlassCard';
import Reveal from '../../components/Reveal';
import ValidityRing from './ValidityRing';
import { ExtendDialog, PanelTitle, PlanPicker, StatusChip, addMonths, mono } from './shared';
import { license, plans } from '../../data/mockAccount';
import { site } from '../../config/site';
import { neon } from '../../theme';

function Field({ label, children }) {
  return (
    <Box>
      <Typography variant="overline" color="text.secondary">{label}</Typography>
      <Box sx={{ mt: 0.25 }}>{children}</Box>
    </Box>
  );
}

export default function License() {
  const [plan, setPlan] = useState('m3');
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const chosen = plans.find((p) => p.id === plan);
  const used = license.totalDays - license.daysLeft;

  const copy = async () => {
    try { await navigator.clipboard.writeText(license.key); setCopied(true); setTimeout(() => setCopied(false), 1500); } catch { /* ignore */ }
  };

  return (
    <>
      <Grid container spacing={2.5}>
        <Grid size={{ xs: 12, lg: 8 }}>
          <Reveal sx={{ height: '100%' }}>
            <GlassCard hover={false}>
              <PanelTitle action={<StatusChip status={license.status} />} sub="Your current licence and validity">Licence details</PanelTitle>
              <Stack direction={{ xs: 'column', md: 'row' }} spacing={4} sx={{ alignItems: { md: 'center' } }}>
                <Box sx={{ alignSelf: 'center' }}><ValidityRing daysLeft={license.daysLeft} totalDays={license.totalDays} size={180} /></Box>
                <Grid container spacing={2.5} sx={{ flex: 1 }}>
                  <Grid size={{ xs: 12 }}>
                    <Field label="Licence key">
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, p: 1.25, pl: 1.75, borderRadius: 2, bgcolor: '#050811', border: `1px solid ${neon.line}` }}>
                        <Typography sx={{ fontFamily: mono, flex: 1, letterSpacing: '0.08em' }}>{license.key}</Typography>
                        <Tooltip title={copied ? 'Copied' : 'Copy'}>
                          <IconButton size="small" onClick={copy} aria-label="Copy licence key">{copied ? <CheckRounded fontSize="small" sx={{ color: neon.green }} /> : <ContentCopyRounded fontSize="small" />}</IconButton>
                        </Tooltip>
                      </Box>
                    </Field>
                  </Grid>
                  <Grid size={{ xs: 6 }}><Field label="Plan"><Typography variant="h6">{license.plan}</Typography></Field></Grid>
                  <Grid size={{ xs: 6 }}><Field label="Devices"><Typography variant="h6">{license.devicesAllowed} device</Typography></Field></Grid>
                  <Grid size={{ xs: 6 }}><Field label="Start date"><Typography sx={{ fontFamily: mono }}>{license.startDate}</Typography></Field></Grid>
                  <Grid size={{ xs: 6 }}><Field label="Expiry date"><Typography sx={{ fontFamily: mono, color: '#FFB547' }}>{license.endDate}</Typography></Field></Grid>
                  <Grid size={12}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: 'text.secondary', mb: 0.75 }}>
                      <span>{used} days used</span><span>{license.daysLeft} days left</span>
                    </Box>
                    <LinearProgress variant="determinate" value={(used / license.totalDays) * 100} sx={{ height: 8, borderRadius: 99, bgcolor: alpha('#fff', 0.06), '& .MuiLinearProgress-bar': { borderRadius: 99, background: `linear-gradient(90deg, ${neon.cyan}, ${neon.violet})` } }} />
                  </Grid>
                </Grid>
              </Stack>
            </GlassCard>
          </Reveal>
        </Grid>
        <Grid size={{ xs: 12, lg: 4 }}>
          <Reveal sx={{ height: '100%' }}>
            <GlassCard hover={false}>
              <PanelTitle sub="Licences are bound to one computer">Bound device</PanelTitle>
              <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', p: 2, borderRadius: 3, border: `1px solid ${alpha(neon.green, 0.3)}`, bgcolor: alpha(neon.green, 0.05) }}>
                <LaptopMacRounded sx={{ fontSize: 40, color: neon.green }} />
                <Box>
                  <Typography sx={{ fontWeight: 600 }}>{license.device.name}</Typography>
                  <Typography variant="body2" color="text.secondary">{license.device.os}</Typography>
                  <Typography variant="caption" sx={{ fontFamily: mono, color: 'text.secondary' }}>{license.device.id}</Typography>
                </Box>
              </Box>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>Bound on {license.device.boundOn}. Need to move to a new computer? Message support and we’ll reset it.</Typography>
              <Button href={site.telegramUrl} target="_blank" rel="noopener noreferrer" startIcon={<Telegram />} variant="outlined" fullWidth sx={{ mt: 2 }}>Request device reset</Button>
            </GlassCard>
          </Reveal>
        </Grid>

        <Grid size={12} id="extend" sx={{ scrollMarginTop: 90 }}>
          <Reveal>
            <GlassCard hover={false} sx={{ borderColor: alpha(neon.violet, 0.35) }}>
              <PanelTitle sub="Time is added on top of your current expiry date — you never lose days">Extend your licence</PanelTitle>
              <PlanPicker value={plan} onChange={setPlan} />
              <Box sx={{ mt: 3, display: 'flex', flexDirection: { xs: 'column', sm: 'row' }, gap: 2, alignItems: { sm: 'center' }, p: 2.5, borderRadius: 3, bgcolor: '#050811', border: `1px solid ${neon.line}` }}>
                <Box sx={{ flex: 1 }}>
                  <Typography color="text.secondary" variant="body2">New expiry date</Typography>
                  <Typography sx={{ fontFamily: mono, fontSize: 18 }}>
                    {license.endDate} <Box component="span" sx={{ color: neon.cyan }}>→ {addMonths(license.endDate, chosen.months)}</Box>
                  </Typography>
                </Box>
                <Button variant="contained" size="large" onClick={() => setOpen(true)}>Extend for {chosen.price}</Button>
              </Box>
            </GlassCard>
          </Reveal>
        </Grid>
      </Grid>
      <ExtendDialog open={open} onClose={() => setOpen(false)} planId={plan} />
    </>
  );
}
