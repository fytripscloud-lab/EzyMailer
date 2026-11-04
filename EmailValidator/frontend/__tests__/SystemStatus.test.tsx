import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import SystemStatus from "@/components/SystemStatus";
import { getDiagnostics } from "@/lib/api";
import type { DiagnosticsResponse } from "@/lib/types";

jest.mock("@/lib/api", () => ({
  ...jest.requireActual("@/lib/api"),
  getDiagnostics: jest.fn(),
}));

const mockGetDiagnostics = getDiagnostics as jest.MockedFunction<typeof getDiagnostics>;

function makeDiagnostics(overrides: Partial<DiagnosticsResponse> = {}): DiagnosticsResponse {
  return {
    checked_at: "2026-01-01T00:00:00Z",
    backend: "ok",
    dns: "ok",
    dns_detail: "resolved MX for gmail.com (mx.gmail.com)",
    smtp_port_25: "open",
    smtp_detail: "connected to mx.gmail.com on port 25",
    smtp_check_enabled: true,
    catch_all_check_enabled: true,
    smtp_concurrency: 5,
    dns_concurrency: 20,
    max_upload_size_mb: 25,
    max_rows: 100000,
    job_retention_hours: 24,
    ...overrides,
  };
}

describe("SystemStatus", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("shows open SMTP port status with no warning", async () => {
    mockGetDiagnostics.mockResolvedValue(makeDiagnostics());
    render(<SystemStatus />);

    await waitFor(() => expect(screen.getByText(/SMTP Port 25: Open/)).toBeInTheDocument());
    expect(screen.getByText(/Backend API: Connected/)).toBeInTheDocument();
    expect(screen.getByText(/DNS Resolution: Working/)).toBeInTheDocument();
    expect(screen.queryByText(/looks blocked on this network/)).not.toBeInTheDocument();
  });

  it("shows a warning banner when port 25 is blocked", async () => {
    mockGetDiagnostics.mockResolvedValue(makeDiagnostics({ smtp_port_25: "blocked" }));
    render(<SystemStatus />);

    await waitFor(() => expect(screen.getByText(/SMTP Port 25: Blocked/)).toBeInTheDocument());
    expect(screen.getByText(/looks blocked on this network/)).toBeInTheDocument();
  });

  it("shows an info banner when SMTP checks are disabled", async () => {
    mockGetDiagnostics.mockResolvedValue(makeDiagnostics({ smtp_port_25: "disabled", smtp_check_enabled: false }));
    render(<SystemStatus />);

    await waitFor(() => expect(screen.getByText(/SMTP Port 25: Disabled/)).toBeInTheDocument());
    expect(screen.getByText(/SMTP mailbox checks are turned off/)).toBeInTheDocument();
  });

  it("shows an unreachable error when the backend call fails", async () => {
    mockGetDiagnostics.mockRejectedValue(new Error("Network Error"));
    render(<SystemStatus />);

    await waitFor(() => expect(screen.getByText(/Backend API: Unreachable/)).toBeInTheDocument());
    expect(screen.getByText(/Can't reach the backend API/)).toBeInTheDocument();
  });

  it("re-checks with refresh=true when the refresh button is clicked", async () => {
    mockGetDiagnostics.mockResolvedValue(makeDiagnostics());
    render(<SystemStatus />);
    await waitFor(() => expect(screen.getByText(/SMTP Port 25: Open/)).toBeInTheDocument());

    await userEvent.click(screen.getByRole("button", { name: /re-check now/i }));

    await waitFor(() => expect(mockGetDiagnostics).toHaveBeenLastCalledWith({ refresh: true }));
  });
});
