import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import Home from "@/app/page";
import { getDiagnostics, getProgress, getReport, getResults } from "@/lib/api";
import { UNAUTHORIZED_EVENT } from "@/lib/auth";
import { loginToEzyMailer } from "@/lib/ezymailerAuth";
import type { DiagnosticsResponse, ProgressResponse, ResultsPage, SummaryReport } from "@/lib/types";

jest.mock("@/lib/api", () => ({
  ...jest.requireActual("@/lib/api"),
  getDiagnostics: jest.fn(),
  getProgress: jest.fn(),
  getResults: jest.fn(),
  getReport: jest.fn(),
}));

jest.mock("@/lib/ezymailerAuth", () => ({
  loginToEzyMailer: jest.fn(),
}));

const mockGetDiagnostics = getDiagnostics as jest.MockedFunction<typeof getDiagnostics>;
const mockGetProgress = getProgress as jest.MockedFunction<typeof getProgress>;
const mockGetResults = getResults as jest.MockedFunction<typeof getResults>;
const mockGetReport = getReport as jest.MockedFunction<typeof getReport>;
const mockLoginToEzyMailer = loginToEzyMailer as jest.MockedFunction<typeof loginToEzyMailer>;

const STORAGE_KEY = "eazyvalidator_active_job";

function diagnostics(): DiagnosticsResponse {
  return {
    checked_at: "2026-01-01T00:00:00Z",
    backend: "ok",
    dns: "ok",
    dns_detail: "ok",
    smtp_port_25: "open",
    smtp_detail: "ok",
    smtp_check_enabled: true,
    catch_all_check_enabled: true,
    smtp_concurrency: 5,
    dns_concurrency: 20,
    max_upload_size_mb: 25,
    max_rows: 100000,
    job_retention_hours: 24,
  };
}

