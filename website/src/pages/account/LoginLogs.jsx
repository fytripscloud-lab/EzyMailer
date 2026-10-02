import { useState } from 'react';
import Box from '@mui/material/Box';
import Table from '@mui/material/Table';
import TableHead from '@mui/material/TableHead';
import TableBody from '@mui/material/TableBody';
import TableRow from '@mui/material/TableRow';
import TableCell from '@mui/material/TableCell';
import ToggleButton from '@mui/material/ToggleButton';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';
import Grid from '@mui/material/Grid';
import Typography from '@mui/material/Typography';
import { alpha } from '@mui/material/styles';
import GlassCard from '../../components/GlassCard';
import Reveal from '../../components/Reveal';
import { PanelTitle, StatusChip, mono } from './shared';
import { loginLogs } from '../../data/mockAccount';
import { neon } from '../../theme';

const filters = { all: () => true, success: (l) => l.status === 'Success', failed: (l) => l.status !== 'Success' };

export default function LoginLogs() {
  const [f, setF] = useState('all');
  const rows = loginLogs.filter(filters[f]);
  const failed = loginLogs.filter(filters.failed).length;

  const summary = [
    { k: 'Sign-ins (7 days)', v: loginLogs.length, c: neon.cyan },
    { k: 'Successful', v: loginLogs.length - failed, c: neon.green },
    { k: 'Failed or blocked', v: failed, c: '#FF6B81' },
  ];

  return (
    <>
      <Grid container spacing={2.5} sx={{ mb: 2.5 }}>
        {summary.map((s) => (
          <Grid key={s.k} size={{ xs: 12, sm: 4 }}>
            <GlassCard glow={s.c} sx={{ p: 2.5 }}>
              <Typography variant="body2" color="text.secondary">{s.k}</Typography>
              <Typography sx={{ fontFamily: '"Space Grotesk"', fontWeight: 700, fontSize: 32, color: s.c }}>{s.v}</Typography>
            </GlassCard>
          </Grid>
        ))}
      </Grid>
      <Reveal>
        <GlassCard hover={false} sx={{ p: { xs: 2, md: 3 } }}>
          <PanelTitle
            sub="Every sign-in to the desktop app and this portal"
            action={
              <ToggleButtonGroup size="small" exclusive value={f} onChange={(_, v) => v && setF(v)} sx={{ '& .MuiToggleButton-root': { textTransform: 'none', px: 1.5 } }}>
                <ToggleButton value="all">All</ToggleButton>
                <ToggleButton value="success">Success</ToggleButton>
                <ToggleButton value="failed">Failed</ToggleButton>
              </ToggleButtonGroup>
            }
          >
            Login logs
          </PanelTitle>
          <Box sx={{ overflowX: 'auto' }}>
            <Table size="small" sx={{ minWidth: 760, '& td, & th': { borderColor: neon.line, py: 1.5 }, '& th': { color: 'text.secondary', fontFamily: mono, fontSize: 11, letterSpacing: '0.12em' } }}>
              <TableHead>
                <TableRow>
                  <TableCell>TIME</TableCell><TableCell>DEVICE</TableCell><TableCell>SOURCE</TableCell><TableCell>IP</TableCell><TableCell>LOCATION</TableCell><TableCell>STATUS</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {rows.map((l) => (
                  <TableRow key={l.id} hover sx={{ '&:hover': { bgcolor: `${alpha(neon.cyan, 0.03)} !important` } }}>
                    <TableCell sx={{ fontFamily: mono, fontSize: 13 }}>{l.time}</TableCell>
                    <TableCell>{l.device}</TableCell>
                    <TableCell sx={{ color: 'text.secondary' }}>{l.app}</TableCell>
                    <TableCell sx={{ fontFamily: mono, fontSize: 13, color: 'text.secondary' }}>{l.ip}</TableCell>
                    <TableCell sx={{ color: 'text.secondary' }}>{l.location}</TableCell>
                    <TableCell><StatusChip status={l.status} /></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Box>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>Don’t recognise a sign-in? Change your password right away from Profile & security.</Typography>
        </GlassCard>
      </Reveal>
    </>
  );
}
