"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { DataGrid } from "@mui/x-data-grid";
import type { GridColDef } from "@mui/x-data-grid";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import InputAdornment from "@mui/material/InputAdornment";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import SearchIcon from "@mui/icons-material/Search";

import { extractErrorMessage, getResults } from "@/lib/api";
import type { ResultFilter, ResultRow } from "@/lib/types";
import StatusBadge from "./StatusBadge";

const FILTERS: { value: ResultFilter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "valid", label: "Valid" },
  { value: "invalid", label: "Invalid" },
  { value: "risky", label: "Risky" },
  { value: "unknown", label: "Unknown" },
  { value: "disposable", label: "Disposable" },
];

interface ResultsTableProps {
  jobId: string;
  refreshKey?: number;
  filter: ResultFilter;
  onFilterChange: (filter: ResultFilter) => void;
  onSearchChange: (search: string) => void;
}

export default function ResultsTable({ jobId, refreshKey, filter, onFilterChange, onSearchChange }: ResultsTableProps) {
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [paginationModel, setPaginationModel] = useState({ page: 0, pageSize: 25 });
  const [rows, setRows] = useState<ResultRow[]>([]);
  const [totalRows, setTotalRows] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleSearchChange = (value: string) => {
    setSearch(value);
    if (debounceTimer.current) clearTimeout(debounceTimer.current);
    debounceTimer.current = setTimeout(() => {
      setDebouncedSearch(value);
      onSearchChange(value);
    }, 300);
  };

  useEffect(() => {
    return () => {
      if (debounceTimer.current) clearTimeout(debounceTimer.current);
    };
  }, []);

  // Reset to page 0 whenever the query changes, using the documented
  // "adjust state during render" pattern instead of an effect that mirrors
  // these values (avoids an extra render + effect round-trip).
  const queryKey = `${filter}|${debouncedSearch}|${refreshKey ?? 0}`;
  const [lastQueryKey, setLastQueryKey] = useState(queryKey);
  let effectivePaginationModel = paginationModel;
  if (queryKey !== lastQueryKey) {
    setLastQueryKey(queryKey);
    effectivePaginationModel = { ...paginationModel, page: 0 };
    setPaginationModel(effectivePaginationModel);
  }

  useEffect(() => {
    let cancelled = false;

    async function run() {
      setLoading(true);
      setError(null);
      try {
        const data = await getResults(jobId, {
          page: effectivePaginationModel.page + 1,
          pageSize: effectivePaginationModel.pageSize,
          filter,
          search: debouncedSearch,
        });
        if (cancelled) return;
        setRows(data.rows);
        setTotalRows(data.total_rows);
      } catch (err) {
        if (!cancelled) setError(extractErrorMessage(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    run();
    return () => {
      cancelled = true;
    };
  }, [jobId, filter, debouncedSearch, effectivePaginationModel, refreshKey]);

  const originalColumnKeys = useMemo(() => {
    const keys = new Set<string>();
    rows.forEach((r) => Object.keys(r.original || {}).forEach((k) => keys.add(k)));
    return Array.from(keys);
  }, [rows]);

  const columns: GridColDef<ResultRow>[] = useMemo(() => {
    const originalCols: GridColDef<ResultRow>[] = originalColumnKeys.map((key) => ({
      field: `original_${key}`,
      headerName: key,
      flex: 1,
      minWidth: 140,
      valueGetter: (_value, row) => row.original?.[key] ?? "",
    }));

    return [
      { field: "row_no", headerName: "Row No.", width: 90 },
      { field: "email", headerName: "Email", flex: 1.4, minWidth: 220 },
      ...originalCols,
      {
        field: "syntax_valid",
        headerName: "Syntax",
        width: 110,
        renderCell: (params) => <StatusBadge label={params.value ? "Valid" : "Invalid"} tone={params.value ? "good" : "bad"} />,
      },
      {
        field: "domain_valid",
        headerName: "Domain",
        width: 110,
        renderCell: (params) => <StatusBadge label={params.value ? "Valid" : "Invalid"} tone={params.value ? "good" : "bad"} />,
      },
      {
        field: "mx_found",
        headerName: "MX Record",
        width: 120,
        renderCell: (params) => (
          <StatusBadge label={params.value ? "Found" : "Not Found"} tone={params.value ? "good" : "bad"} />
        ),
      },
      {
        field: "smtp",
        headerName: "SMTP",
        width: 120,
        renderCell: (params) => {
          const v = String(params.value);
          const tone = v === "accepted" ? "good" : v === "rejected" ? "bad" : "neutral";
          return <StatusBadge label={v[0].toUpperCase() + v.slice(1)} tone={tone} />;
        },
      },
      {
        field: "disposable",
        headerName: "Disposable",
        width: 110,
        renderCell: (params) => <StatusBadge label={params.value ? "Yes" : "No"} tone={params.value ? "risky" : "neutral"} />,
      },
      {
        field: "free_provider",
        headerName: "Free Provider",
        width: 130,
        renderCell: (params) => <StatusBadge label={params.value ? "Yes" : "No"} tone="neutral" />,
      },
      {
        field: "role_based",
        headerName: "Role Based",
        width: 120,
        renderCell: (params) => <StatusBadge label={params.value ? "Yes" : "No"} tone={params.value ? "risky" : "neutral"} />,
      },
      {
        field: "catch_all",
        headerName: "Catch-All",
        width: 120,
        renderCell: (params) => {
          const v = String(params.value);
          const tone = v === "yes" ? "risky" : v === "no" ? "good" : "neutral";
          return <StatusBadge label={v[0].toUpperCase() + v.slice(1)} tone={tone} />;
        },
      },
      {
        field: "final_status",
        headerName: "Final Status",
        width: 130,
        renderCell: (params) => {
          const v = String(params.value);
          const tone = v === "valid" ? "good" : v === "invalid" ? "bad" : v === "risky" ? "risky" : "neutral";
          return <StatusBadge label={v[0].toUpperCase() + v.slice(1)} tone={tone} />;
        },
      },
    ];
  }, [originalColumnKeys]);

  return (
    <Card>
      <CardContent>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ mb: 2, justifyContent: "space-between" }}>
          <Typography variant="h6">Validation Results</Typography>
          <TextField
            size="small"
            placeholder="Search email…"
            value={search}
            onChange={(e) => handleSearchChange(e.target.value)}
            slotProps={{ input: { startAdornment: <InputAdornment position="start"><SearchIcon fontSize="small" /></InputAdornment> } }}
            sx={{ minWidth: 220 }}
          />
        </Stack>

        <Stack direction="row" spacing={1} sx={{ mb: 2, flexWrap: "wrap" }}>
          {FILTERS.map((f) => (
            <Chip
              key={f.value}
              label={f.label}
              onClick={() => onFilterChange(f.value)}
              color={filter === f.value ? "primary" : "default"}
              variant={filter === f.value ? "filled" : "outlined"}
            />
          ))}
        </Stack>

        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

        <Box sx={{ width: "100%" }}>
          <DataGrid
            autoHeight
            rows={rows}
            columns={columns}
            getRowId={(row) => row.row_no}
            loading={loading}
            paginationMode="server"
            rowCount={totalRows}
            paginationModel={effectivePaginationModel}
            onPaginationModelChange={setPaginationModel}
            pageSizeOptions={[25, 50, 100]}
            disableRowSelectionOnClick
            density="compact"
          />
        </Box>
      </CardContent>
    </Card>
  );
}
