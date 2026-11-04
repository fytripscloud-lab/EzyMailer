"use client";

import { useState } from "react";
import axios from "axios";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import Grid from "@mui/material/Grid";
import LinearProgress from "@mui/material/LinearProgress";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { keyframes } from "@mui/material/styles";
import CancelIcon from "@mui/icons-material/Cancel";

import { cancelJob, extractErrorMessage, getProgress } from "@/lib/api";
import { formatDuration } from "@/lib/format";
import { usePolling } from "@/lib/usePolling";
import type { ProgressResponse } from "@/lib/types";
import TerminalLog from "./TerminalLog";

const stripeMove = keyframes`
  0% { background-position: 0 0; }
  100% { background-position: 32px 0; }
`;

interface StatTileProps {
  label: string;
  value: string | number;
  color?: string;
}

function StatTile({ label, value, color }: StatTileProps) {
  return (
    <Box sx={{ textAlign: "center", p: 1.5, borderRadius: 2, bgcolor: "background.default", height: "100%" }}>
      <Typography variant="h5" color={color ?? "text.primary"} sx={{ fontWeight: 700 }}>
        {value}
      </Typography>
      <Typography variant="body2" color="text.secondary">
        {label}
      </Typography>
    </Box>
  );
}

interface ValidationProgressProps {
  jobId: string;
  totalRecords: number;
  onCompleted: () => void;
  onReset: () => void;
}

export default function ValidationProgress({ jobId, totalRecords, onCompleted, onReset }: ValidationProgressProps) {
  const [progress, setProgress] = useState<ProgressResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [confirmCancelOpen, setConfirmCancelOpen] = useState(false);
  const active = !notFound && (!progress || progress.status === "validating");

  usePolling(
    async () => {
      try {
        const data = await getProgress(jobId);
        setProgress(data);
        setError(null);
        // "failed" (e.g. the job was orphaned by a server restart mid-run)
        // stays on this screen with its error shown, rather than moving on
        // to a "completed" view whose report/export/results would just 409.
        if (data.status === "completed" || data.status === "cancelled") {
          onCompleted();
        }
      } catch (err) {
        // A 404 means the job genuinely no longer exists (e.g. this tab was
        // refreshed and reconnected to a job that has since been deleted) -
        // further polling can't recover that, so stop and let the user
        // start over instead of silently retrying forever.
        if (axios.isAxiosError(err) && err.response?.status === 404) {
          setNotFound(true);
        }
        setError(extractErrorMessage(err));
      }
    },
    1500,
    active
  );

  const requestCancel = () => setConfirmCancelOpen(true);

  const confirmCancel = async () => {
    setConfirmCancelOpen(false);
    setCancelling(true);
    try {
      await cancelJob(jobId);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setCancelling(false);
    }
  };

  const total = progress?.total ?? totalRecords;
  const percent = progress?.percent ?? 0;

  return (
    <Card>
      <CardContent>
        <Stack direction="row" sx={{ mb: 2, justifyContent: "space-between", alignItems: "center" }}>
          <Typography variant="h6">Validation Progress</Typography>
          {active && (
            <Button
              size="small"
              color="error"
              variant="outlined"
              startIcon={<CancelIcon />}
              disabled={cancelling}
              onClick={requestCancel}
            >
              {cancelling ? "Cancelling…" : "Cancel"}
            </Button>
          )}
        </Stack>

        <Dialog open={confirmCancelOpen} onClose={() => setConfirmCancelOpen(false)}>
          <DialogTitle>Cancel validation?</DialogTitle>
          <DialogContent>
            <DialogContentText>
              This stops the job partway through. Emails already checked keep their results and stay available to
              export — only the remaining, unprocessed emails are skipped.
            </DialogContentText>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setConfirmCancelOpen(false)}>Keep Validating</Button>
            <Button color="error" onClick={confirmCancel} autoFocus>
              Cancel Validation
            </Button>
          </DialogActions>
        </Dialog>

        {notFound && (
          <Alert
            severity="error"
            sx={{ mb: 2 }}
            action={
              <Button color="inherit" size="small" onClick={onReset}>
                Start Over
              </Button>
            }
          >
            This job could no longer be found — it may have expired or been deleted.
          </Alert>
        )}

        {!notFound && error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {progress?.status === "failed" && (
          <Alert
            severity="error"
            sx={{ mb: 2 }}
            action={
              <Button color="inherit" size="small" onClick={onReset}>
                Start Over
              </Button>
            }
          >
            {progress.error || "Validation failed."}
          </Alert>
        )}

        <Box sx={{ mb: 3 }}>
          <Stack direction="row" sx={{ mb: 0.5, justifyContent: "space-between" }}>
            <Typography variant="body2" color="text.secondary">
              {progress?.status ? progress.status[0].toUpperCase() + progress.status.slice(1) : "Starting…"}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {percent.toFixed(1)}%
            </Typography>
          </Stack>
          <LinearProgress
            variant="determinate"
            value={Math.min(percent, 100)}
            sx={{
              height: 10,
              borderRadius: 5,
              bgcolor: "action.hover",
              "& .MuiLinearProgress-bar": {
                borderRadius: 5,
                ...(active && {
                  backgroundImage:
                    "linear-gradient(45deg, rgba(255,255,255,.25) 25%, transparent 25%, transparent 50%, rgba(255,255,255,.25) 50%, rgba(255,255,255,.25) 75%, transparent 75%, transparent)",
                  backgroundSize: "32px 32px",
                  animation: `${stripeMove} 0.9s linear infinite`,
                }),
              },
            }}
          />
        </Box>

        <Grid container spacing={2}>
          <Grid size={{ xs: 6, sm: 3 }}>
            <StatTile label="Total" value={total} />
          </Grid>
          <Grid size={{ xs: 6, sm: 3 }}>
            <StatTile label="Processed" value={progress?.processed ?? 0} />
          </Grid>
          <Grid size={{ xs: 6, sm: 3 }}>
            <StatTile label="Remaining" value={progress?.remaining ?? total} />
          </Grid>
          <Grid size={{ xs: 6, sm: 3 }}>
            <StatTile label="Speed (emails/s)" value={(progress?.emails_per_second ?? 0).toFixed(1)} />
          </Grid>
          <Grid size={{ xs: 6, sm: 3 }}>
            <StatTile label="Valid" value={progress?.valid ?? 0} color="success.main" />
          </Grid>
          <Grid size={{ xs: 6, sm: 3 }}>
            <StatTile label="Invalid" value={progress?.invalid ?? 0} color="error.main" />
          </Grid>
          <Grid size={{ xs: 6, sm: 3 }}>
            <StatTile label="Risky" value={progress?.risky ?? 0} color="warning.main" />
          </Grid>
          <Grid size={{ xs: 6, sm: 3 }}>
            <StatTile label="Unknown" value={progress?.unknown ?? 0} />
          </Grid>
        </Grid>

        <TerminalLog lines={progress?.recent_activity ?? []} active={active} total={total} />

        <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
          {progress?.eta_seconds != null
            ? `Estimated time remaining: ${formatDuration(progress.eta_seconds)}`
            : "Estimating time remaining…"}
        </Typography>
      </CardContent>
    </Card>
  );
}
