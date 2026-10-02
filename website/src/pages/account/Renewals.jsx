import { Link as RouterLink } from 'react-router-dom';
import Box from '@mui/material/Box';
import Table from '@mui/material/Table';
import TableHead from '@mui/material/TableHead';
import TableBody from '@mui/material/TableBody';
import TableRow from '@mui/material/TableRow';
import TableCell from '@mui/material/TableCell';
import Grid from '@mui/material/Grid';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import IconButton from '@mui/material/IconButton';
import Tooltip from '@mui/material/Tooltip';
import { alpha } from '@mui/material/styles';
import ReceiptRounded from '@mui/icons-material/ReceiptRounded';
import GlassCard from '../../components/GlassCard';
import Reveal from '../../components/Reveal';
import { PanelTitle, StatusChip, mono } from './shared';
import { renewals, license } from '../../data/mockAccount';
import { neon } from '../../theme';

export default function Renewals() {
  const paid = renewals.filter((r) => r.status === 'Paid');
  const total = paid.reduce((s, r) => s + Number(r.amount.replace(/[^\d]/g, '')), 0);

  const summary = [
    { k: 'Renewals', v: paid.length, c: neon.cyan },
    { k: 'Total paid', v: `₹${total.toLocaleString('en-IN')}`, c: neon.violet },
    { k: 'Next renewal due', v: license.endDate, c: '#FFB547' },
  ];

  return (
    <>
      <Grid container spacing={2.5} sx={{ mb: 2.5 }}>
        {summary.map((s) => (
          <Grid key={s.k} size={{ xs: 12, sm: 4 }}>
            <GlassCard glow={s.c} sx={{ p: 2.5 }}>
              <Typography variant="body2" color="text.secondary">{s.k}</Typography>
              <Typography sx={{ fontFamily: '"Space Grotesk"', fontWeight: 700, fontSize: 28, color: s.c }}>{s.v}</Typography>
            </GlassCard>
          </Grid>
        ))}
      </Grid>
      <Reveal>
        <GlassCard hover={false} sx={{ p: { xs: 2, md: 3 } }}>
          <PanelTitle sub="Every purchase and extension on your account" action={<Button component={RouterLink} to="/account/license#extend" variant="contained" size="small">Extend licence</Button>}>
            Renewal history
          </PanelTitle>
          <Box sx={{ overflowX: 'auto' }}>
            <Table size="small" sx={{ minWidth: 820, '& td, & th': { borderColor: neon.line, py: 1.5 }, '& th': { color: 'text.secondary', fontFamily: mono, fontSize: 11, letterSpacing: '0.12em' } }}>
              <TableHead>
                <TableRow>
                  <TableCell>INVOICE</TableCell><TableCell>DATE</TableCell><TableCell>PLAN</TableCell><TableCell>PERIOD</TableCell><TableCell>METHOD</TableCell><TableCell align="right">AMOUNT</TableCell><TableCell>STATUS</TableCell><TableCell />
                </TableRow>
              </TableHead>
              <TableBody>
                {renewals.map((r) => (
                  <TableRow key={r.id} hover sx={{ '&:hover': { bgcolor: `${alpha(neon.cyan, 0.03)} !important` } }}>
                    <TableCell sx={{ fontFamily: mono, fontSize: 13, color: neon.cyan }}>{r.id}</TableCell>
                    <TableCell sx={{ fontFamily: mono, fontSize: 13 }}>{r.date}</TableCell>
                    <TableCell>{r.plan}</TableCell>
                    <TableCell sx={{ fontFamily: mono, fontSize: 12.5, color: 'text.secondary' }}>{r.period}</TableCell>
                    <TableCell sx={{ color: 'text.secondary' }}>{r.method}</TableCell>
                    <TableCell align="right" sx={{ fontWeight: 600 }}>{r.amount}</TableCell>
                    <TableCell><StatusChip status={r.status} /></TableCell>
                    <TableCell align="right">
                      <Tooltip title="Download receipt"><span><IconButton size="small" disabled={r.status !== 'Paid'} aria-label={`Download receipt ${r.id}`}><ReceiptRounded fontSize="small" /></IconButton></span></Tooltip>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Box>
        </GlassCard>
      </Reveal>
    </>
  );
}
