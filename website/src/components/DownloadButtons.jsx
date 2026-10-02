import Button from '@mui/material/Button';
import Stack from '@mui/material/Stack';
import Box from '@mui/material/Box';
import Apple from '@mui/icons-material/Apple';
import Microsoft from '@mui/icons-material/Microsoft';
import { site } from '../config/site';
import useOS from './useOS';

const platforms = {
  windows: { ...site.downloads.windows, icon: Microsoft },
  mac: { ...site.downloads.mac, icon: Apple },
};

// Two download buttons; the one matching the visitor's OS is shown first and filled.
export default function DownloadButtons({ size = 'large', justify = 'flex-start', showMeta = true }) {
  const os = useOS();
  const order = os === 'mac' ? ['mac', 'windows'] : ['windows', 'mac'];

  return (
    <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ alignItems: { xs: 'stretch', sm: 'center' }, justifyContent: justify }}>
      {order.map((key, i) => {
        const p = platforms[key];
        const Icon = p.icon;
        return (
          <Button
            key={key}
            href={p.url}
            download={p.fileName}
            size={size}
            variant={i === 0 ? 'contained' : 'outlined'}
            startIcon={<Icon />}
            sx={{ minWidth: 230, justifyContent: 'flex-start' }}
          >
            <Box sx={{ textAlign: 'left', lineHeight: 1.15 }}>
              <Box component="span" sx={{ display: 'block' }}>Download for {p.label}</Box>
              {showMeta && (
                <Box component="span" sx={{ display: 'block', fontSize: 11, fontFamily: '"JetBrains Mono", monospace', opacity: 0.75, fontWeight: 500 }}>
                  v{site.version} · {p.size}
                </Box>
              )}
            </Box>
          </Button>
        );
      })}
    </Stack>
  );
}
