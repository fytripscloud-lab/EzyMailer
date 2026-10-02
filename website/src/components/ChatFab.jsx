import { useState } from 'react';
import Box from '@mui/material/Box';
import Fab from '@mui/material/Fab';
import Tooltip from '@mui/material/Tooltip';
import { alpha } from '@mui/material/styles';
import Telegram from '@mui/icons-material/Telegram';
import { site } from '../config/site';
import { neon } from '../theme';

const tg = '#29A9EB';

// Floating "Chat with us" button that opens the Telegram support chat.
export default function ChatFab() {
  const [hover, setHover] = useState(false);
  return (
    <Box sx={{ position: 'fixed', right: { xs: 16, md: 28 }, bottom: { xs: 16, md: 28 }, zIndex: 1200 }}>
      <Box aria-hidden sx={{ position: 'absolute', inset: -6, borderRadius: 99, border: `2px solid ${alpha(tg, 0.5)}`, animation: 'pulseGlow 2s ease-in-out infinite', pointerEvents: 'none' }} />
      <Tooltip title="Chat with us on Telegram" placement="left">
        <Fab
          variant={hover ? 'extended' : 'circular'}
          component="a"
          href={site.telegramUrl}
          target="_blank"
          rel="noopener noreferrer"
          aria-label="Chat with us on Telegram"
          onMouseEnter={() => setHover(true)}
          onMouseLeave={() => setHover(false)}
          sx={{
            bgcolor: tg,
            color: '#fff',
            gap: 1,
            fontFamily: '"Space Grotesk", sans-serif',
            fontWeight: 600,
            textTransform: 'none',
            boxShadow: `0 10px 40px -6px ${alpha(tg, 0.8)}, 0 0 0 1px ${alpha('#fff', 0.15)} inset`,
            transition: 'all .25s ease',
            '&:hover': { bgcolor: '#1F98D8', boxShadow: `0 14px 50px -6px ${alpha(tg, 1)}, 0 0 24px ${alpha(neon.cyan, 0.4)}` },
          }}
        >
          <Telegram />
          {hover && 'Chat with us'}
        </Fab>
      </Tooltip>
    </Box>
  );
}
