/**
 * AVAE API client — base fetch wrapper with auth token injection.
 *
 * Usage from client components:
 *   const getToken = useAuthToken();
 *   const token = await getToken();
 *   const data = await apiJson<MyType>('/endpoint', { token });
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

export type ApiOptions = RequestInit & {
  /** Clerk JWT — when provided, adds Authorization: Bearer header */
  token?: string | null;
};

/**
 * Build full URL for API requests.
 */
function buildUrl(path: string): string {
  if (path.startsWith("http")) return path;
  // Next.js API proxy routes — same origin, no backend prefix
  if (path.startsWith("/api/")) return path;
  const base = API_URL.replace(/\/$/, "");
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${base}${p}`;
}

/**
 * Fetch wrapper that injects auth token when provided.
 */
export async function apiFetch(
  path: string,
  options: ApiOptions = {}
): Promise<Response> {
  const { token, ...init } = options;
  const url = buildUrl(path);
  const headers = new Headers(init.headers);

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  return fetch(url, { ...init, headers });
}

/**
 * API error with status and optional backend message.
 */
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public body?: unknown
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/**
 * Fetch JSON response. Throws ApiError on non-2xx.
 */
export async function apiJson<T>(
  path: string,
  options: ApiOptions = {}
): Promise<T> {
  const headers = new Headers(options.headers);
  if (
    options.method !== "GET" &&
    options.method !== "HEAD" &&
    !headers.has("Content-Type")
  ) {
    headers.set("Content-Type", "application/json");
  }

  const res = await apiFetch(path, { ...options, headers });

  if (!res.ok) {
    let body: unknown;
    try {
      body = await res.json();
    } catch {
      body = await res.text();
    }
    let msg: string | null = null;
    if (typeof body === "object" && body !== null) {
      if ("detail" in body && typeof (body as { detail?: unknown }).detail === "string") {
        msg = (body as { detail: string }).detail;
      } else if ("error" in body) {
        msg = String((body as { error?: string }).error);
      }
    }
    throw new ApiError(msg || res.statusText || `Request failed: ${res.status}`, res.status, body);
  }

  const text = await res.text();
  if (!text) return undefined as T;
  return JSON.parse(text) as T;
}

/** Task status from GET /status/{task_id} */
export interface TaskStatusResponse {
  task_id: string;
  status: string;
  progress: number;
  filename: string;
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
  error?: string | null;
}

/** Upload response from POST /upload */
export interface UploadResponse {
  task_ids: string[];
  total_files: number;
  message: string;
}

/**
 * Upload files to the backend. Uses FormData; do not set Content-Type (browser sets multipart boundary).
 *
 * When remediationForCheckpointId is set: single-file mode; attaches to AWAITING_CLIENT_REMEDIATION checkpoint.
 */
export async function uploadFiles(
  files: File[],
  params: {
    auditTarget: string;
    userId?: number;
    prompt?: string;
    token?: string | null;
    /** When set, single-file remediation upload for checkpoint (Task 4.8) */
    remediationForCheckpointId?: string | null;
  }
): Promise<UploadResponse> {
  const {
    auditTarget,
    userId = 1,
    prompt,
    token,
    remediationForCheckpointId,
  } = params;
  const search = new URLSearchParams({
    user_id: String(userId),
    audit_target: auditTarget,
  });
  if (prompt) search.set("prompt", prompt);
  if (remediationForCheckpointId) {
    search.set("remediation_for_checkpoint_id", remediationForCheckpointId);
  }

  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }

  // Use Next.js API proxy to avoid CORS issues (browser → localhost:3000 → backend)
  const uploadUrl =
    typeof window !== "undefined"
      ? `/api/upload?${search}`
      : `${buildUrl("/upload")}?${search}`;
  const headers = new Headers();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(uploadUrl, {
    method: "POST",
    headers,
    body: formData,
  });

  if (!res.ok) {
    let body: unknown;
    try {
      body = await res.json();
    } catch {
      body = await res.text();
    }
    const msg =
      typeof body === "object" && body !== null && "error" in body
        ? String((body as { error?: string }).error)
        : res.statusText;
    throw new ApiError(msg || `Upload failed: ${res.status}`, res.status, body);
  }

  return res.json() as Promise<UploadResponse>;
}

/**
 * Get PDF URL for document preview (Phase 5, Task 5.3).
 * Uses Next.js API proxy (same-origin) to avoid CORS.
 */
export function getDocumentPdfUrl(documentId: number | string): string {
  return `/api/documents/${documentId}/pdf`;
}

/** PDF location for highlighting (matches backend PdfLocation) */
export interface PdfLocation {
  page_index: number;
  left: number;
  top: number;
  width: number;
  height: number;
}

/** Verification table row (Task 5.4) */
export interface VerificationFieldRow {
  field: string;
  document_value: unknown;
  api_value: unknown;
  status: "VERIFIED" | "DISCREPANCY" | "PENDING";
  /** Location in PDF for interactive highlighting (red=discrepancy, green=verified) */
  pdf_location?: PdfLocation | null;
}

/** Response from GET /documents/{id}/verification */
export interface DocumentVerificationResponse {
  document_id: number;
  verification_status: string;
  audit_target: string;
  rows: VerificationFieldRow[];
  /** ISO timestamp when official registry was last synced (for "Live sync" display) */
  official_record_synced_at?: string | null;
}

/**
 * Fetch verification data for VerificationTable (Task 5.4).
 * Uses Next.js API proxy (same-origin).
 */
export async function getDocumentVerification(
  documentId: number | string,
  options: ApiOptions = {}
): Promise<DocumentVerificationResponse> {
  return apiJson<DocumentVerificationResponse>(
    `/api/documents/${documentId}/verification`,
    { ...options, cache: "no-store" }
  );
}

/** Task 5.8: HITL checkpoints */

export interface CheckpointListItem {
  checkpoint_id: string;
  filename: string;
  audit_target: string;
  status: string;
  document_preview?: Record<string, unknown> | null;
  discrepancy_flags?: unknown[] | null;
  created_at: string;
}

export interface CheckpointListResponse {
  checkpoints: CheckpointListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface GetCheckpointsParams {
  status?: string | null;
  audit_target?: string | null;
  page?: number;
  page_size?: number;
}

/**
 * Fetch HITL checkpoints (Task 5.8).
 * Uses Next.js API proxy.
 */
export async function getHitlCheckpoints(
  params: GetCheckpointsParams = {},
  options: ApiOptions = {}
): Promise<CheckpointListResponse> {
  const search = new URLSearchParams();
  if (params.status) search.set("status", params.status);
  if (params.audit_target) search.set("audit_target", params.audit_target);
  if (params.page != null) search.set("page", String(params.page));
  if (params.page_size != null) search.set("page_size", String(params.page_size));

  const qs = search.toString();
  return apiJson<CheckpointListResponse>(
    `/api/hitl/checkpoints${qs ? `?${qs}` : ""}`,
    { ...options, cache: "no-store" }
  );
}

/** Summary for Pending Reconciliation card (Phase 7.8) */
export interface CheckpointSummaryResponse {
  total: number;
  pending_review: number;
  awaiting_client: number;
}

export async function getHitlCheckpointsSummary(
  options: ApiOptions = {}
): Promise<CheckpointSummaryResponse> {
  return apiJson<CheckpointSummaryResponse>("/api/hitl/checkpoints/summary", {
    ...options,
    cache: "no-store",
  });
}

/** Similar override suggestion returned by Semantic Memory (Phase 8). */
export interface SimilarOverrideSuggestion {
  id: string;
  justification: string;
  field?: string;
  confidence?: number;
  /**
   * Phase 8.4: provenance for which override_memories informed each suggestion.
   * May be absent until backend is complete.
   */
  source_override_memory_ids?: string[];
}

/**
 * Get similar overrides for a HITL checkpoint (Task 8.3 UI).
 *
 * Expected backend route (not yet implemented in every env):
 *   GET /hitl/similar-overrides/{checkpoint_id}?field={field?}
 *
 * UI falls back to sample suggestions if this endpoint returns an error.
 */
export async function getSimilarOverrides(
  checkpointId: string,
  options: { field?: string | null } = {},
  apiOptions: ApiOptions = {}
): Promise<{ suggestions: SimilarOverrideSuggestion[] }> {
  const params = new URLSearchParams();
  if (options.field != null && options.field !== "") params.set("field", options.field);
  const qs = params.toString();

  return apiJson<{ suggestions: SimilarOverrideSuggestion[] }>(
    `/api/hitl/similar-overrides/${encodeURIComponent(checkpointId)}${qs ? `?${qs}` : ""}`,
    { ...apiOptions, cache: "no-store" }
  );
}

/** Task 5.7: HITL actions */

export interface HITLResponse {
  success: boolean;
  message: string;
  task_id?: string;
  status?: string;
  email_draft?: { subject: string; body: string };
}

/** Approve Entry — POST /hitl/override (Task 6.3: justification required) */
export async function hitlOverride(
  checkpointId: string,
  params?: { field?: string | null; justification?: string | null },
  options: ApiOptions = {}
): Promise<HITLResponse> {
  const body: Record<string, unknown> = { checkpoint_id: checkpointId };
  if (params?.field != null) body.field = params.field;
  if (params?.justification != null) body.justification = params.justification;
  return apiJson<HITLResponse>("/api/hitl/override", {
    ...options,
    method: "POST",
    body: JSON.stringify(body),
  });
}

/** Manual Correction — POST /hitl/manual-correction (Task 6.4) */
export async function hitlManualCorrection(
  checkpointId: string,
  corrections: Record<string, unknown>,
  options: ApiOptions = {}
): Promise<HITLResponse> {
  return apiJson<HITLResponse>("/api/hitl/manual-correction", {
    ...options,
    method: "POST",
    body: JSON.stringify({ checkpoint_id: checkpointId, corrections }),
  });
}

/** Remediation email draft — GET /hitl/remediation-email/{checkpoint_id} (Task 6.5, 6.7) */
export interface RemediationEmailDraft {
  subject: string;
  body: string;
}

export async function getRemediationEmailDraft(
  checkpointId: string,
  message?: string | null,
  options: ApiOptions = {}
): Promise<RemediationEmailDraft> {
  const search = message ? `?message=${encodeURIComponent(message)}` : "";
  return apiJson<RemediationEmailDraft>(
    `/api/hitl/remediation-email/${checkpointId}${search}`,
    { ...options, cache: "no-store" }
  );
}

/** Flag for Manual Review — POST /hitl/request-client-remediation */
export async function hitlRequestClientRemediation(
  checkpointId: string,
  message?: string | null,
  options: ApiOptions = {}
): Promise<HITLResponse> {
  return apiJson<HITLResponse>("/api/hitl/request-client-remediation", {
    ...options,
    method: "POST",
    body: JSON.stringify({ checkpoint_id: checkpointId, message: message ?? null }),
  });
}

/** Re-run Extraction — POST /documents/{id}/requeue */
export async function requeueDocument(
  documentId: number | string,
  options: ApiOptions = {}
): Promise<{ success: boolean; message: string; message_id?: string }> {
  return apiJson<{ success: boolean; message: string; message_id?: string }>(
    `/api/documents/${documentId}/requeue`,
    { ...options, method: "POST" }
  );
}

/** Audit log list item (Phase 7.2) */
export interface AuditLogListItem {
  id: number;
  document_id: number;
  created_at: string;
  audit_target: string;
  verification_status: string;
  filename: string;
}

/** Paginated audit logs response (Phase 7.6) */
export interface AuditLogListResponse {
  items: AuditLogListItem[];
  total: number;
  page: number;
  page_size: number;
}

/** Audit Health Index stats (Phase 7.7) */
export interface AuditHealthStatsResponse {
  total: number;
  verified: number;
  discrepancy_flag: number;
  pending_human_review: number;
  success_rate: number;
  trend_direction: "up" | "down" | "stable";
  trend_value: number;
}

/** Full audit log entry for expand row (Phase 7.9) */
export interface AuditLogDetailResponse {
  id: number;
  document_id: number;
  created_at: string;
  audit_target: string;
  verification_status: string;
  filename: string;
  extracted_json: Record<string, unknown>;
  api_response_json: Record<string, unknown> | null;
  discrepancy_flags: unknown[] | null;
  fields_compared: unknown[] | null;
}

/** Full audit log details — GET /audit-logs/{id} (Phase 7.9) */
export async function getAuditLogDetails(
  auditLogId: number,
  options: ApiOptions = {}
): Promise<AuditLogDetailResponse> {
  return apiJson<AuditLogDetailResponse>(`/api/audit-logs/${auditLogId}`, {
    ...options,
    cache: "no-store",
  });
}

export interface GetAuditLogsParams {
  status?: string | null;
  audit_target?: string | null;
  date_from?: string | null;
  date_to?: string | null;
  search?: string | null;
  page?: number;
  page_size?: number;
}

/** List audit logs — GET /audit-logs (Phase 7.2, 7.6) */
export async function getAuditLogs(
  params: GetAuditLogsParams = {},
  options: ApiOptions = {}
): Promise<AuditLogListResponse> {
  const search = new URLSearchParams();
  if (params.status != null && params.status !== "") search.set("status", params.status);
  if (params.audit_target != null && params.audit_target !== "")
    search.set("audit_target", params.audit_target);
  if (params.date_from != null && params.date_from !== "")
    search.set("date_from", params.date_from);
  if (params.date_to != null && params.date_to !== "")
    search.set("date_to", params.date_to);
  if (params.search != null && params.search.trim() !== "")
    search.set("search", params.search.trim());
  if (params.page != null) search.set("page", String(params.page));
  if (params.page_size != null) search.set("page_size", String(params.page_size));
  const qs = search.toString();
  return apiJson<AuditLogListResponse>(
    `/api/audit-logs${qs ? `?${qs}` : ""}`,
    { ...options, cache: "no-store" }
  );
}

/** Audit Health Index — GET /audit-logs/stats (Phase 7.7) */
export async function getAuditLogsStats(
  params: { date_from?: string | null; date_to?: string | null } = {},
  options: ApiOptions = {}
): Promise<AuditHealthStatsResponse> {
  const search = new URLSearchParams();
  if (params.date_from != null && params.date_from !== "")
    search.set("date_from", params.date_from);
  if (params.date_to != null && params.date_to !== "")
    search.set("date_to", params.date_to);
  const qs = search.toString();
  return apiJson<AuditHealthStatsResponse>(
    `/api/audit-logs/stats${qs ? `?${qs}` : ""}`,
    { ...options, cache: "no-store" }
  );
}

/**
 * Fetch task status from GET /status/{task_id}.
 * Uses cache: 'no-store' to prevent stale status (critical for compliance).
 */
export async function getTaskStatus(
  taskId: string,
  options: ApiOptions = {}
): Promise<TaskStatusResponse> {
  return apiJson<TaskStatusResponse>(`/status/${taskId}`, {
    ...options,
    cache: "no-store",
  });
}
