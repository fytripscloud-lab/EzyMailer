import Container from '@mui/material/Container';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import { Link as RouterLink } from 'react-router-dom';
import { gradientText } from '../theme';

export default function NotFound() {
  return (
    <Container maxWidth="sm" sx={{ textAlign: 'center', py: { xs: 12, md: 18 } }}>
      <Typography sx={{ ...gradientText, fontFamily: '"Space Grotesk"', fontWeight: 700, fontSize: { xs: 110, md: 160 }, lineHeight: 1 }}>404</Typography>
      <Typography variant="h4" sx={{ mt: 2 }}>Lost in the outbox.</Typography>
      <Typography color="text.secondary" sx={{ mt: 1.5, mb: 4 }}>The page you are looking for has drifted out of orbit.</Typography>
      <Button component={RouterLink} to="/" variant="contained" size="large">Back to home</Button>
    </Container>
  );
}
