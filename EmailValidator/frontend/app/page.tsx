"use client";

import { useEffect, useState } from "react";
import AppBar from "@mui/material/AppBar";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Container from "@mui/material/Container";
import Stack from "@mui/material/Stack";
import Toolbar from "@mui/material/Toolbar";
import Typography from "@mui/material/Typography";
import MarkEmailReadIcon from "@mui/icons-material/MarkEmailRead";

import ExportSection from "@/components/ExportSection";
import LoginForm from "@/components/LoginForm";
import ResultsTable from "@/components/ResultsTable";
import SummaryReport from "@/components/SummaryReport";
import SystemStatus from "@/components/SystemStatus";
import UploadSection from "@/components/UploadSection";
import ValidationProgress from "@/components/ValidationProgress";
import { initAuthToken, setAuthToken, UNAUTHORIZED_EVENT } from "@/lib/auth";
import { loadPersistedSession, savePersistedSession } from "@/lib/persistedSession";
import type { ResultFilter } from "@/lib/types";

type Stage = "checking" | "forbidden" | "upload" | "validating" | "completed";

export default function Home() {
  const [stage, setStage] = useState<Stage>("checking");
  const [jobId, setJobId] = useState<string | null>(null);
  const [totalRecords, setTotalRecords] = useState(0);
  const [refreshKey, setRefreshKey] = useState(0);
  const [resultsFilter, setResultsFilter] = useState<ResultFilter>("all");
  const [resultsSearch, setResultsSearch] = useState("");

  // Resumes an in-progress or just-completed job after a page refresh (the
  // backend job itself is unaffected - it's a separate background task) once
  // a token is in hand, whether from the URL or a fresh login.
  function proceedPastAuth() {
    const session = loadPersistedSession();
    if (session) {
      setJobId(session.jobId);
      setTotalRecords(session.totalRecords);
      setStage(session.stage);
    } else {
      setStage("upload");
    }
  }

  const handleLoggedIn = (token: string) => {
    setAuthToken(token);
    proceedPastAuth();
  };

  // Normally opened from EzyMailer's desktop app with the JWT already in the
  // URL (?token=...) - no login needed. Opened directly with no token, the
  // "forbidden" stage renders a login form instead; a later 401 flips back.
  useEffect(() => {
    function checkAuthAndRestore() {
      const token = initAuthToken();
      if (!token) {
        setStage("forbidden");
        return;
      }
      proceedPastAuth();
    }
    checkAuthAndRestore();

    const onUnauthorized = () => setStage("forbidden");
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
  }, []);

  useEffect(() => {
    if (jobId && (stage === "validating" || stage === "completed")) {
      savePersistedSession({ jobId, stage, totalRecords });
    } else {
      savePersistedSession(null);
    }
  }, [jobId, stage, totalRecords]);

  const handleStarted = (id: string, total: number) => {
    setJobId(id);
    setTotalRecords(total);
    setResultsFilter("all");
    setResultsSearch("");
    setStage("validating");
  };

  const handleCompleted = () => {
    setRefreshKey((k) => k + 1);
    setStage("completed");
  };

  const handleReset = () => {
    setJobId(null);
    setTotalRecords(0);
    setResultsFilter("all");
    setResultsSearch("");
    setStage("upload");
  };

  return (
    <>
      <AppBar position="static" color="primary" elevation={0}>
        <Toolbar>
          <MarkEmailReadIcon sx={{ mr: 1.5 }} />
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            EazyValidator Pro
          </Typography>
        </Toolbar>
      </AppBar>

      <Container maxWidth="lg" sx={{ py: 4, flex: 1 }}>
        <Stack spacing={3}>
          {stage === "forbidden" && (
            <Box sx={{ py: 6 }}>
              <LoginForm onLoggedIn={handleLoggedIn} />
            </Box>
          )}

          {stage === "upload" && (
            <>
              <SystemStatus />
              <UploadSection onStarted={handleStarted} />
            </>
          )}

          {stage === "validating" && jobId && (
            <ValidationProgress
              jobId={jobId}
              totalRecords={totalRecords}
              onCompleted={handleCompleted}
              onReset={handleReset}
            />
          )}

          {stage === "completed" && jobId && (
            <>
              <SummaryReport jobId={jobId} refreshKey={refreshKey} />
              <ResultsTable
                jobId={jobId}
                refreshKey={refreshKey}
                filter={resultsFilter}
                onFilterChange={setResultsFilter}
                onSearchChange={setResultsSearch}
              />
              <ExportSection jobId={jobId} filter={resultsFilter} search={resultsSearch} />
              <Stack direction="row" sx={{ justifyContent: "flex-end" }}>
                <Button variant="text" onClick={handleReset}>
                  Validate another file
                </Button>
              </Stack>
            </>
          )}
        </Stack>
      </Container>
    </>
  );
}
