const BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? "";

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, init);
  } catch {
    throw new ApiError(0, "Cannot reach the API. Is the backend running on port 8000?");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail
        : Array.isArray(body.detail) ? body.detail.map((d: { loc: string[]; msg: string }) => `${d.loc.slice(1).join(".")}: ${d.msg}`).join("; ")
        : detail;
    } catch { /* keep statusText */ }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  get: <T,>(path: string) => request<T>(path),
  post: <T,>(path: string, body: unknown) =>
    request<T>(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }),
  patch: <T,>(path: string, body: unknown) =>
    request<T>(path, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }),
  upload: <T,>(path: string, file: File) => {
    const fd = new FormData(); fd.append("file", file);
    return request<T>(path, { method: "POST", body: fd });
  },
};

export type Risk = "Low" | "Medium" | "High";
export const STATUSES = ["Pending", "Confirmed Fraud", "Legitimate", "Escalated"] as const;
export type Status = (typeof STATUSES)[number];

export interface Impact { feature: string; value: number; impact: number }
export interface Prediction {
  id: number; probability: number; threshold: number; flagged: boolean; risk_level: Risk;
  model_version: string; latency_ms: number; explanation: Impact[];
}
export interface BatchResult {
  rows: number; flagged: number; flagged_rate: number; model_version: string; threshold: number; top: Prediction[];
}
export interface TxRow {
  id: number; created_at: string; source: string; amount: number; probability: number; threshold: number;
  flagged: boolean; risk_level: Risk; model_version: string; review_status: Status; review_note: string | null;
}
export interface TxDetail extends TxRow {
  features: Record<string, number>; latency_ms: number; explanation: Impact[];
  history: { created_at: string; action: string; detail: string }[];
}
export interface TxPage { items: TxRow[]; total: number; page: number; page_size: number }
export interface Metrics {
  total: number; flagged: number; flagged_rate: number; avg_probability: number;
  by_status: Record<Status, number>; by_risk: Record<Risk, number>;
  score_histogram: { bucket: string; count: number }[];
  daily: { date: string; total: number; flagged: number }[];
  review_quality: { reviewed_alerts: number; alert_precision: number | null; fraud_found_in_unflagged: number; marked_legitimate: number };
}
export interface Confusion {
  threshold: number; tp: number; fp: number; fn: number; tn: number; precision: number; recall: number; f1: number; flagged_rate: number;
  average_precision?: number; roc_auc?: number;
}
export interface ModelRow {
  name: string; fit_seconds: number; threshold: number; threshold_rule: string;
  validation: Confusion; test: Confusion;
  test_ci_95: { average_precision: [number, number]; precision: [number, number]; recall: [number, number] };
  latency_ms: { p50: number; p95: number }; pr_curve: { recall: number; precision: number }[];
}
export interface ModelInfo {
  model_version: string; model_name: string; trained_at: string; threshold: number; threshold_rule: string;
  selection_metric: string; split_strategy: string; dataset_note: string;
  splits: Record<string, { rows: number; fraud: number; fraud_rate: number }>;
  comparison: ModelRow[]; threshold_table: Confusion[]; feature_importance: { feature: string; importance: number }[];
}
export interface Monitoring {
  model_version: string; volume_24h: number; volume_7d: number; sample_size: number;
  latency_ms: { avg: number; p95: number }; api_errors_since_restart: number; score_mean: number;
  drift_status: string; drift_note: string; drift: { feature: string; shift_std: number }[];
}
export interface Sample { name: string; synthetic_label: number; values: Record<string, number> }