describe("Home page session persistence", () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    jest.clearAllMocks();
    window.localStorage.clear();
    // Home now gates everything behind the token EzyMailer's desktop app
    // hands it via ?token=; simulate an already-authenticated tab.
    window.sessionStorage.setItem("eazyvalidator_auth_token", "test-token");
    mockGetDiagnostics.mockResolvedValue(diagnostics());
    // Default: no auto-login available (the /api/v1/session/local probe
    // fails), as if the desktop app weren't running - tests that need the
    // success path override this explicitly.
    global.fetch = jest.fn().mockRejectedValue(new Error("connection refused"));
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it("shows the upload screen when nothing is persisted", async () => {
    render(<Home />);

    await waitFor(() => expect(screen.getByText("Upload Email List")).toBeInTheDocument());
  });

  it("shows a login form instead of the upload flow when there's no auth token", async () => {
    window.sessionStorage.removeItem("eazyvalidator_auth_token");

    render(<Home />);

    await waitFor(() => expect(screen.getByText("Sign in to EzyMailer")).toBeInTheDocument());
    expect(screen.queryByText("Upload Email List")).not.toBeInTheDocument();
  });

  it("auto-logs in via the local desktop session instead of showing the login form", async () => {
    window.sessionStorage.removeItem("eazyvalidator_auth_token");
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ token: "auto-login-token" }),
    });

    render(<Home />);

    await waitFor(() => expect(screen.getByText("Upload Email List")).toBeInTheDocument());
    expect(screen.queryByText("Sign in to EzyMailer")).not.toBeInTheDocument();
    expect(window.sessionStorage.getItem("eazyvalidator_auth_token")).toBe("auto-login-token");
  });

  it("recovers from a stale token by retrying auto-login instead of jumping straight to the login form", async () => {
    // beforeEach already seeded a token, so this starts on "upload" like a
    // normal session - then the stale token gets rejected (401), the same
    // way a token left over from an earlier run in this tab would.
    render(<Home />);
    await waitFor(() => expect(screen.getByText("Upload Email List")).toBeInTheDocument());

    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ token: "refreshed-token" }),
    });
    window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));

    await waitFor(() => expect(screen.getByText("Upload Email List")).toBeInTheDocument());
    expect(screen.queryByText("Sign in to EzyMailer")).not.toBeInTheDocument();
    expect(window.sessionStorage.getItem("eazyvalidator_auth_token")).toBe("refreshed-token");
  });

  it("falls back to the login form when a stale token is rejected and auto-login also fails", async () => {
    render(<Home />);
    await waitFor(() => expect(screen.getByText("Upload Email List")).toBeInTheDocument());

    global.fetch = jest.fn().mockRejectedValue(new Error("connection refused"));
    window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));

    await waitFor(() => expect(screen.getByText("Sign in to EzyMailer")).toBeInTheDocument());
  });

  it("logging in through the fallback form stores the token and proceeds to upload", async () => {
    window.sessionStorage.removeItem("eazyvalidator_auth_token");
    mockLoginToEzyMailer.mockResolvedValue("logged-in-token");

    render(<Home />);
    await waitFor(() => expect(screen.getByText("Sign in to EzyMailer")).toBeInTheDocument());

    await userEvent.type(screen.getByLabelText("Username"), "koushik");
    await userEvent.type(screen.getByLabelText("Password"), "secret");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => expect(screen.getByText("Upload Email List")).toBeInTheDocument());
    expect(mockLoginToEzyMailer).toHaveBeenCalledWith("koushik", "secret");
    expect(window.sessionStorage.getItem("eazyvalidator_auth_token")).toBe("logged-in-token");
  });

  it("shows the server's error message when the fallback login fails", async () => {
    window.sessionStorage.removeItem("eazyvalidator_auth_token");
    mockLoginToEzyMailer.mockRejectedValue(new Error("Invalid username or password."));

    render(<Home />);
    await waitFor(() => expect(screen.getByText("Sign in to EzyMailer")).toBeInTheDocument());

    await userEvent.type(screen.getByLabelText("Username"), "koushik");
    await userEvent.type(screen.getByLabelText("Password"), "wrong");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => expect(screen.getByText("Invalid username or password.")).toBeInTheDocument());
    expect(screen.queryByText("Upload Email List")).not.toBeInTheDocument();
  });

  it("picks up the token from the URL, stores it, and strips it from the address bar", async () => {
    window.sessionStorage.removeItem("eazyvalidator_auth_token");
    window.history.replaceState({}, "", "/?token=url-token&foo=bar");

    render(<Home />);

    await waitFor(() => expect(screen.getByText("Upload Email List")).toBeInTheDocument());
    expect(window.sessionStorage.getItem("eazyvalidator_auth_token")).toBe("url-token");
    expect(window.location.search).toBe("?foo=bar");

    window.history.replaceState({}, "", "/");
  });

  it("restores an in-progress job after a refresh instead of dropping back to upload", async () => {
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ jobId: "job-123", stage: "validating", totalRecords: 50 })
    );
    mockGetProgress.mockResolvedValue({
      job_id: "job-123",
      status: "validating",
      total: 50,
      processed: 10,
      remaining: 40,
      valid: 0,
      invalid: 0,
      risky: 0,
      unknown: 0,
      percent: 20,
      emails_per_second: 1,
      eta_seconds: 40,
      started_at: null,
      completed_at: null,
      recent_activity: [],
    } satisfies ProgressResponse);

    render(<Home />);

    await waitFor(() => expect(screen.getByText("Validation Progress")).toBeInTheDocument());
    expect(screen.queryByText("Upload Email List")).not.toBeInTheDocument();
    expect(mockGetProgress).toHaveBeenCalledWith("job-123");
  });

  it("restores a completed job's results view after a refresh", async () => {
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ jobId: "job-456", stage: "completed", totalRecords: 10 })
    );
    mockGetResults.mockResolvedValue({
      job_id: "job-456",
      page: 1,
      page_size: 50,
      total_rows: 0,
      total_pages: 0,
      filter: "all",
      search: null,
      rows: [],
    } satisfies ResultsPage);
    mockGetReport.mockResolvedValue({
      job_id: "job-456",
      total_uploaded: 10,
      unique_emails: 10,
      duplicate_emails: 0,
      valid_count: 10,
      invalid_count: 0,
      risky_count: 0,
      unknown_count: 0,
      disposable_count: 0,
      free_provider_count: 0,
      role_based_count: 0,
      success_percent: 100,
      validation_duration_seconds: 5,
      started_at: null,
      completed_at: null,
    } satisfies SummaryReport);

    render(<Home />);

    await waitFor(() => expect(screen.getByText("Export Results")).toBeInTheDocument());
    expect(screen.getByText("Validation Results")).toBeInTheDocument();
  });

  it("clears the persisted session when the user resets to validate another file", async () => {
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ jobId: "job-456", stage: "completed", totalRecords: 10 })
    );
    mockGetResults.mockResolvedValue({
      job_id: "job-456",
      page: 1,
      page_size: 50,
      total_rows: 0,
      total_pages: 0,
      filter: "all",
      search: null,
      rows: [],
    } satisfies ResultsPage);
    mockGetReport.mockResolvedValue({
      job_id: "job-456",
      total_uploaded: 10,
      unique_emails: 10,
      duplicate_emails: 0,
      valid_count: 10,
      invalid_count: 0,
      risky_count: 0,
      unknown_count: 0,
      disposable_count: 0,
      free_provider_count: 0,
      role_based_count: 0,
      success_percent: 100,
      validation_duration_seconds: 5,
      started_at: null,
      completed_at: null,
    } satisfies SummaryReport);

    render(<Home />);
    await waitFor(() => expect(screen.getByText("Export Results")).toBeInTheDocument());

    await userEvent.click(screen.getByRole("button", { name: /validate another file/i }));

    await waitFor(() => expect(screen.getByText("Upload Email List")).toBeInTheDocument());
    expect(window.localStorage.getItem(STORAGE_KEY)).toBeNull();
  });

  it("shows the product name EazyValidator Pro in the header", async () => {
    render(<Home />);
    expect(screen.getByText("EazyValidator Pro")).toBeInTheDocument();
  });
});
