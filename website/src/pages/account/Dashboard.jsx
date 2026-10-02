import { useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import Grid from '@mui/material/Grid';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Stack from '@mui/material/Stack';
import Alert from '@mui/material/Alert';
import Chip from '@mui/material/Chip';
import { alpha } from '@mui/material/styles';
import ArrowForwardRounded from '@mui/icons-material/ArrowForwardRounded';
import SendRounded from '@mui/icons-material/SendRounded';
import CalendarMonthRounded from '@mui/icons-material/CalendarMonthRounded';
import LaptopMacRounded from '@mui/icons-material/LaptopMacRounded';
import LoginRounded from '@mui/icons-material/LoginRounded';
import GlassCard from '../../components/GlassCard';
import Reveal from '../../components/Reveal';
import ValidityRing from './ValidityRing';
import { ExtendDialog, PanelTitle, StatusChip, mono } from './shared';
import { user, license, loginLogs, updates, sentLast14 } from '../../data/mockAccount';
import { gradientText, neon } from '../../theme';

function Stat({ icon: Icon, label, value, sub, color }) {
  return (
    <GlassCard glow={color} sx={{ p: 2.5 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25, color: 'text.secondary', fontSize: 13 }}>
        <Box sx={{ width: 32, height: 32, borderRadius: 2, display: 'grid', placeItems: 'center', bgcolor: alpha(color, 0.12), color }}><Icon fontSize="small" /></Box>
        {label}
      </Box>
      <Typography sx={{ fontFamily: '"Space Grotesk"', fontWeight: 700, fontSize: 28, mt: 1.5 }}>{value}</Typography>
      <Typography variant="body2" color="text.secondary">{sub}</Typography>
    </GlassCard>
  );
}

function SendChart() {
  const max = Math.max(...sentLast14);
  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'flex-end', gap: { xs: 0.5, sm: 1 }, height: 140 }}>
        {sentLast14.map((v, i) => {
          const last = i === sentLast14.length - 1;
          return (
            <Box key={i} title={`${v} emails`} sx={{ flex: 1, height: `${(v / max) * 100}%`, borderRadius: '6px 6px 2px 2px', background: last ? `linear-gradient(180deg, ${neon.cyan}, ${alpha(neon.cyan, 0.3)})` : `linear-gradient(180deg, ${alpha(neon.violet, 0.8)}, ${alpha(neon.violet, 0.15)})`, boxShadow: last ? `0 0 18px ${alpha(neon.cyan, 0.6)}` : 'none', transformOrigin: 'bottom', animation: 'fillBar .8s ease both' }} />
          );
        })}
      </Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 1, fontFamily: mono, fontSize: 11, color: 'text.secondary' }}>
        <span>14 days ago</span><span>Today</span>
      </Box>
    </Box>
  );
}

