import axios from "axios";

import { getAuthToken, notifyUnauthorized } from "./auth";
import type {
  DiagnosticsResponse,
  ProgressResponse,
  ResultsPage,
  SummaryReport,
  UploadResponse,
} from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const client = axios.create({ baseURL: API_BASE_URL });

client.interceptors.request.use((config) => {
  const token = getAuthToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (axios.isAxiosError(error) && error.response?.status === 401) {
      notifyUnauthorized();
    }
    return Promise.reject(error);
  }
);

const BASE = "/api/v1/bulk-validator";

export async function uploadFile(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await client.post<UploadResponse>(`${BASE}/upload`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function startValidation(
  jobId: string,
  options: { emailColumn?: string; sheetName?: string } = {}
): Promise<ProgressResponse> {
  const { data } = await client.post<ProgressResponse>(`${BASE}/start/${jobId}`, {
    email_column: options.emailColumn ?? null,
    sheet_name: options.sheetName ?? null,
  });
  return data;
}

export async function getProgress(jobId: string): Promise<ProgressResponse> {
  const { data } = await client.get<ProgressResponse>(`${BASE}/progress/${jobId}`);
  return data;
}

export async function getResults(
  jobId: string,
  params: { page?: number; pageSize?: number; filter?: string; search?: string } = {}
): Promise<ResultsPage> {
  const { data } = await client.get<ResultsPage>(`${BASE}/results/${jobId}`, {
    params: {
      page: params.page ?? 1,
      page_size: params.pageSize ?? 50,
      filter: params.filter ?? "all",
      search: params.search || undefined,
    },
  });
  return data;
}

export async function getReport(jobId: string): Promise<SummaryReport> {
  const { data } = await client.get<SummaryReport>(`${BASE}/report/${jobId}`);
  return data;
}

export function getExportUrl(
  jobId: string,
  format: "xlsx" | "csv" | "pdf",
  scope: { filter?: string; search?: string } = {}
): string {
  const params = new URLSearchParams({ format });
  if (scope.filter && scope.filter !== "all") params.set("filter", scope.filter);
  if (scope.search) params.set("search", scope.search);
  // A plain <a href> download can't set an Authorization header, so the
  // token rides along as a query param here (the backend accepts either).
  const token = getAuthToken();
  if (token) params.set("token", token);
  return `${API_BASE_URL}${BASE}/export/${jobId}?${params.toString()}`;
}

export async function cancelJob(jobId: string): Promise<void> {
  await client.post(`${BASE}/cancel/${jobId}`);
}

export async function deleteJob(jobId: string): Promise<void> {
  await client.delete(`${BASE}/job/${jobId}`);
}

export async function getDiagnostics(options: { refresh?: boolean } = {}): Promise<DiagnosticsResponse> {
  const { data } = await client.get<DiagnosticsResponse>("/api/v1/system/diagnostics", {
    params: options.refresh ? { refresh: true } : undefined,
  });
  return data;
}

export function extractErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    return error.message;
  }
  return error instanceof Error ? error.message : "Unexpected error";
}
