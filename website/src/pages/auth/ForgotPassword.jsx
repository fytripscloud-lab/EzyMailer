import { useState } from 'react';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import Alert from '@mui/material/Alert';
import AuthShell, { authLink } from './AuthShell';

// DESIGN ONLY — shows the confirmation state without sending anything.
export default function ForgotPassword() {
  const [sent, setSent] = useState(false);
  return (
    <AuthShell
      title="Reset your password"
      subtitle="Enter your account email and we’ll send you a reset link."
      footer={<>Remembered it? {authLink('/login', 'Back to sign in')}</>}
    >
      <Stack component="form" spacing={2.25} onSubmit={(e) => { e.preventDefault(); setSent(true); }}>
        {sent && <Alert severity="success" variant="outlined">If that email has an account, a reset link is on its way.</Alert>}
        <TextField label="Email" type="email" autoComplete="email" required />
        <Button type="submit" variant="contained" size="large">Send reset link</Button>
      </Stack>
    </AuthShell>
  );
}
