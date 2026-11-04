"use client";

import { useEffect, useState } from "react";
import AppBar from "@mui/material/AppBar";
import Button from "@mui/material/Button";
import Container from "@mui/material/Container";
import Stack from "@mui/material/Stack";
import Toolbar from "@mui/material/Toolbar";
import Typography from "@mui/material/Typography";
import LockIcon from "@mui/icons-material/Lock";
import MarkEmailReadIcon from "@mui/icons-material/MarkEmailRead";

import ExportSection from "@/components/ExportSection";
import ResultsTable from "@/components/ResultsTable";
import SummaryReport from "@/components/SummaryReport";
import SystemStatus from "@/components/SystemStatus";
import UploadSection from "@/components/UploadSection";
import ValidationProgress from "@/components/ValidationProgress";
import { initAuthToken, UNAUTHORIZED_EVENT } from "@/lib/auth";
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

  // EazyValidator has no login of its own - it's only reachable with the JWT
  // EzyMailer's desktop app hands it via ?token=. No token means this tab
  // didn't come from a signed-in session; a later 401 flips it back too.
  useEffect(() => {
    function checkAuthAndRestore() {
      const token = initAuthToken();
      if (!token) {
        setStage("forbidden");
        return;
      }

      // Restore an in-progress or just-completed job after a page refresh -
      // the backend job itself is unaffected (it's a separate background
      // task), but without this the UI would lose track of it.
      const session = loadPersistedSession();
      if (session) {
        setJobId(session.jobId);
        setTotalRecords(session.totalRecords);
        setStage(session.stage);
      } else {
        setStage("upload");
      }
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
            <Stack spacing={2} sx={{ py: 10, alignItems: "center" }}>
              <LockIcon color="disabled" sx={{ fontSize: 48 }} />
              <Typography variant="h6">Access restricted</Typography>
              <Typography color="text.secondary" sx={{ textAlign: "center", maxWidth: 420 }}>
                Open EazyValidator from the &quot;Mail Validator&quot; button in EzyMailer - this page
                isn&apos;t reachable on its own.
              </Typography>
            </Stack>
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
