import type {
  Project,
  CompressionConfig,
  ModelSource,
  TargetId,
  CatalogModel,
  ProgressEvent,
} from "@asicify/shared";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(
  path: string,
  init?: RequestInit & { token?: string },
): Promise<T> {
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(init?.headers ?? {}),
  };
  if (init?.token) {
    (headers as Record<string, string>).Authorization = `Bearer ${init.token}`;
  }
  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${path} ${res.status}: ${text}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  listProjects: (token: string) =>
    request<Project[]>("/api/projects", { token }),

  getProject: (id: string, token: string) =>
    request<Project>(`/api/projects/${id}`, { token }),

  createProject: (
    body: {
      name: string;
      model_source: ModelSource;
      compression: CompressionConfig;
      targets: TargetId[];
    },
    token: string,
  ) =>
    request<Project>("/api/projects", {
      method: "POST",
      body: JSON.stringify(body),
      token,
    }),

  startCompress: (id: string, token: string) =>
    request<{ job_id: string }>(`/api/projects/${id}/compress`, {
      method: "POST",
      token,
    }),

  startGenerateRtl: (id: string, token: string) =>
    request<{ job_id: string }>(`/api/projects/${id}/generate-rtl`, {
      method: "POST",
      token,
    }),

  catalog: () => request<CatalogModel[]>("/api/models/catalog"),

  targets: () => request<TargetId[]>("/api/targets"),
};

export function subscribeProgress(
  projectId: string,
  onEvent: (e: ProgressEvent) => void,
): () => void {
  const wsBase = API_BASE.replace(/^http/, "ws");
  const ws = new WebSocket(`${wsBase}/api/projects/${projectId}/progress`);
  ws.addEventListener("message", (m) => {
    try {
      onEvent(JSON.parse(m.data) as ProgressEvent);
    } catch {
      // ignore malformed
    }
  });
  return () => ws.close();
}
