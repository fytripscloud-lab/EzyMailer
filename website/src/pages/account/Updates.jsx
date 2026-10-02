import { useState } from 'react';
import Box from '@mui/material/Box';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import TextField from '@mui/material/TextField';
import InputAdornment from '@mui/material/InputAdornment';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import Grid from '@mui/material/Grid';
import { alpha } from '@mui/material/styles';
import SearchRounded from '@mui/icons-material/SearchRounded';
import PushPinRounded from '@mui/icons-material/PushPinRounded';
import SystemUpdateAltRounded from '@mui/icons-material/SystemUpdateAltRounded';
import GavelRounded from '@mui/icons-material/GavelRounded';
import MailRounded from '@mui/icons-material/MailRounded';
import NewspaperRounded from '@mui/icons-material/NewspaperRounded';
import GlassCard from '../../components/GlassCard';
import Reveal from '../../components/Reveal';
import { updates, updateCategories } from '../../data/mockAccount';
import { mono } from './shared';
import { neon } from '../../theme';

const meta = {
  app: { icon: SystemUpdateAltRounded, color: neon.cyan },
  rules: { icon: GavelRounded, color: '#FFB547' },
  google: { icon: MailRounded, color: neon.green },
  news: { icon: NewspaperRounded, color: neon.violet },
};

export default function Updates() {
  const [tab, setTab] = useState('all');
  const [q, setQ] = useState('');
  const term = q.trim().toLowerCase();
  const list = updates
    .filter((u) => tab === 'all' || u.cat === tab)
    .filter((u) => !term || `${u.title} ${u.body}`.toLowerCase().includes(term))
    .sort((a, b) => (b.pinned ? 1 : 0) - (a.pinned ? 1 : 0) || b.date.localeCompare(a.date));

  return (
    <>
      <Box sx={{ display: 'flex', flexDirection: { xs: 'column', md: 'row' }, gap: 2, alignItems: { md: 'center' }, mb: 3 }}>
        <Tabs
          value={tab}
          onChange={(_, v) => setTab(v)}
          variant="scrollable"
          allowScrollButtonsMobile
          sx={{ flex: 1, minHeight: 0, '& .MuiTab-root': { textTransform: 'none', minHeight: 40, fontWeight: 500 }, '& .MuiTabs-indicator': { bgcolor: neon.cyan, boxShadow: `0 0 10px ${neon.cyan}` } }}
        >
          <Tab value="all" label={`All (${updates.length})`} />
          {updateCategories.map((c) => <Tab key={c.id} value={c.id} label={c.label} />)}
        </Tabs>
        <TextField
          size="small"
          placeholder="Search updates"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          sx={{ width: { md: 280 } }}
          slotProps={{ input: { startAdornment: <InputAdornment position="start"><SearchRounded fontSize="small" /></InputAdornment> } }}
        />
      </Box>

      <Grid container spacing={2}>
        {list.map((u, i) => {
          const m = meta[u.cat];
          const Icon = m.icon;
          return (
            <Grid key={u.id} size={{ xs: 12, md: 6 }}>
              <Reveal delay={(i % 2) * 60} sx={{ height: '100%' }}>
                <GlassCard glow={m.color} sx={{ p: 3, ...(u.pinned && { borderColor: alpha(m.color, 0.4) }) }}>
                  <Stack direction="row" spacing={1.5} sx={{ alignItems: 'center', mb: 1.5 }}>
                    <Box sx={{ width: 36, height: 36, borderRadius: 2.5, display: 'grid', placeItems: 'center', bgcolor: alpha(m.color, 0.12), color: m.color }}><Icon fontSize="small" /></Box>
                    <Chip size="small" label={u.tag} sx={{ bgcolor: alpha(m.color, 0.1), color: m.color, border: `1px solid ${alpha(m.color, 0.3)}` }} />
                    {u.pinned && <PushPinRounded sx={{ fontSize: 16, color: 'text.secondary', transform: 'rotate(30deg)' }} />}
                    <Typography variant="caption" color="text.secondary" sx={{ ml: 'auto !important', fontFamily: mono }}>{u.date}</Typography>
                  </Stack>
                  <Typography variant="h6" sx={{ fontSize: 17, mb: 0.75 }}>{u.title}</Typography>
                  <Typography color="text.secondary" sx={{ lineHeight: 1.7, fontSize: 14.5 }}>{u.body}</Typography>
                </GlassCard>
              </Reveal>
            </Grid>
          );
        })}
        {list.length === 0 && (
          <Grid size={12}><Typography color="text.secondary" sx={{ textAlign: 'center', py: 8 }}>No updates match “{q}”.</Typography></Grid>
        )}
      </Grid>
    </>
  );
}
