import Box from '@mui/material/Box';
import { alpha } from '@mui/material/styles';
import { neon } from '../theme';

// Frosted panel with a gradient hairline border and an optional hover glow.
export default function GlassCard({ children, glow = neon.cyan, hover = true, sx, ...rest }) {
  return (
    <Box
      sx={{
        position: 'relative',
        height: '100%',
        p: { xs: 3, md: 3.5 },
        borderRadius: 4,
        background: `linear-gradient(160deg, ${alpha('#121a33', 0.75)}, ${alpha('#070b18', 0.75)})`,
        backdropFilter: 'blur(14px)',
        border: `1px solid ${neon.line}`,
        transition: 'transform .35s cubic-bezier(.2,.7,.2,1), border-color .35s, box-shadow .35s',
        ...(hover && {
          '&:hover': {
            transform: 'translateY(-6px)',
            borderColor: alpha(glow, 0.5),
            boxShadow: `0 20px 60px -20px ${alpha(glow, 0.45)}, inset 0 0 0 1px ${alpha(glow, 0.15)}`,
          },
        }),
        ...sx,
      }}
      {...rest}
    >
      {children}
    </Box>
  );
}
