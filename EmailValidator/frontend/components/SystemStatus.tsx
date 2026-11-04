"use client";

import { useEffect, useState } from "react";
import Alert from "@mui/material/Alert";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import IconButton from "@mui/material/IconButton";
import Stack from "@mui/material/Stack";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import RefreshIcon from "@mui/icons-material/Refresh";

import { extractErrorMessage, getDiagnostics } from "@/lib/api";
import type { DiagnosticsResponse } from "@/lib/types";
import StatusBadge from "./StatusBadge";

export default function SystemStatus() {
  const [data, setData] = useState<DiagnosticsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async (refresh = false) => {
    setLoading(true);
    setError(null);
    try {
      const result = await getDiagnostics({ refresh });
      setData(result);
    } catch (err) {
      setError(extractErrorMessage(err));
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Run once on mount only - this is a one-shot checkup, not a poll.
    function run() {
      load();
    }
    run();
  }, []);

  const SMTP_LABELS = {
    open: "Open",
    blocked: "Blocked",
    timeout: "Handshake stalls",
    disabled: "Disabled",
    unknown: "Unknown",
  } as const;
  const smtpLabel = !data ? "Checking…" : SMTP_LABELS[data.smtp_port_25];
  const smtpTone = !data ? "neutral" : data.smtp_port_25 === "open" ? "good" : data.smtp_port_25 === "disabled" ? "neutral" : "risky";

  return (
    <Card>
      <CardContent>
        <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "center", mb: 1.5 }}>
          <Typography variant="h6">System Status</Typography>
          <Tooltip title="Re-check now">
            <span>
              <IconButton size="small" aria-label="re-check now" onClick={() => load(true)} disabled={loading}>
                {loading ? <CircularProgress size={18} /> : <RefreshIcon fontSize="small" />}
              </IconButton>
            </span>
          </Tooltip>
        </Stack>

        <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", rowGap: 1 }}>
          <StatusBadge label={`Backend API: ${error ? "Unreachable" : "Connected"}`} tone={error ? "bad" : "good"} />
          <StatusBadge
            label={`DNS Resolution: ${!data ? "Checking…" : data.dns === "ok" ? "Working" : "Failing"}`}
            tone={!data ? "neutral" : data.dns === "ok" ? "good" : "bad"}
          />
          <StatusBadge label={`SMTP Port 25: ${smtpLabel}`} tone={smtpTone} />
          {data && (
            <>
              <Chip size="small" variant="outlined" label={`SMTP checks: ${data.smtp_check_enabled ? "on" : "off"}`} />
              <Chip
                size="small"
                variant="outlined"
                label={`Catch-all checks: ${data.catch_all_check_enabled ? "on" : "off"}`}
              />
              <Chip
                size="small"
                variant="outlined"
                label={`Limits: ${data.max_upload_size_mb}MB / ${data.max_rows.toLocaleString()} rows`}
              />
            </>
          )}
        </Stack>

        {error && (
          <Alert severity="error" sx={{ mt: 2 }}>
            Can&apos;t reach the backend API ({error}). Make sure it&apos;s running and{" "}
            <code>NEXT_PUBLIC_API_URL</code> points at it.
          </Alert>
        )}

        {!error && data?.smtp_port_25 === "blocked" && (
          <Alert severity="warning" sx={{ mt: 2 }}>
            Outbound SMTP (port 25) looks blocked on this network — mailbox verification will mostly come back{" "}
            <strong>Unknown</strong> rather than Valid/Invalid. This is expected on most cloud hosts; see the README
            for deployment notes.
          </Alert>
        )}

        {!error && data?.smtp_port_25 === "timeout" && (
          <Alert severity="warning" sx={{ mt: 2 }}>
            Port 25 accepts a connection here, but the SMTP conversation itself stalls before finishing — some
            providers do this on purpose for unrecognized senders. Real validation will see this the same way as a
            blocked port: mostly <strong>Unknown</strong> results.
          </Alert>
        )}

        {!error && data?.smtp_port_25 === "disabled" && (
          <Alert severity="info" sx={{ mt: 2 }}>
            SMTP mailbox checks are turned off (<code>ENABLE_SMTP_CHECK=false</code>) — results rely on syntax/DNS/MX/
            disposable/role checks only.
          </Alert>
        )}

        {data && (
          <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1.5 }}>
            Last checked {new Date(data.checked_at).toLocaleTimeString()} · {data.dns_detail} · {data.smtp_detail}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
}
