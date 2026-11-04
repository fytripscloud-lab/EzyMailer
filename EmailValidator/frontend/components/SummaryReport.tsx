"use client";

import { useEffect, useState } from "react";
import { PieChart } from "@mui/x-charts/PieChart";
import { BarChart } from "@mui/x-charts/BarChart";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Grid from "@mui/material/Grid";
import Skeleton from "@mui/material/Skeleton";
import Typography from "@mui/material/Typography";

import { extractErrorMessage, getReport } from "@/lib/api";
import { formatDuration } from "@/lib/format";
import type { SummaryReport as SummaryReportType } from "@/lib/types";

interface SummaryReportProps {
  jobId: string;
  refreshKey?: number;
}

function StatItem({ label, value }: { label: string; value: string | number }) {
  return (
    <Grid size={{ xs: 6, sm: 4, md: 3 }}>
      <Box sx={{ p: 1.5 }}>
        <Typography variant="h6" sx={{ fontWeight: 700 }}>
          {value}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {label}
        </Typography>
      </Box>
    </Grid>
  );
}

export default function SummaryReport({ jobId, refreshKey }: SummaryReportProps) {
  const [summary, setSummary] = useState<SummaryReportType | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getReport(jobId)
      .then((data) => {
        if (!cancelled) setSummary(data);
      })
      .catch((err) => {
        if (!cancelled) setError(extractErrorMessage(err));
      });
    return () => {
      cancelled = true;
    };
  }, [jobId, refreshKey]);

  if (error) {
    return (
      <Card>
        <CardContent>
          <Alert severity="error">{error}</Alert>
        </CardContent>
      </Card>
    );
  }

  if (!summary) {
    return (
      <Card>
        <CardContent>
          <Skeleton variant="rounded" height={200} />
        </CardContent>
      </Card>
    );
  }

  const statusData = [
    { id: "valid", value: summary.valid_count, label: "Valid", color: "#2E7D32" },
    { id: "invalid", value: summary.invalid_count, label: "Invalid", color: "#C62828" },
    { id: "risky", value: summary.risky_count, label: "Risky", color: "#F9A825" },
    { id: "unknown", value: summary.unknown_count, label: "Unknown", color: "#757575" },
  ].filter((d) => d.value > 0);

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Validation Summary
        </Typography>

        <Grid container>
          <StatItem label="Total Uploaded" value={summary.total_uploaded} />
          <StatItem label="Unique Emails" value={summary.unique_emails} />
          <StatItem label="Duplicate Emails" value={summary.duplicate_emails} />
          <StatItem label="Disposable" value={summary.disposable_count} />
          <StatItem label="Free Provider" value={summary.free_provider_count} />
          <StatItem label="Role Based" value={summary.role_based_count} />
          <StatItem label="Success Rate" value={`${summary.success_percent}%`} />
          <StatItem
            label="Duration"
            value={summary.validation_duration_seconds != null ? formatDuration(summary.validation_duration_seconds) : "—"}
          />
        </Grid>

        <Grid container spacing={2} sx={{ mt: 2 }}>
          <Grid size={{ xs: 12, md: 6 }}>
            <Typography variant="subtitle2" align="center" gutterBottom>
              Status Distribution
            </Typography>
            {statusData.length > 0 ? (
              <PieChart
                series={[{ data: statusData, innerRadius: 50, paddingAngle: 1, cornerRadius: 3 }]}
                height={260}
                slotProps={{ legend: { direction: "horizontal", position: { vertical: "bottom", horizontal: "center" } } }}
              />
            ) : (
              <Typography color="text.secondary" align="center">
                No data yet
              </Typography>
            )}
          </Grid>
          <Grid size={{ xs: 12, md: 6 }}>
            <Typography variant="subtitle2" align="center" gutterBottom>
              Risk Signal Breakdown
            </Typography>
            <BarChart
              height={260}
              dataset={[
                {
                  category: "Disposable",
                  count: summary.disposable_count,
                },
                { category: "Free Provider", count: summary.free_provider_count },
                { category: "Role Based", count: summary.role_based_count },
                { category: "Duplicates", count: summary.duplicate_emails },
              ]}
              xAxis={[{ dataKey: "category" }]}
              series={[{ dataKey: "count", label: "Count", color: "#1565C0" }]}
            />
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );
}
