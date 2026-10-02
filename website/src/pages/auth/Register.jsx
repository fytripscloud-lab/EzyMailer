import { useNavigate } from 'react-router-dom';
import Grid from '@mui/material/Grid';
import TextField from '@mui/material/TextField';
import MenuItem from '@mui/material/MenuItem';
import Button from '@mui/material/Button';
import FormControlLabel from '@mui/material/FormControlLabel';
import Checkbox from '@mui/material/Checkbox';
import Box from '@mui/material/Box';
import RocketLaunchRounded from '@mui/icons-material/RocketLaunchRounded';
import AuthShell, { authLink } from './AuthShell';
import PasswordField from './PasswordField';

const countries = ['India', 'United States', 'United Kingdom', 'United Arab Emirates', 'Bangladesh', 'Other'];

// DESIGN ONLY — submitting just opens the sample dashboard.
export default function Register() {
  const navigate = useNavigate();
  return (
    <AuthShell
      title="Create your account"
      subtitle="One account for the desktop app and the portal."
      footer={<>Already have an account? {authLink('/login', 'Sign in')}</>}
    >
      <Box component="form" onSubmit={(e) => { e.preventDefault(); navigate('/account'); }}>
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, sm: 6 }}><TextField label="Full name" autoComplete="name" required /></Grid>
          <Grid size={{ xs: 12, sm: 6 }}><TextField label="Username" autoComplete="username" required /></Grid>
          <Grid size={12}><TextField label="Email" type="email" autoComplete="email" required /></Grid>
          <Grid size={{ xs: 12, sm: 6 }}><TextField label="Phone" type="tel" autoComplete="tel" /></Grid>
          <Grid size={{ xs: 12, sm: 6 }}>
            <TextField select label="Country" defaultValue="India">
              {countries.map((c) => <MenuItem key={c} value={c}>{c}</MenuItem>)}
            </TextField>
          </Grid>
          <Grid size={12}><PasswordField label="Password" autoComplete="new-password" helperText="At least 8 characters" required /></Grid>
          <Grid size={12}><PasswordField label="Confirm password" autoComplete="new-password" required /></Grid>
          <Grid size={12}>
            <FormControlLabel
              control={<Checkbox size="small" required />}
              label={<>I agree to the {authLink('/terms', 'Terms')}, {authLink('/privacy', 'Privacy Policy')} and {authLink('/acceptable-use', 'Acceptable Use Policy')}</>}
              slotProps={{ typography: { fontSize: 14, color: 'text.secondary' } }}
            />
          </Grid>
          <Grid size={12}>
            <Button type="submit" variant="contained" size="large" fullWidth endIcon={<RocketLaunchRounded />}>Create account</Button>
          </Grid>
        </Grid>
      </Box>
    </AuthShell>
  );
}
