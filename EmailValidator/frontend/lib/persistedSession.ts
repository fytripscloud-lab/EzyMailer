const STORAGE_KEY = "eazyvalidator_active_job";

export interface PersistedSession {
  jobId: string;
  stage: "validating" | "completed";
  totalRecords: number;
}

/**
 * Keeps the active job visible across a page refresh. A refresh doesn't
 * touch the backend job at all (it's an independent background task), but
 * without this the frontend would forget which job it was watching and drop
 * the user back to the upload screen with no way to see progress or cancel
 * an already-running job.
 */
export function loadPersistedSession(): PersistedSession | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (
      parsed &&
      typeof parsed.jobId === "string" &&
      (parsed.stage === "validating" || parsed.stage === "completed") &&
      typeof parsed.totalRecords === "number"
    ) {
      return parsed as PersistedSession;
    }
    return null;
  } catch {
    return null;
  }
}

export function savePersistedSession(session: PersistedSession | null): void {
  if (typeof window === "undefined") return;
  if (!session) {
    window.localStorage.removeItem(STORAGE_KEY);
    return;
  }
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
}
