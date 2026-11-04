import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import UploadSection from "@/components/UploadSection";
import { deleteJob, startValidation, uploadFile } from "@/lib/api";
import type { UploadResponse } from "@/lib/types";

jest.mock("@/lib/api", () => ({
  ...jest.requireActual("@/lib/api"),
  uploadFile: jest.fn(),
  startValidation: jest.fn(),
  deleteJob: jest.fn(),
}));

const mockUploadFile = uploadFile as jest.MockedFunction<typeof uploadFile>;
const mockStartValidation = startValidation as jest.MockedFunction<typeof startValidation>;
const mockDeleteJob = deleteJob as jest.MockedFunction<typeof deleteJob>;

const baseUploadResponse: UploadResponse = {
  job_id: "job-123",
  filename: "contacts.csv",
  size_bytes: 2048,
  total_records: 10,
  detected_email_column: "Email",
  available_columns: ["Name", "Email"],
  sheet_names: ["Sheet1"],
  selected_sheet: "Sheet1",
  requires_column_selection: false,
};

function makeFile(name: string, content = "a,b\n1,2") {
  return new File([content], name, { type: "text/csv" });
}

describe("UploadSection", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("uploads a dropped file and displays its metadata", async () => {
    mockUploadFile.mockResolvedValue(baseUploadResponse);
    const onStarted = jest.fn();
    render(<UploadSection onStarted={onStarted} />);

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    await userEvent.upload(input, makeFile("contacts.csv"));

    await waitFor(() => expect(screen.getByText("contacts.csv")).toBeInTheDocument());
    expect(screen.getByText("10 records")).toBeInTheDocument();
    expect(mockUploadFile).toHaveBeenCalledTimes(1);
  });

  it("shows a warning and requires manual column selection when auto-detect fails", async () => {
    mockUploadFile.mockResolvedValue({
      ...baseUploadResponse,
      detected_email_column: null,
      requires_column_selection: true,
    });
    render(<UploadSection onStarted={jest.fn()} />);

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    await userEvent.upload(input, makeFile("contacts.csv"));

    await waitFor(() =>
      expect(screen.getByText(/could not automatically detect an email column/i)).toBeInTheDocument()
    );
  });

  it("starts validation with the selected column and notifies the parent", async () => {
    mockUploadFile.mockResolvedValue(baseUploadResponse);
    mockStartValidation.mockResolvedValue({
      job_id: "job-123",
      status: "validating",
      total: 10,
      processed: 0,
      remaining: 10,
      valid: 0,
      invalid: 0,
      risky: 0,
      unknown: 0,
      percent: 0,
      emails_per_second: 0,
      eta_seconds: null,
      started_at: null,
      completed_at: null,
      recent_activity: [],
    });
    const onStarted = jest.fn();
    render(<UploadSection onStarted={onStarted} />);

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    await userEvent.upload(input, makeFile("contacts.csv"));
    await waitFor(() => expect(screen.getByText("contacts.csv")).toBeInTheDocument());

    const startButton = screen.getByRole("button", { name: /start validation/i });
    await userEvent.click(startButton);

    await waitFor(() => expect(mockStartValidation).toHaveBeenCalledWith("job-123", { emailColumn: "Email" }));
    expect(onStarted).toHaveBeenCalledWith("job-123", 10);
  });

  it("removes the uploaded file and deletes the job on the backend", async () => {
    mockUploadFile.mockResolvedValue(baseUploadResponse);
    mockDeleteJob.mockResolvedValue(undefined);
    render(<UploadSection onStarted={jest.fn()} />);

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    await userEvent.upload(input, makeFile("contacts.csv"));
    await waitFor(() => expect(screen.getByText("contacts.csv")).toBeInTheDocument());

    await userEvent.click(screen.getByRole("button", { name: /remove file/i }));

    await waitFor(() => expect(mockDeleteJob).toHaveBeenCalledWith("job-123"));
    expect(screen.queryByText("contacts.csv")).not.toBeInTheDocument();
  });

  it("shows an error message when the upload fails", async () => {
    mockUploadFile.mockRejectedValue(new Error("file too large"));
    render(<UploadSection onStarted={jest.fn()} />);

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    await userEvent.upload(input, makeFile("contacts.csv"));

    await waitFor(() => expect(screen.getByText("file too large")).toBeInTheDocument());
  });
});
