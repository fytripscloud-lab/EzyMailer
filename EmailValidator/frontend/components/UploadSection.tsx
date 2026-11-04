"use client";

import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import FormControl from "@mui/material/FormControl";
import IconButton from "@mui/material/IconButton";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import CloseIcon from "@mui/icons-material/Close";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import InsertDriveFileIcon from "@mui/icons-material/InsertDriveFile";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";

import { deleteJob, extractErrorMessage, startValidation, uploadFile } from "@/lib/api";
import type { UploadResponse } from "@/lib/types";

const ACCEPTED_TYPES = {
  "text/csv": [".csv"],
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
  "application/vnd.ms-excel": [".xls"],
};

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

interface UploadSectionProps {
  onStarted: (jobId: string, totalRecords: number) => void;
}

export default function UploadSection({ onStarted }: UploadSectionProps) {
  const [uploading, setUploading] = useState(false);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [upload, setUpload] = useState<UploadResponse | null>(null);
  const [selectedColumn, setSelectedColumn] = useState<string>("");

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (!file) return;
    setError(null);
    setUploading(true);
    try {
      const result = await uploadFile(file);
      setUpload(result);
      setSelectedColumn(result.detected_email_column ?? "");
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setUploading(false);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive, fileRejections } = useDropzone({
    onDrop,
    accept: ACCEPTED_TYPES,
    multiple: false,
    disabled: uploading || !!upload,
  });

  const handleRemove = async () => {
    if (upload) {
      try {
        await deleteJob(upload.job_id);
      } catch {
        // best-effort cleanup; ignore failures removing an already-gone job
      }
    }
    setUpload(null);
    setSelectedColumn("");
    setError(null);
  };

  const handleStart = async () => {
    if (!upload) return;
    setError(null);
    setStarting(true);
    try {
      await startValidation(upload.job_id, { emailColumn: selectedColumn });
      onStarted(upload.job_id, upload.total_records);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setStarting(false);
    }
  };

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Upload Email List
        </Typography>

        {!upload && (
          <Box
            {...getRootProps()}
            sx={{
              border: "2px dashed",
              borderColor: isDragActive ? "primary.main" : "divider",
              borderRadius: 2,
              p: 6,
              textAlign: "center",
              cursor: uploading ? "default" : "pointer",
              bgcolor: isDragActive ? "action.hover" : "background.default",
              transition: "background-color 0.2s, border-color 0.2s",
            }}
          >
            <input {...getInputProps()} />
            {uploading ? (
              <Stack spacing={2} sx={{ alignItems: "center" }}>
                <CircularProgress />
                <Typography color="text.secondary">Uploading…</Typography>
              </Stack>
            ) : (
              <Stack spacing={1} sx={{ alignItems: "center" }}>
                <CloudUploadIcon sx={{ fontSize: 48, color: "primary.main" }} />
                <Typography variant="body1">
                  Drag & drop your file here, or click to browse
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Supported formats: .xlsx, .xls, .csv
                </Typography>
              </Stack>
            )}
          </Box>
        )}

        {fileRejections.length > 0 && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {fileRejections[0].errors[0]?.message ?? "File was rejected"}
          </Alert>
        )}

        {error && (
          <Alert severity="error" sx={{ mt: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {upload && (
          <Box sx={{ mt: 2 }}>
            <Stack
              direction="row"
              sx={{ p: 2, borderRadius: 2, bgcolor: "background.default", alignItems: "center", justifyContent: "space-between" }}
            >
              <Stack direction="row" spacing={2} sx={{ alignItems: "center" }}>
                <InsertDriveFileIcon color="primary" />
                <Box>
                  <Typography variant="body1" sx={{ fontWeight: 600 }}>
                    {upload.filename}
                  </Typography>
                  <Stack direction="row" spacing={1} sx={{ mt: 0.5 }}>
                    <Chip size="small" label={formatBytes(upload.size_bytes)} />
                    <Chip size="small" label={`${upload.total_records} records`} />
                  </Stack>
                </Box>
              </Stack>
              <IconButton onClick={handleRemove} aria-label="remove file">
                <CloseIcon />
              </IconButton>
            </Stack>

            {upload.requires_column_selection && (
              <Alert severity="warning" sx={{ mt: 2 }}>
                We could not automatically detect an email column. Please select one below.
              </Alert>
            )}

            <FormControl fullWidth sx={{ mt: 2 }}>
              <InputLabel id="email-column-label">Email Column</InputLabel>
              <Select
                labelId="email-column-label"
                label="Email Column"
                value={selectedColumn}
                onChange={(e) => setSelectedColumn(e.target.value)}
              >
                {upload.available_columns.map((col) => (
                  <MenuItem key={col} value={col}>
                    {col}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <Button
              variant="contained"
              size="large"
              startIcon={starting ? <CircularProgress size={18} color="inherit" /> : <PlayArrowIcon />}
              sx={{ mt: 3 }}
              disabled={!selectedColumn || starting}
              onClick={handleStart}
              fullWidth
            >
              {starting ? "Starting…" : "Start Validation"}
            </Button>
          </Box>
        )}
      </CardContent>
    </Card>
  );
}
