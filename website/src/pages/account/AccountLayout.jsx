import { useState } from 'react';
import { NavLink, Outlet, Link as RouterLink, useLocation, useNavigate } from 'react-router-dom';
import Box from '@mui/material/Box';
import Drawer from '@mui/material/Drawer';
import List from '@mui/material/List';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import IconButton from '@mui/material/IconButton';
import Avatar from '@mui/material/Avatar';
import Badge from '@mui/material/Badge';
import Menu from '@mui/material/Menu';
import MenuItem from '@mui/material/MenuItem';
import Divider from '@mui/material/Divider';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import { alpha } from '@mui/material/styles';
import DashboardRounded from '@mui/icons-material/DashboardRounded';
import WorkspacePremiumRounded from '@mui/icons-material/WorkspacePremiumRounded';
import CampaignRounded from '@mui/icons-material/CampaignRounded';
import PersonRounded from '@mui/icons-material/PersonRounded';
import HistoryRounded from '@mui/icons-material/HistoryRounded';
import ReceiptLongRounded from '@mui/icons-material/ReceiptLongRounded';
import MenuRounded from '@mui/icons-material/MenuRounded';
import NotificationsRounded from '@mui/icons-material/NotificationsRounded';
import LogoutRounded from '@mui/icons-material/LogoutRounded';
import DownloadRounded from '@mui/icons-material/DownloadRounded';
import Logo from '../../components/Logo';
import Background from '../../components/Background';
import ChatFab from '../../components/ChatFab';
import ScrollToTop from '../../components/ScrollToTop';
import { user, license } from '../../data/mockAccount';
import { neon } from '../../theme';

const W = 260;

export const accountNav = [
  { to: '/account', label: 'Dashboard', icon: DashboardRounded, end: true },
  { to: '/account/license', label: 'Licence', icon: WorkspacePremiumRounded },
  { to: '/account/updates', label: 'Updates & news', icon: CampaignRounded, badge: 3 },
  { to: '/account/profile', label: 'Profile & security', icon: PersonRounded },
  { to: '/account/logins', label: 'Login logs', icon: HistoryRounded },
  { to: '/account/renewals', label: 'Renewal history', icon: ReceiptLongRounded },
];

function SideNav({ onNavigate }) {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', p: 2 }}>
      <Box sx={{ px: 1, py: 1.5 }}><Logo size={30} /></Box>
      <List sx={{ mt: 2, flex: 1 }}>
        {accountNav.map((n) => {
          const Icon = n.icon;
          return (
            <ListItemButton
              key={n.to}
              component={NavLink}
              to={n.to}
              end={n.end}
              onClick={onNavigate}
              sx={{
                borderRadius: 3, mb: 0.5, color: 'text.secondary', border: '1px solid transparent',
                '& .MuiListItemIcon-root': { color: 'inherit', minWidth: 40 },
                '&:hover': { color: 'text.primary', bgcolor: alpha(neon.cyan, 0.05) },
                '&.active': { color: neon.cyan, bgcolor: alpha(neon.cyan, 0.08), borderColor: alpha(neon.cyan, 0.25), boxShadow: `inset 3px 0 0 ${neon.cyan}` },
              }}
            >
              <ListItemIcon><Icon fontSize="small" /></ListItemIcon>
              <ListItemText primary={n.label} slotProps={{ primary: { fontSize: 14.5, fontWeight: 500 } }} />
              {n.badge && <Box sx={{ fontFamily: '"JetBrains Mono", monospace', fontSize: 11, px: 0.9, borderRadius: 99, bgcolor: neon.violet, color: '#fff' }}>{n.badge}</Box>}
            </ListItemButton>
          );
        })}
      </List>
      <Box sx={{ p: 2, borderRadius: 4, border: `1px solid ${alpha(neon.violet, 0.35)}`, background: `linear-gradient(160deg, ${alpha(neon.violet, 0.18)}, ${alpha(neon.cyan, 0.06)})` }}>
        <Typography variant="overline" sx={{ color: neon.violet }}>{license.plan} licence</Typography>
        <Typography sx={{ fontWeight: 600, mt: 0.5 }}>{license.daysLeft} days left</Typography>
        <Button component={RouterLink} to="/account/license#extend" onClick={onNavigate} size="small" variant="contained" fullWidth sx={{ mt: 1.5 }}>Extend licence</Button>
      </Box>
    </Box>
  );
}

