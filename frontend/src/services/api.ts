/**
 * Centralized API client for CodeShieldAI.
 *
 * Every backend call goes through here — components must never call
 * fetch() directly. This keeps the base URL, error handling, and
 * request/response typing in one place.
 */
import type {
  AITestResponse,
  Endpoint,
  FindingDetail,
  KnowledgeStats,
  Observation,
  Project,
  ProjectSummary,
  Report,
  Scan,
  ScanType,
  SourceFile,
  SourceUploadResponse,
  TargetType,
  User,
  WebPage,
} from "../types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

export class ApiRequestError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers ?? {}) },
    // Auth is cookie-based (HttpOnly access/refresh tokens) — this is
    // required for the browser to send/receive those cookies across
    // the frontend (5173) <-> backend (8000) origin boundary.
    credentials: "include",
    ...options,
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      // response had no JSON body — fall back to statusText
    }
    throw new ApiRequestError(detail, response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

// --- Health ---
export const getHealth = () => request<{ status: string; service: string; database: string }>("/health");

// --- Projects ---
export const listProjects = () => request<ProjectSummary[]>("/projects");
export const getProject = (projectId: string) => request<ProjectSummary>(`/projects/${projectId}`);
export const createProject = (payload: {
  name: string;
  description?: string;
  target_type: TargetType;
  target_value: string;
}) =>
  request<Project>("/projects", {
    method: "POST",
    body: JSON.stringify(payload),
  });
export const deleteProject = (projectId: string) =>
  request<void>(`/projects/${projectId}`, { method: "DELETE" });

// --- Scans ---
export const listScans = (projectId: string) => request<Scan[]>(`/projects/${projectId}/scans`);
export const getScan = (scanId: string) => request<Scan>(`/scans/${scanId}`);
export const createScan = (projectId: string, scanType: ScanType) =>
  request<Scan>(`/projects/${projectId}/scans`, {
    method: "POST",
    body: JSON.stringify({ scan_type: scanType }),
  });
export const deleteScan = (scanId: string) =>
  request<void>(`/scans/${scanId}`, {
    method: "DELETE",
  });
// --- Findings ---
export const listFindingsForScan = (scanId: string) => request<FindingDetail[]>(`/scans/${scanId}/findings`);
export const getFinding = (findingId: string) => request<FindingDetail>(`/findings/${findingId}`);

// --- Reports ---
export const listReportsForScan = (scanId: string) => request<Report[]>(`/reports/scan/${scanId}`);
export const generateReport = (scanId: string) =>
  request<Report>(`/scans/${scanId}/reports`, { method: "POST" });
export const downloadReportUrl = (reportId: string) => `${BASE_URL}/reports/${reportId}/download`;
export const deleteReport = (reportId: string) =>
  request<void>(`/reports/${reportId}`, {
    method: "DELETE",
  });

// --- Application map (dynamic analysis) ---
export const listScanPages = (scanId: string) => request<WebPage[]>(`/scans/${scanId}/pages`);
export const listScanEndpoints = (scanId: string) => request<Endpoint[]>(`/scans/${scanId}/endpoints`);

// --- Source ingestion (Phase 2) ---
export async function uploadSourceZip(projectId: string, file: File): Promise<SourceUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${BASE_URL}/projects/${projectId}/source/upload`, {
    method: "POST",
    body: formData,
    credentials: "include",
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      // no JSON body
    }
    throw new ApiRequestError(detail, response.status);
  }
  return (await response.json()) as SourceUploadResponse;
}

export const importGithubRepo = (projectId: string, repoUrl: string) =>
  request<SourceUploadResponse>(`/projects/${projectId}/source/github`, {
    method: "POST",
    body: JSON.stringify({ repo_url: repoUrl }),
  });

export const listProjectSourceFiles = (projectId: string) =>
  request<SourceFile[]>(`/projects/${projectId}/source-files`);

export const listScanSourceFiles = (scanId: string) => request<SourceFile[]>(`/scans/${scanId}/source-files`);

export const listScanObservations = (scanId: string) => request<Observation[]>(`/scans/${scanId}/observations`);

// --- Knowledge base (RAG) ---
export const getKnowledgeStats = () => request<KnowledgeStats>("/knowledge/stats");

// --- AI ---
export const testAI = (prompt: string) =>
  request<AITestResponse>("/ai/test", {
    method: "POST",
    body: JSON.stringify({ prompt }),
  });

// --- Auth ---
export const registerUser = (payload: { name: string; email: string; password: string; confirm_password: string }) =>
  request<User>("/auth/register", { method: "POST", body: JSON.stringify(payload) });

export const loginUser = (payload: { email: string; password: string }) =>
  request<User>("/auth/login", { method: "POST", body: JSON.stringify(payload) });

export const logoutUser = () => request<void>("/auth/logout", { method: "POST" });

export const getCurrentUser = () => request<User>("/auth/me");

export const changePassword = (payload: { current_password: string; new_password: string }) =>
  request<void>("/auth/change-password", { method: "POST", body: JSON.stringify(payload) });

export const googleLoginUrl = () => `${BASE_URL}/auth/google`;
