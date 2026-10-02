import { useState } from 'react';
import Grid from '@mui/material/Grid';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import Avatar from '@mui/material/Avatar';
import Stack from '@mui/material/Stack';
import Alert from '@mui/material/Alert';
import LinearProgress from '@mui/material/LinearProgress';
import { alpha } from '@mui/material/styles';
import PhotoCameraRounded from '@mui/icons-material/PhotoCameraRounded';
import LockResetRounded from '@mui/icons-material/LockResetRounded';
import GlassCard from '../../components/GlassCard';
import Reveal from '../../components/Reveal';
import PasswordField from '../auth/PasswordField';
import { PanelTitle, mono } from './shared';
import { user } from '../../data/mockAccount';
import { neon } from '../../theme';

function strength(pw) {
  let s = 0;
  if (pw.length >= 8) s++;
  if (/[A-Z]/.test(pw) && /[a-z]/.test(pw)) s++;
  if (/\d/.test(pw)) s++;
  if (/[^A-Za-z0-9]/.test(pw)) s++;
  return s;
}
const levels = [
  { l: 'Too short', c: '#FF6B81' },
  { l: 'Weak', c: '#FF6B81' },
  { l: 'Fair', c: '#FFB547' },
  { l: 'Good', c: neon.cyan },
  { l: 'Strong', c: neon.green },
];

// DESIGN ONLY — saving shows a confirmation; nothing is stored.
export default function Profile() {
  const [saved, setSaved] = useState(false);
  const [pwDone, setPwDone] = useState(false);
  const [pw, setPw] = useState('');
  const lv = levels[pw ? strength(pw) : 0];

  return (
    <Grid container spacing={2.5}>
      <Grid size={{ xs: 12, lg: 7 }}>
        <Reveal sx={{ height: '100%' }}>
          <GlassCard hover={false}>
            <PanelTitle sub="How you appear across EzyMailer">Profile details</PanelTitle>
            <Stack direction="row" spacing={2.5} sx={{ alignItems: 'center', mb: 3.5 }}>
              <Box sx={{ position: 'relative' }}>
                <Avatar sx={{ width: 84, height: 84, fontSize: 30, fontWeight: 700, color: '#021018', background: `linear-gradient(135deg, ${neon.cyan}, ${neon.violet})`, boxShadow: `0 0 40px -6px ${alpha(neon.cyan, 0.7)}` }}>{user.avatarInitials}</Avatar>
                <Box component="button" type="button" aria-label="Change photo" sx={{ all: 'unset', cursor: 'pointer', position: 'absolute', right: -4, bottom: -4, width: 32, height: 32, borderRadius: '50%', display: 'grid', placeItems: 'center', bgcolor: '#0B1020', border: `1px solid ${neon.line}`, '&:hover': { borderColor: neon.cyan } }}>
                  <PhotoCameraRounded sx={{ fontSize: 16 }} />
                </Box>
              </Box>
              <Box>
                <Typography variant="h5">{user.name}</Typography>
                <Typography color="text.secondary" sx={{ fontFamily: mono, fontSize: 13 }}>@{user.username} · member since {user.joined}</Typography>
              </Box>
            </Stack>
            <Box component="form" onSubmit={(e) => { e.preventDefault(); setSaved(true); }}>
              {saved && <Alert severity="success" variant="outlined" sx={{ mb: 2 }} onClose={() => setSaved(false)}>Profile updated.</Alert>}
              <Grid container spacing={2}>
                <Grid size={{ xs: 12, sm: 6 }}><TextField label="Full name" defaultValue={user.name} /></Grid>
                <Grid size={{ xs: 12, sm: 6 }}><TextField label="Username" defaultValue={user.username} disabled helperText="Contact support to change" /></Grid>
                <Grid size={{ xs: 12, sm: 6 }}><TextField label="Email" type="email" defaultValue={user.email} /></Grid>
                <Grid size={{ xs: 12, sm: 6 }}><TextField label="Phone" defaultValue={user.phone} /></Grid>
                <Grid size={{ xs: 12, sm: 6 }}><TextField label="Company" defaultValue={user.company} /></Grid>
                <Grid size={{ xs: 12, sm: 6 }}><TextField label="Country" defaultValue={user.country} /></Grid>
                <Grid size={12}><Button type="submit" variant="contained">Save changes</Button></Grid>
              </Grid>
            </Box>
          </GlassCard>
        </Reveal>
      </Grid>
      <Grid size={{ xs: 12, lg: 5 }}>
        <Reveal sx={{ height: '100%' }}>
          <GlassCard hover={false} sx={{ borderColor: alpha(neon.violet, 0.3) }}>
            <PanelTitle sub="Applies to the desktop app and this portal">Change password</PanelTitle>
            <Stack component="form" spacing={2} onSubmit={(e) => { e.preventDefault(); setPwDone(true); setPw(''); }}>
              {pwDone && <Alert severity="success" variant="outlined" onClose={() => setPwDone(false)}>Password changed. Other sessions have been signed out.</Alert>}
              <PasswordField label="Current password" autoComplete="current-password" required />
              <Box>
                <PasswordField label="New password" autoComplete="new-password" value={pw} onChange={(e) => setPw(e.target.value)} required />
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mt: 1 }}>
                  <LinearProgress variant="determinate" value={pw ? (strength(pw) / 4) * 100 : 0} sx={{ flex: 1, height: 6, borderRadius: 99, bgcolor: alpha('#fff', 0.06), '& .MuiLinearProgress-bar': { bgcolor: lv.c, borderRadius: 99 } }} />
                  <Typography variant="caption" sx={{ color: lv.c, minWidth: 64, textAlign: 'right' }}>{pw ? lv.l : ''}</Typography>
                </Box>
                <Typography variant="caption" color="text.secondary">8+ characters with upper & lower case, a number and a symbol.</Typography>
              </Box>
              <PasswordField label="Confirm new password" autoComplete="new-password" required />
              <Button type="submit" variant="contained" startIcon={<LockResetRounded />}>Update password</Button>
            </Stack>
          </GlassCard>
        </Reveal>
      </Grid>
    </Grid>
  );
}
