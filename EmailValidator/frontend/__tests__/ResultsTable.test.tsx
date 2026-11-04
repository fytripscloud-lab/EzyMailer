import { useState } from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import ResultsTable from "@/components/ResultsTable";
import { getResults } from "@/lib/api";
import type { ResultFilter, ResultsPage } from "@/lib/types";

jest.mock("@/lib/api", () => ({
  ...jest.requireActual("@/lib/api"),
  getResults: jest.fn(),
}));

const mockGetResults = getResults as jest.MockedFunction<typeof getResults>;

function makePage(overrides: Partial<ResultsPage> = {}): ResultsPage {
  return {
    job_id: "job-1",
    page: 1,
    page_size: 25,
    total_rows: 1,
    total_pages: 1,
    filter: "all",
    search: null,
    rows: [
      {
        row_no: 2,
        original: { Name: "Alice" },
        email: "alice@example.com",
        syntax_valid: true,
        domain_valid: true,
        mx_found: true,
        smtp: "accepted",
        disposable: false,
        free_provider: true,
        role_based: false,
        catch_all: "no",
        final_status: "valid",
        is_duplicate: false,
      },
    ],
    ...overrides,
  };
}

// Mimics how app/page.tsx owns filter/search state and feeds it back into
// ResultsTable as controlled props, since filter/search are lifted up so
// ExportSection can build a "Validation Results" export matching the table.
function ControlledResultsTable({ jobId, refreshKey }: { jobId: string; refreshKey?: number }) {
  const [filter, setFilter] = useState<ResultFilter>("all");
  return (
    <ResultsTable
      jobId={jobId}
      refreshKey={refreshKey}
      filter={filter}
      onFilterChange={setFilter}
      onSearchChange={() => {}}
    />
  );
}

describe("ResultsTable", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("loads and displays the first page of results", async () => {
    mockGetResults.mockResolvedValue(makePage());
    render(<ControlledResultsTable jobId="job-1" />);

    await waitFor(() => expect(screen.getByText("alice@example.com")).toBeInTheDocument());
    expect(mockGetResults).toHaveBeenCalledWith("job-1", {
      page: 1,
      pageSize: 25,
      filter: "all",
      search: "",
    });
  });

  it("refetches with the chosen filter when a filter chip is clicked", async () => {
    mockGetResults.mockResolvedValue(makePage());
    render(<ControlledResultsTable jobId="job-1" />);
    await waitFor(() => expect(mockGetResults).toHaveBeenCalled());

    mockGetResults.mockResolvedValue(
      makePage({ filter: "risky", rows: [], total_rows: 0 })
    );
    await userEvent.click(screen.getByText("Risky"));

    await waitFor(() =>
      expect(mockGetResults).toHaveBeenLastCalledWith(
        "job-1",
        expect.objectContaining({ filter: "risky" })
      )
    );
  });

  it("debounces search input before refetching and reports it to the parent", async () => {
    mockGetResults.mockResolvedValue(makePage());
    const onSearchChange = jest.fn();
    render(
      <ResultsTable jobId="job-1" filter="all" onFilterChange={() => {}} onSearchChange={onSearchChange} />
    );
    await waitFor(() => expect(mockGetResults).toHaveBeenCalled());

    await userEvent.type(screen.getByPlaceholderText(/search email/i), "alice");

    await waitFor(
      () =>
        expect(mockGetResults).toHaveBeenLastCalledWith(
          "job-1",
          expect.objectContaining({ search: "alice" })
        ),
      { timeout: 2000 }
    );
    expect(onSearchChange).toHaveBeenLastCalledWith("alice");
  });

  it("shows an error message when the request fails", async () => {
    mockGetResults.mockRejectedValue(new Error("server exploded"));
    render(<ControlledResultsTable jobId="job-1" />);

    await waitFor(() => expect(screen.getByText("server exploded")).toBeInTheDocument());
  });
});
