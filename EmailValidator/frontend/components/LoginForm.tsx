"use client";

import { useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import LockIcon from "@mui/icons-material/Lock";

import { loginToEzyMailer } from "@/lib/ezymailerAuth";

interface LoginFormProps {
  onLoggedIn: (token: string) => void;
}

export default function LoginForm({ onLoggedIn }: LoginFormProps) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password) return;
    setError(null);
    setSubmitting(true);
    try {
      const token = await loginToEzyMailer(username.trim(), password);
      onLoggedIn(token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Card sx={{ maxWidth: 420, mx: "auto" }}>
      <CardContent>
        <Stack spacing={1} sx={{ alignItems: "center", mb: 2 }}>
          <LockIcon color="primary" sx={{ fontSize: 40 }} />
          <Typography variant="h6">Sign in to EzyMailer</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ textAlign: "center" }}>
            Opened directly rather than via the &quot;Mail Validator&quot; button - sign in with your
            EzyMailer account to continue.
          </Typography>
        </Stack>

        <Box component="form" onSubmit={handleSubmit}>
          <Stack spacing={2}>
            <TextField
              label="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoFocus
              fullWidth
              disabled={submitting}
            />
            <TextField
              label="Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              fullWidth
              disabled={submitting}
            />

            {error && <Alert severity="error">{error}</Alert>}

            <Button
              type="submit"
              variant="contained"
              size="large"
              fullWidth
              disabled={!username.trim() || !password || submitting}
              startIcon={submitting ? <CircularProgress size={18} color="inherit" /> : undefined}
            >
              {submitting ? "Signing in…" : "Sign In"}
            </Button>
          </Stack>
        </Box>
      </CardContent>
    </Card>
  );
}
