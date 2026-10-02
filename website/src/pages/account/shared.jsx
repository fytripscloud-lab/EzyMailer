import { useState } from 'react';
import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip';
import Typography from '@mui/material/Typography';
import Dialog from '@mui/material/Dialog';
import DialogContent from '@mui/material/DialogContent';
import Button from '@mui/material/Button';
import Grid from '@mui/material/Grid';
import Stack from '@mui/material/Stack';
import Divider from '@mui/material/Divider';
import IconButton from '@mui/material/IconButton';
import { alpha } from '@mui/material/styles';
import CloseRounded from '@mui/icons-material/CloseRounded';
import CheckCircleRounded from '@mui/icons-material/CheckCircleRounded';
import { plans, license } from '../../data/mockAccount';
import { neon } from '../../theme';

export const mono = '"JetBrains Mono", monospace';

export function StatusChip({ status }) {
  const s = status.toLowerCase();
  const color = s.startsWith('success') || s === 'paid' || s === 'active' ? neon.green
    : s.startsWith('blocked') || s.startsWith('failed') || s === 'expired' ? '#FF6B81'
    : s === 'converted' ? neon.violet : '#FFB547';
  return (
    <Chip
      size="small"
      label={status}
      icon={<Box component="span" sx={{ width: 6, height: 6, borderRadius: '50%', bgcolor: color, ml: '8px !important', boxShadow: `0 0 8px ${color}` }} />}
      sx={{ bgcolor: alpha(color, 0.1), color, border: `1px solid ${alpha(color, 0.3)}`, fontWeight: 500 }}
    />
  );
}

export function PanelTitle({ children, action, sub }) {
  return (
    <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2, mb: 2.5 }}>
      <Box sx={{ flex: 1 }}>
        <Typography variant="h6">{children}</Typography>
        {sub && <Typography variant="body2" color="text.secondary" sx={{ mt: 0.25 }}>{sub}</Typography>}
      </Box>
      {action}
    </Box>
  );
}

export function addMonths(dateStr, months) {
  const d = new Date(`${dateStr}T00:00:00`);
  d.setMonth(d.getMonth() + months);
  return d.toISOString().slice(0, 10);
}

export function PlanPicker({ value, onChange }) {
  return (
    <Grid container spacing={1.5}>
      {plans.map((p) => {
        const on = p.id === value;
        return (
          <Grid key={p.id} size={{ xs: 6, md: 3 }}>
            <Box
              component="button"
              type="button"
              onClick={() => onChange(p.id)}
              aria-pressed={on}
              sx={{
                all: 'unset', boxSizing: 'border-box', cursor: 'pointer', width: '100%', height: '100%', position: 'relative',
                p: 2, borderRadius: 3, textAlign: 'left',
                border: `1px solid ${on ? neon.cyan : neon.line}`,
                bgcolor: on ? alpha(neon.cyan, 0.08) : alpha('#0B1020', 0.5),
                boxShadow: on ? `0 0 30px -8px ${alpha(neon.cyan, 0.7)}` : 'none',
                transition: 'all .2s',
                '&:hover': { borderColor: alpha(neon.cyan, 0.6) },
                '&:focus-visible': { outline: `2px solid ${neon.cyan}`, outlineOffset: 2 },
              }}
            >
              {p.tag && <Box sx={{ position: 'absolute', top: -9, right: 10, px: 1, borderRadius: 99, fontSize: 10.5, fontFamily: mono, bgcolor: neon.violet, color: '#fff' }}>{p.tag}</Box>}
              <Typography sx={{ fontWeight: 600 }}>{p.label}</Typography>
              <Typography sx={{ fontFamily: '"Space Grotesk"', fontWeight: 700, fontSize: 24, color: on ? neon.cyan : 'text.primary', mt: 0.5 }}>{p.price}</Typography>
              <Typography variant="body2" color="text.secondary">{p.perMonth}</Typography>
            </Box>
          </Grid>
        );
      })}
    </Grid>
  );
}

// DESIGN ONLY — confirms and shows a success state; no payment happens.
export function ExtendDialog({ open, onClose, planId }) {
  const [done, setDone] = useState(false);
  const plan = plans.find((p) => p.id === planId) ?? plans[0];
  const close = () => { onClose(); setTimeout(() => setDone(false), 300); };
  const row = (k, v, strong) => (
    <Box sx={{ display: 'flex', justifyContent: 'space-between', py: 0.75 }}>
      <Typography color="text.secondary">{k}</Typography>
      <Typography sx={{ fontWeight: strong ? 700 : 500, fontFamily: strong ? '"Space Grotesk"' : undefined, fontSize: strong ? 20 : undefined }}>{v}</Typography>
    </Box>
  );
  return (
    <Dialog open={open} onClose={close} fullWidth maxWidth="xs" slotProps={{ paper: { sx: { bgcolor: '#0B1020', border: `1px solid ${alpha(neon.cyan, 0.3)}`, borderRadius: 4 } } }}>
      <DialogContent sx={{ p: 3.5, position: 'relative' }}>
        <IconButton onClick={close} aria-label="Close" sx={{ position: 'absolute', top: 12, right: 12 }}><CloseRounded /></IconButton>
        {done ? (
          <Stack spacing={1.5} sx={{ alignItems: 'center', textAlign: 'center', py: 3 }}>
            <CheckCircleRounded sx={{ fontSize: 64, color: neon.green, filter: `drop-shadow(0 0 16px ${neon.green})` }} />
            <Typography variant="h5">Licence extended</Typography>
            <Typography color="text.secondary">Valid until {addMonths(license.endDate, plan.months)}. A receipt has been added to your renewal history.</Typography>
            <Button variant="contained" onClick={close} sx={{ mt: 1 }}>Done</Button>
          </Stack>
        ) : (
          <>
            <Typography variant="h5">Confirm extension</Typography>
            <Typography color="text.secondary" sx={{ mt: 0.5, mb: 2.5 }}>Your new period starts when the current one ends.</Typography>
            {row('Plan', `${license.plan} · ${plan.label}`)}
            {row('Current expiry', license.endDate)}
            {row('New expiry', addMonths(license.endDate, plan.months))}
            <Divider sx={{ my: 1.5 }} />
            {row('Total', plan.price, true)}
            <Button variant="contained" size="large" fullWidth sx={{ mt: 3 }} onClick={() => setDone(true)}>Pay {plan.price}</Button>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', textAlign: 'center', mt: 1.5 }}>Secure payment · UPI, cards and net banking</Typography>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
