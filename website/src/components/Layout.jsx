import { Outlet } from 'react-router-dom';
import Box from '@mui/material/Box';
import Navbar from './Navbar';
import Footer from './Footer';
import Background from './Background';
import ScrollToTop from './ScrollToTop';
import ChatFab from './ChatFab';

export default function Layout() {
  return (
    <Box sx={{ overflowX: 'clip' }}>
      <ScrollToTop />
      <Background />
      <Navbar />
      <Box component="main" sx={{ pt: { xs: 8, md: 9.5 }, minHeight: '70vh' }}>
        <Outlet />
      </Box>
      <Footer />
      <ChatFab />
    </Box>
  );
}
