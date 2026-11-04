import axios from "axios";

import { extractErrorMessage, getExportUrl } from "@/lib/api";

afterEach(() => {
  jest.restoreAllMocks();
});

describe("getExportUrl", () => {
  it("builds the correct export URL per format", () => {
    expect(getExportUrl("abc123", "xlsx")).toContain("/api/v1/bulk-validator/export/abc123?format=xlsx");
    expect(getExportUrl("abc123", "csv")).toContain("format=csv");
    expect(getExportUrl("abc123", "pdf")).toContain("format=pdf");
  });
});

describe("extractErrorMessage", () => {
  it("extracts the detail field from an axios error response", () => {
    const error = {
      isAxiosError: true,
      response: { data: { detail: "job not found" } },
      message: "Request failed with status code 404",
    };
    jest.spyOn(axios, "isAxiosError").mockReturnValue(true);
    expect(extractErrorMessage(error)).toBe("job not found");
  });

  it("falls back to the axios error message when there is no detail", () => {
    const error = {
      isAxiosError: true,
      response: undefined,
      message: "Network Error",
    };
    jest.spyOn(axios, "isAxiosError").mockReturnValue(true);
    expect(extractErrorMessage(error)).toBe("Network Error");
  });

  it("handles plain Error instances", () => {
    jest.spyOn(axios, "isAxiosError").mockReturnValue(false);
    expect(extractErrorMessage(new Error("boom"))).toBe("boom");
  });

  it("handles unknown thrown values", () => {
    jest.spyOn(axios, "isAxiosError").mockReturnValue(false);
    expect(extractErrorMessage("just a string")).toBe("Unexpected error");
  });
});
