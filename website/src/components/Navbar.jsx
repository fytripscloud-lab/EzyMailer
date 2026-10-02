import { useEffect, useState } from 'react';
import { NavLink, Link as RouterLink } from 'react-router-dom';
import AppBar from '@mui/material/AppBar';
import Toolbar from '@mui/material/Toolbar';
import Container from '@mui/material/Container';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import IconButton from '@mui/material/IconButton';
import Drawer from '@mui/material/Drawer';
import List from '@mui/material/List';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemText from '@mui/material/ListItemText';
import MenuRounded from '@mui/icons-material/MenuRounded';
import CloseRounded from '@mui/icons-material/CloseRounded';
import DownloadRounded from '@mui/icons-material/DownloadRounded';
import { alpha } from '@mui/material/styles';
import Logo from './Logo';
import { neon } from '../theme';

const links = [
  { to: '/', label: 'Home', end: true },
  { to: '/features', label: 'Features' },
  { to: '/download', label: 'Download' },
  { to: '/faq', label: 'FAQ' },
  { to: '/about', label: 'About' },
  { to: '/contact', label: 'Contact' },
];

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <AppBar
      position="fixed"
      elevation={0}
      sx={{
        background: scrolled ? alpha('#05070F', 0.72) : 'transparent',
        backdropFilter: scrolled ? 'blur(18px) saturate(140%)' : 'none',
        borderBottom: `1px solid ${scrolled ? neon.line : 'transparent'}`,
        transition: 'all .3s ease',
      }}
    >
      <Container maxWidth="lg">
        <Toolbar disableGutters sx={{ minHeight: { xs: 64, md: 76 }, gap: 2 }}>
          <Logo />
          <Box component="nav" sx={{ display: { xs: 'none', md: 'flex' }, gap: 0.5, mx: 'auto' }}>
            {links.map((l) => (
              <Button
                key={l.to}
                component={NavLink}
                to={l.to}
                end={l.end}
                color="inherit"
                sx={{
                  color: 'text.secondary',
                  px: 2,
                  py: 0.75,
                  fontFamily: '"Inter", sans-serif',
                  fontWeight: 500,
                  '&:hover': { color: 'text.primary', bgcolor: alpha(neon.cyan, 0.06) },
                  '&.active': { color: neon.cyan, bgcolor: alpha(neon.cyan, 0.08) },
                }}
              >
                {l.label}
              </Button>
            ))}
          </Box>
          <Button
            component={RouterLink}
            to="/login"
            color="inherit"
            sx={{ display: { xs: 'none', md: 'inline-flex' }, color: 'text.primary', fontFamily: '"Inter", sans-serif', fontWeight: 500 }}
          >
            Log in
          </Button>
          <Button
            component={RouterLink}
            to="/download"
            variant="contained"
            startIcon={<DownloadRounded />}
            sx={{ display: { xs: 'none', md: 'inline-flex' }, py: 0.9 }}
          >
            Get the app
          </Button>
          <IconButton
            aria-label="Open menu"
            onClick={() => setOpen(true)}
            sx={{ display: { md: 'none' }, ml: 'auto', color: 'text.primary' }}
          >
            <MenuRounded />
          </IconButton>
        </Toolbar>
      </Container>

      <Drawer
        anchor="right"
        open={open}
        onClose={() => setOpen(false)}
        slotProps={{ paper: { sx: { width: 'min(320px, 85vw)', bgcolor: '#070b18', borderLeft: `1px solid ${neon.line}` } } }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', p: 2 }}>
          <Logo size={28} />
          <IconButton aria-label="Close menu" onClick={() => setOpen(false)}>
            <CloseRounded />
          </IconButton>
        </Box>
        <List sx={{ px: 1 }}>
          {links.map((l) => (
            <ListItemButton
              key={l.to}
              component={NavLink}
              to={l.to}
              end={l.end}
              onClick={() => setOpen(false)}
              sx={{ borderRadius: 2, '&.active': { color: neon.cyan, bgcolor: alpha(neon.cyan, 0.08) } }}
            >
              <ListItemText primary={l.label} />
            </ListItemButton>
          ))}
        </List>
        <Box sx={{ p: 2, mt: 'auto', display: 'grid', gap: 1.25 }}>
          <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1.25 }}>
            <Button component={RouterLink} to="/login" variant="outlined" onClick={() => setOpen(false)}>Log in</Button>
            <Button component={RouterLink} to="/register" variant="outlined" onClick={() => setOpen(false)}>Register</Button>
          </Box>
          <Button fullWidth component={RouterLink} to="/download" variant="contained" startIcon={<DownloadRounded />} onClick={() => setOpen(false)}>
            Get the app
          </Button>
        </Box>
      </Drawer>
    </AppBar>
  );
}
