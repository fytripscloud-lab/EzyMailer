import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import axios from "axios";

import ValidationProgress from "@/components/ValidationProgress";
import { cancelJob, getProgress } from "@/lib/api";
import type { ProgressResponse } from "@/lib/types";

jest.mock("@/lib/api", () => ({
  ...jest.requireActual("@/lib/api"),
  getProgress: jest.fn(),
  cancelJob: jest.fn(),
}));

const mockGetProgress = getProgress as jest.MockedFunction<typeof getProgress>;
const mockCancelJob = cancelJob as jest.MockedFunction<typeof cancelJob>;

function makeProgress(overrides: Partial<ProgressResponse> = {}): ProgressResponse {
  return {
    job_id: "job-1",
    status: "validating",
    total: 100,
    processed: 10,
    remaining: 90,
    valid: 5,
    invalid: 2,
    risky: 2,
    unknown: 1,
    percent: 10,
    emails_per_second: 3.2,
    eta_seconds: 28,
    started_at: "2026-01-01T00:00:00Z",
    completed_at: null,
    recent_activity: [
      { email: "alice@example.com", status: "valid", timestamp: "10:00:01" },
      { email: "bad@nowhere.invalid", status: "invalid", timestamp: "10:00:02" },
    ],
    ...overrides,
  };
}

describe("ValidationProgress", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders the live activity terminal with recent checks", async () => {
    mockGetProgress.mockResolvedValue(makeProgress());
    render(<ValidationProgress jobId="job-1" totalRecords={100} onCompleted={jest.fn()} onReset={jest.fn()} />);

    await waitFor(() => expect(screen.getByText(/alice@example.com/)).toBeInTheDocument());
    expect(screen.getByText(/bad@nowhere.invalid/)).toBeInTheDocument();
    expect(screen.getByText("VALID")).toBeInTheDocument();
    expect(screen.getByText("INVALID")).toBeInTheDocument();
  });

  it("calls onCompleted once validation finishes", async () => {
    const onCompleted = jest.fn();
    mockGetProgress.mockResolvedValue(makeProgress({ status: "completed", percent: 100 }));
    render(<ValidationProgress jobId="job-1" totalRecords={100} onCompleted={onCompleted} onReset={jest.fn()} />);

    await waitFor(() => expect(onCompleted).toHaveBeenCalled());
  });

  it("shows a waiting placeholder before any activity arrives", async () => {
    mockGetProgress.mockResolvedValue(makeProgress({ recent_activity: [] }));
    render(<ValidationProgress jobId="job-1" totalRecords={100} onCompleted={jest.fn()} onReset={jest.fn()} />);

    await waitFor(() => expect(screen.getByText(/waiting for the first results/i)).toBeInTheDocument());
  });

  it("shows an error banner and does not call onCompleted when the job failed (e.g. orphaned by a server restart)", async () => {
    const onCompleted = jest.fn();
    mockGetProgress.mockResolvedValue(
      makeProgress({
        status: "failed",
        error: "Validation was interrupted by a server restart. Please start validation again.",
        recent_activity: [],
      })
    );
    render(<ValidationProgress jobId="job-1" totalRecords={100} onCompleted={onCompleted} onReset={jest.fn()} />);

    await waitFor(() => expect(screen.getByText(/interrupted by a server restart/i)).toBeInTheDocument());
    expect(onCompleted).not.toHaveBeenCalled();
  });

  it("calls onReset when 'Start Over' is clicked on a failed job", async () => {
    const onReset = jest.fn();
    mockGetProgress.mockResolvedValue(makeProgress({ status: "failed", error: "boom", recent_activity: [] }));
    render(<ValidationProgress jobId="job-1" totalRecords={100} onCompleted={jest.fn()} onReset={onReset} />);

    await waitFor(() => expect(screen.getByText("boom")).toBeInTheDocument());
    await userEvent.click(screen.getByRole("button", { name: /start over/i }));

    expect(onReset).toHaveBeenCalledTimes(1);
  });

  it("shows the ETA formatted in minutes rather than raw seconds", async () => {
    mockGetProgress.mockResolvedValue(makeProgress({ eta_seconds: 2190 }));
    render(<ValidationProgress jobId="job-1" totalRecords={100} onCompleted={jest.fn()} onReset={jest.fn()} />);

    await waitFor(() => expect(screen.getByText(/Estimated time remaining: 36m 30s/)).toBeInTheDocument());
  });

  it("asks for confirmation before cancelling, and does not cancel if dismissed", async () => {
    mockGetProgress.mockResolvedValue(makeProgress());
    render(<ValidationProgress jobId="job-1" totalRecords={100} onCompleted={jest.fn()} onReset={jest.fn()} />);
    await waitFor(() => expect(screen.getByRole("button", { name: /^cancel$/i })).toBeInTheDocument());

    await userEvent.click(screen.getByRole("button", { name: /^cancel$/i }));
    expect(await screen.findByText(/cancel validation\?/i)).toBeInTheDocument();
    expect(mockCancelJob).not.toHaveBeenCalled();

    await userEvent.click(screen.getByRole("button", { name: /keep validating/i }));
    await waitFor(() => expect(screen.queryByText(/cancel validation\?/i)).not.toBeInTheDocument());
    expect(mockCancelJob).not.toHaveBeenCalled();
  });

  it("cancels the job only after confirming in the dialog", async () => {
    mockGetProgress.mockResolvedValue(makeProgress());
    mockCancelJob.mockResolvedValue(undefined);
    render(<ValidationProgress jobId="job-1" totalRecords={100} onCompleted={jest.fn()} onReset={jest.fn()} />);
    await waitFor(() => expect(screen.getByRole("button", { name: /^cancel$/i })).toBeInTheDocument());

    await userEvent.click(screen.getByRole("button", { name: /^cancel$/i }));
    await userEvent.click(screen.getByRole("button", { name: /cancel validation/i }));

    await waitFor(() => expect(mockCancelJob).toHaveBeenCalledWith("job-1"));
  });

  it("stops and offers 'Start Over' when the job can no longer be found (404)", async () => {
    const onReset = jest.fn();
    const notFoundError = Object.assign(new Error("Not Found"), {
      isAxiosError: true,
      response: { status: 404, data: { detail: "job not found" } },
    });
    jest.spyOn(axios, "isAxiosError").mockReturnValue(true);
    mockGetProgress.mockRejectedValue(notFoundError);

    render(<ValidationProgress jobId="gone-job" totalRecords={100} onCompleted={jest.fn()} onReset={onReset} />);

    await waitFor(() => expect(screen.getByText(/could no longer be found/i)).toBeInTheDocument());
    await userEvent.click(screen.getByRole("button", { name: /start over/i }));
    expect(onReset).toHaveBeenCalledTimes(1);

    (axios.isAxiosError as unknown as jest.Mock).mockRestore();
  });
});
