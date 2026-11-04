import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import ExportSection from "@/components/ExportSection";

describe("ExportSection", () => {
  let openSpy: jest.SpyInstance;

  beforeEach(() => {
    openSpy = jest.spyOn(window, "open").mockImplementation(() => null);
  });

  afterEach(() => {
    openSpy.mockRestore();
  });

  it("downloads the full workbook with no filter params when 'All' is chosen", async () => {
    render(<ExportSection jobId="job-1" filter="risky" search="alice" />);

    await userEvent.click(screen.getByRole("button", { name: /download excel/i }));
    await userEvent.click(screen.getByText("All"));

    expect(openSpy).toHaveBeenCalledTimes(1);
    const url = openSpy.mock.calls[0][0] as string;
    expect(url).toContain("/export/job-1");
    expect(url).toContain("format=xlsx");
    expect(url).not.toContain("filter=");
    expect(url).not.toContain("search=");
  });

  it("downloads a scoped export matching the current filter/search when 'Validation Results' is chosen", async () => {
    render(<ExportSection jobId="job-1" filter="risky" search="alice" />);

    await userEvent.click(screen.getByRole("button", { name: /download excel/i }));
    await userEvent.click(screen.getByText("Validation Results"));

    expect(openSpy).toHaveBeenCalledTimes(1);
    const url = openSpy.mock.calls[0][0] as string;
    expect(url).toContain("format=xlsx");
    expect(url).toContain("filter=risky");
    expect(url).toContain("search=alice");
  });

  it("shows the current scope description in the menu", async () => {
    render(<ExportSection jobId="job-1" filter="risky" search="alice" />);

    await userEvent.click(screen.getByRole("button", { name: /download excel/i }));

    expect(screen.getByText(/Risky.*search "alice"/)).toBeInTheDocument();
  });

  it("downloads CSV and PDF directly without a menu", async () => {
    render(<ExportSection jobId="job-1" filter="all" search="" />);

    await userEvent.click(screen.getByRole("button", { name: /download csv/i }));
    await userEvent.click(screen.getByRole("button", { name: /download report/i }));

    expect(openSpy).toHaveBeenCalledTimes(2);
    expect(openSpy.mock.calls[0][0]).toContain("format=csv");
    expect(openSpy.mock.calls[1][0]).toContain("format=pdf");
  });
});