export default function Dashboard() {
  const [open, setOpen] = useState(false);
  const lastLogin = loginLogs[0];

  return (
    <>
      <Reveal>
        <Typography variant="h3" sx={{ fontSize: { xs: '1.8rem', md: '2.4rem' } }}>
          Welcome back, <Box component="span" sx={gradientText}>{user.name.split(' ')[0]}</Box>
        </Typography>
        <Typography color="text.secondary" sx={{ mt: 0.5, mb: 3 }}>Here’s the state of your EzyMailer licence and activity.</Typography>
      </Reveal>

      {license.daysLeft <= 31 && (
        <Reveal>
          <Alert
            severity="warning"
            variant="outlined"
            sx={{ mb: 3, borderRadius: 3, bgcolor: alpha('#FFB547', 0.05), alignItems: 'center' }}
            action={<Button color="inherit" size="small" onClick={() => setOpen(true)}>Extend now</Button>}
          >
            Your licence expires on <b>{license.endDate}</b>. Extend now to avoid interruption.
          </Alert>
        </Reveal>
      )}

      <Grid container spacing={2.5}>
        <Grid size={{ xs: 12, lg: 5 }}>
          <Reveal sx={{ height: '100%' }}>
            <GlassCard hover={false} sx={{ borderColor: alpha(neon.cyan, 0.3), background: `radial-gradient(circle at 0% 0%, ${alpha(neon.cyan, 0.12)}, transparent 60%), linear-gradient(160deg, rgba(18,26,51,.75), rgba(7,11,24,.75))` }}>
              <PanelTitle action={<StatusChip status={license.status} />}>Licence</PanelTitle>
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={3} sx={{ alignItems: 'center' }}>
                <ValidityRing daysLeft={license.daysLeft} totalDays={license.totalDays} />
                <Box sx={{ width: '100%' }}>
                  <Typography variant="overline" color="text.secondary">Plan</Typography>
                  <Typography variant="h5" sx={{ mb: 1.5 }}>{license.plan}</Typography>
                  <Typography variant="overline" color="text.secondary">Valid</Typography>
                  <Typography sx={{ fontFamily: mono, fontSize: 14 }}>{license.startDate} → {license.endDate}</Typography>
                  <Stack direction="row" spacing={1} sx={{ mt: 2.5 }}>
                    <Button variant="contained" onClick={() => setOpen(true)}>Extend</Button>
                    <Button component={RouterLink} to="/account/license" variant="outlined">Details</Button>
                  </Stack>
                </Box>
              </Stack>
            </GlassCard>
          </Reveal>
        </Grid>
        <Grid size={{ xs: 12, lg: 7 }}>
          <Grid container spacing={2.5} sx={{ height: '100%' }}>
            <Grid size={{ xs: 12, sm: 6 }}><Stat icon={SendRounded} label="Sent today" value={license.sentToday.toLocaleString()} sub="Across all senders" color={neon.cyan} /></Grid>
            <Grid size={{ xs: 12, sm: 6 }}><Stat icon={CalendarMonthRounded} label="Sent this month" value={license.sentThisMonth.toLocaleString()} sub="Since Oct 1" color={neon.violet} /></Grid>
            <Grid size={{ xs: 12, sm: 6 }}><Stat icon={LaptopMacRounded} label="Bound device" value={license.device.name} sub={`${license.device.os} · ${license.devicesAllowed} of ${license.devicesAllowed} used`} color={neon.green} /></Grid>
            <Grid size={{ xs: 12, sm: 6 }}><Stat icon={LoginRounded} label="Last sign-in" value={lastLogin.time.slice(11)} sub={`${lastLogin.time.slice(0, 10)} · ${lastLogin.location}`} color={neon.pink} /></Grid>
          </Grid>
        </Grid>

        <Grid size={{ xs: 12, lg: 7 }}>
          <Reveal sx={{ height: '100%' }}>
            <GlassCard hover={false}>
              <PanelTitle sub="Emails sent per day, last 14 days">Sending activity</PanelTitle>
              <SendChart />
            </GlassCard>
          </Reveal>
        </Grid>
        <Grid size={{ xs: 12, lg: 5 }}>
          <Reveal sx={{ height: '100%' }}>
            <GlassCard hover={false}>
              <PanelTitle action={<Button component={RouterLink} to="/account/updates" size="small" endIcon={<ArrowForwardRounded />}>All</Button>}>Latest updates</PanelTitle>
              <Stack spacing={1.5}>
                {updates.slice(0, 4).map((u) => (
                  <Box key={u.id} component={RouterLink} to="/account/updates" sx={{ textDecoration: 'none', color: 'inherit', p: 1.5, borderRadius: 3, border: `1px solid ${neon.line}`, '&:hover': { borderColor: alpha(neon.cyan, 0.4) } }}>
                    <Stack direction="row" spacing={1} sx={{ alignItems: 'center', mb: 0.5 }}>
                      <Chip size="small" label={u.tag} variant="outlined" sx={{ height: 20, fontSize: 10.5, borderColor: neon.line }} />
                      <Typography variant="caption" color="text.secondary" sx={{ fontFamily: mono }}>{u.date}</Typography>
                    </Stack>
                    <Typography sx={{ fontWeight: 600, fontSize: 14.5 }}>{u.title}</Typography>
                  </Box>
                ))}
              </Stack>
            </GlassCard>
          </Reveal>
        </Grid>
      </Grid>
      <ExtendDialog open={open} onClose={() => setOpen(false)} planId="m3" />
    </>
  );
}
