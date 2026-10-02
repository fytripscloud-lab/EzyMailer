import { createTheme, alpha } from '@mui/material/styles';

export const neon = {
  cyan: '#1EE8FF',
  blue: '#0A6CFF',
  violet: '#8B5CF6',
  pink: '#FF4FD8',
  green: '#3DFFA8',
  bg: '#05070F',
  panel: '#0B1020',
  line: 'rgba(120, 160, 255, 0.14)',
};

export const gradientText = {
  background: `linear-gradient(92deg, ${neon.cyan} 0%, #6AA8FF 45%, ${neon.violet} 100%)`,
  WebkitBackgroundClip: 'text',
  backgroundClip: 'text',
  WebkitTextFillColor: 'transparent',
};

const display = '"Space Grotesk", "Inter", system-ui, sans-serif';

const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: { main: neon.cyan, contrastText: '#021018' },
    secondary: { main: neon.violet },
    background: { default: neon.bg, paper: neon.panel },
    text: { primary: '#E8EEFF', secondary: '#9AA7C7' },
    divider: neon.line,
  },
  shape: { borderRadius: 4 },
  typography: {
    fontFamily: '"Inter", system-ui, -apple-system, "Segoe UI", sans-serif',
    h1: { fontFamily: display, fontWeight: 700, letterSpacing: '-0.035em', lineHeight: 1.02 },
    h2: { fontFamily: display, fontWeight: 700, letterSpacing: '-0.03em', lineHeight: 1.08 },
    h3: { fontFamily: display, fontWeight: 700, letterSpacing: '-0.02em' },
    h4: { fontFamily: display, fontWeight: 600, letterSpacing: '-0.015em' },
    h5: { fontFamily: display, fontWeight: 600 },
    h6: { fontFamily: display, fontWeight: 600 },
    overline: { fontFamily: '"JetBrains Mono", monospace', letterSpacing: '0.2em', fontWeight: 500 },
    button: { fontFamily: display, fontWeight: 600, textTransform: 'none', letterSpacing: '0.01em' },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        html: { scrollBehavior: 'smooth' },
        body: { backgroundColor: neon.bg, overflowX: 'hidden' },
        '::selection': { background: alpha(neon.cyan, 0.3) },
        '@media (prefers-reduced-motion: reduce)': {
          '*, *::before, *::after': { animation: 'none !important', transition: 'none !important' },
        },
      },
    },
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: {
        root: { borderRadius: 999, paddingInline: 22, paddingBlock: 10 },
        sizeLarge: { paddingInline: 30, paddingBlock: 14, fontSize: '1rem' },
        containedPrimary: {
          background: `linear-gradient(100deg, ${neon.cyan}, #4DA3FF 55%, ${neon.violet})`,
          color: '#020812',
          boxShadow: `0 0 0 1px ${alpha(neon.cyan, 0.4)}, 0 10px 40px -8px ${alpha(neon.cyan, 0.55)}`,
          transition: 'transform .2s ease, box-shadow .2s ease',
          '&:hover': {
            transform: 'translateY(-2px)',
            boxShadow: `0 0 0 1px ${alpha(neon.cyan, 0.7)}, 0 16px 50px -6px ${alpha(neon.cyan, 0.75)}`,
          },
        },
        outlined: {
          borderColor: alpha(neon.cyan, 0.35),
          backdropFilter: 'blur(8px)',
          backgroundColor: alpha('#0B1020', 0.4),
          '&:hover': { borderColor: neon.cyan, backgroundColor: alpha(neon.cyan, 0.08) },
        },
      },
    },
    MuiPaper: { styleOverrides: { root: { backgroundImage: 'none' } } },
    MuiChip: { styleOverrides: { root: { fontFamily: '"JetBrains Mono", monospace', fontSize: 12 } } },
    MuiAccordion: {
      styleOverrides: {
        root: {
          background: alpha('#0B1020', 0.6),
          border: `1px solid ${neon.line}`,
          borderRadius: '14px !important',
          '&::before': { display: 'none' },
          '&.Mui-expanded': { borderColor: alpha(neon.cyan, 0.4) },
        },
      },
    },
    MuiTextField: { defaultProps: { variant: 'outlined', fullWidth: true } },
    MuiOutlinedInput: { styleOverrides: { root: { borderRadius: 12 } } },
  },
});

export default theme;
