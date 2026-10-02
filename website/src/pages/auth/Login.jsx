import { useNavigate } from 'react-router-dom';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import Box from '@mui/material/Box';
import FormControlLabel from '@mui/material/FormControlLabel';
import Checkbox from '@mui/material/Checkbox';
import LoginRounded from '@mui/icons-material/LoginRounded';
import AuthShell, { authLink } from './AuthShell';
import PasswordField from './PasswordField';

// DESIGN ONLY — submitting just opens the sample dashboard.
export default function Login() {
  const navigate = useNavigate();
  return (
    <AuthShell
      title="Welcome back"
      subtitle="Sign in with the same account you use in the desktop app."
      footer={<>New to EzyMailer? {authLink('/register', 'Create an account')}</>}
    >
      <Stack component="form" spacing={2.25} onSubmit={(e) => { e.preventDefault(); navigate('/account'); }}>
        <TextField label="Username or email" autoComplete="username" required />
        <PasswordField label="Password" autoComplete="current-password" required />
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <FormControlLabel control={<Checkbox size="small" defaultChecked />} label="Remember me" slotProps={{ typography: { fontSize: 14, color: 'text.secondary' } }} />
          <Box sx={{ fontSize: 14 }}>{authLink('/forgot-password', 'Forgot password?')}</Box>
        </Box>
        <Button type="submit" variant="contained" size="large" endIcon={<LoginRounded />}>Sign in</Button>
      </Stack>
    </AuthShell>
  );
}