export default function AccountLayout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [anchor, setAnchor] = useState(null);
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const current = accountNav.find((n) => (n.end ? pathname === n.to : pathname.startsWith(n.to)));

  const paper = { width: W, bgcolor: alpha('#070B16', 0.85), backdropFilter: 'blur(16px)', borderRight: `1px solid ${neon.line}` };

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', overflowX: 'clip' }}>
      <ScrollToTop />
      <Background />
      <Drawer variant="permanent" sx={{ display: { xs: 'none', md: 'block' }, width: W, flexShrink: 0 }} slotProps={{ paper: { sx: paper } }}>
        <SideNav />
      </Drawer>
      <Drawer variant="temporary" open={mobileOpen} onClose={() => setMobileOpen(false)} sx={{ display: { md: 'none' } }} slotProps={{ paper: { sx: paper } }}>
        <SideNav onNavigate={() => setMobileOpen(false)} />
      </Drawer>

      <Box sx={{ flex: 1, minWidth: 0 }}>
        <Box
          component="header"
          sx={{ position: 'sticky', top: 0, zIndex: 10, display: 'flex', alignItems: 'center', gap: 1.5, px: { xs: 2, md: 4 }, height: { xs: 64, md: 72 }, bgcolor: alpha('#05070F', 0.75), backdropFilter: 'blur(16px)', borderBottom: `1px solid ${neon.line}` }}
        >
          <IconButton onClick={() => setMobileOpen(true)} sx={{ display: { md: 'none' } }} aria-label="Open menu"><MenuRounded /></IconButton>
          <Typography variant="h6" sx={{ fontSize: { xs: 17, md: 20 } }}>{current?.label ?? 'Account'}</Typography>
          <Box sx={{ ml: 'auto', display: 'flex', alignItems: 'center', gap: 1 }}>
            <Button component={RouterLink} to="/download" startIcon={<DownloadRounded />} size="small" variant="outlined" sx={{ display: { xs: 'none', sm: 'inline-flex' } }}>Download app</Button>
            <IconButton component={RouterLink} to="/account/updates" aria-label="Updates">
              <Badge badgeContent={3} color="secondary"><NotificationsRounded /></Badge>
            </IconButton>
            <IconButton onClick={(e) => setAnchor(e.currentTarget)} aria-label="Account menu">
              <Avatar sx={{ width: 36, height: 36, fontSize: 14, fontWeight: 700, color: '#021018', background: `linear-gradient(135deg, ${neon.cyan}, ${neon.violet})` }}>{user.avatarInitials}</Avatar>
            </IconButton>
          </Box>
          <Menu anchorEl={anchor} open={Boolean(anchor)} onClose={() => setAnchor(null)} slotProps={{ paper: { sx: { minWidth: 220, bgcolor: '#0B1020', border: `1px solid ${neon.line}` } } }}>
            <Box sx={{ px: 2, py: 1.25 }}>
              <Typography sx={{ fontWeight: 600 }}>{user.name}</Typography>
              <Typography variant="body2" color="text.secondary">{user.email}</Typography>
            </Box>
            <Divider />
            <MenuItem component={RouterLink} to="/account/profile" onClick={() => setAnchor(null)}>Profile & security</MenuItem>
            <MenuItem component={RouterLink} to="/" onClick={() => setAnchor(null)}>Back to website</MenuItem>
            <Divider />
            <MenuItem onClick={() => navigate('/login')} sx={{ color: '#FF6B81', gap: 1 }}><LogoutRounded fontSize="small" /> Sign out</MenuItem>
          </Menu>
        </Box>

        <Box component="main" sx={{ p: { xs: 2, sm: 3, md: 4 }, pb: { xs: 12, md: 14 }, maxWidth: 1280, mx: 'auto' }}>
          <Outlet />
        </Box>
      </Box>
      <ChatFab />
    </Box>
  );
}
