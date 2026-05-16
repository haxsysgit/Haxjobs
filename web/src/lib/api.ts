import type {
  AnalysisMode,
  AnalysisResponse,
  DemoOptionsResponse,
  HealthResponse
} from "../types";

type ApiErrorKind = "backend_unavailable" | "request_failed";

export class ApiError extends Error {
  kind: ApiErrorKind;

  constructor(message: string, kind: ApiErrorKind) {
    super(message);
    this.name = "ApiError";
    this.kind = kind;
  }
}

export function getApiBaseUrl(): string {
  return (import.meta.env.VITE_API_BASE_URL ?? "").trim().replace(/\/$/, "");
}

export function buildApiUrl(path: string): string {
  const base = getApiBaseUrl();
  return `${base}${path.startsWith("/") ? path : `/${path}`}`;
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(buildApiUrl(path), init);
  } catch (error) {
    if (error instanceof TypeError) {
      throw new ApiError(
        "Backend unavailable. Start `./scripts/dev.sh start` and try again.",
        "backend_unavailable"
      );
    }
    throw error;
  }

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new ApiError(payload?.detail ?? "Analysis failed.", "request_failed");
  }

  return (await response.json()) as T;
}

export async function getHealth(): Promise<HealthResponse> {
  return requestJson<HealthResponse>("/api/health");
}

export async function getDemoOptions(): Promise<DemoOptionsResponse> {
  return requestJson<DemoOptionsResponse>("/api/demo-options");
}

export async function analyzeCv(
  file: File,
  jdText: string,
  mode: AnalysisMode
): Promise<AnalysisResponse> {
  const formData = new FormData();
  formData.append("cv_file", file);
  formData.append("jd_text", jdText);
  formData.append("mode", mode);
  return requestJson<AnalysisResponse>("/api/analyze", {
    method: "POST",
    body: formData
  });
}

export async function analyzeDemo(
  cvFixture: string,
  jdFixture: string,
  mode: AnalysisMode
): Promise<AnalysisResponse> {
  return requestJson<AnalysisResponse>("/api/analyze-demo", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      cv_fixture: cvFixture,
      jd_fixture: jdFixture,
      mode
    })
  });
}
