export type TargetType = "website" | "github" | "zip";

export type ScanStatus = "pending" | "running" | "completed" | "failed";
export type ScanType = "source_code" | "web_application";

export type Severity = "informational" | "low" | "medium" | "high" | "critical";
export type FindingStatus = "potential" | "confirmed" | "open" | "false_positive" | "accepted_risk" | "resolved";

export interface Project {
  id: string;
  name: string;
  description: string | null;
  target_type: TargetType;
  target_value: string;
  created_at: string;
  updated_at: string;
}

export interface ProjectSummary extends Project {
  scan_count: number;
  finding_count: number;
  last_scan_status: ScanStatus | null;
}

export interface Scan {
  id: string;
  project_id: string;
  status: ScanStatus;
  scan_type: ScanType;
  current_stage: string | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  finding_count: number;
  pages_discovered: number;
  endpoints_discovered: number;
  requests_made: number;
}

export type ScanStage =
  | "queued"
  | "extracting"
  | "parsing"
  | "static_analysis"
  | "ai_analysis"
  | "scope_validation"
  | "reconnaissance"
  | "application_mapping"
  | "security_testing"
  | "evidence_collection"
  | "verification"
  | "completed"
  | "failed";

export interface SourceFile {
  id: string;
  project_id: string;
  path: string;
  language: string | null;
  size: number;
  function_count: number;
  class_count: number;
  created_at: string;
}

export interface SourceUploadResponse {
  files_ingested: number;
  total_size_bytes: number;
  languages: Record<string, number>;
}

export interface Observation {
  id: string;
  scan_id: string;
  source: string;
  observation_type: string;
  rule_id: string | null;
  file: string | null;
  line: number | null;
  message: string;
  raw_severity: string | null;
  raw_confidence: string | null;
  processed: boolean;
  created_at: string;
}

export interface KnowledgeStats {
  indexed_chunks: number;
  documents: string[];
}

export type AuthProvider = "password" | "google";

export interface User {
  id: string;
  name: string;
  email: string;
  auth_provider: AuthProvider;
  profile_image: string | null;
  created_at: string;
  last_login: string | null;
}

export interface Evidence {
  id: string;
  evidence_type: string;
  content: string;
  source: string | null;
  created_at: string;
}

export interface Finding {
  id: string;
  scan_id: string;
  title: string;
  category: string;
  severity: Severity;
  confidence: number;
  description: string | null;

  file: string | null;
  line: number | null;
  start_line: number | null;
  end_line: number | null;
  start_column: number | null;
  end_column: number | null;
  code_snippet: string | null;

  endpoint: string | null;
  http_method: string | null;
  parameter: string | null;

  analyzer: string | null;
  rule_id: string | null;

  impact: string | null;
  recommendation: string | null;
  cwe_id: string | null;
  owasp_category: string | null;

  verified: boolean;
  verification_method: string | null;
  verification_reason: string | null;
  reasoning_steps: string | null;

  status: FindingStatus;
  created_at: string;
}

export interface WebPage {
  id: string;
  url: string;
  title: string | null;
  status_code: number | null;
  form_count: number;
  link_count: number;
  created_at: string;
}

export interface Endpoint {
  id: string;
  method: string;
  url: string;
  parameters_json: string | null;
  response_headers_json: string | null;
  cookies_json: string | null;
  source: string;
  created_at: string;
}

export interface FindingDetail extends Finding {
  evidence: Evidence[];
}

export interface Report {
  id: string;
  scan_id: string;
  report_name: string;
  report_type: string;
  file_path: string | null;
  created_at: string;
}

export interface AITestResponse {
  prompt: string;
  response: string;
  model: string;
}

export interface ApiError {
  detail: string;
}
