export type SourceFile = { path: string; content: string };

export type AnalysisRequest = {
  project_name: string;
  files: SourceFile[];
  provider: string;
  model?: string;
  variant?: string;
  iterations: number;
  mode: "auto" | "direct" | "async";
  instruction?: string;
};

export type Artifact = { path: string; title: string; content: string; kind: string };
export type ProviderAuth = {
  provider?: string;
  apiKey?: string;
  baseUrl?: string;
  authMode?: "api_key" | "bearer";
};
export type AnalysisResult = {
  analysis_id: string;
  summary: {
    project_name: string;
    status: string;
    provider: string;
    model: string;
    files_analyzed: number;
    total_lines: number;
    ui_elements: number;
    flows: number;
    endpoints: number;
    risks: number;
    contradictions: number;
    iterations_completed: number;
  };
  report: Record<string, unknown>;
  artifacts: Artifact[];
  response_text: string;
};

export type AnalysisProgress = {
  status: string;
  progress: number;
  stage: string;
  message: string;
};

const API = import.meta.env.VITE_API_URL || "";

async function parse<T>(response: Response): Promise<T> {
  const text = await response.text();
  if (text.trim().toLowerCase().startsWith("<!doctype") || text.trim().toLowerCase().startsWith("<html")) {
    throw new Error("El servidor backend no está respondiendo en /api (comprueba que uvicorn esté corriendo en el puerto 8000).");
  }
  let payload: any = {};
  try {
    payload = JSON.parse(text);
  } catch {
    payload = { detail: text.slice(0, 200) };
  }
  if (!response.ok) {
    throw new Error(payload.detail || "KSPR API error " + response.status);
  }
  return payload;
}

function providerHeaders(auth?: ProviderAuth): Record<string, string> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (auth?.apiKey) headers["X-KSPR-API-Key"] = auth.apiKey;
  if (auth?.provider) headers["X-KSPR-Provider"] = auth.provider;
  if (auth?.baseUrl) headers["X-KSPR-Base-URL"] = auth.baseUrl;
  if (auth?.authMode) headers["X-KSPR-Auth-Mode"] = auth.authMode;
  return headers;
}

async function runAnalysisStream(payload: AnalysisRequest, auth: ProviderAuth | undefined, signal: AbortSignal | undefined, onProgress?: (progress: AnalysisProgress) => void, onToken?: (delta: string) => void): Promise<AnalysisResult | undefined> {
  const response = await fetch(API + "/api/v1/analyze/stream", {
    method: "POST",
    headers: providerHeaders(auth),
    signal,
    body: JSON.stringify(payload),
  });
  if (response.status === 404) return undefined;
  if (!response.ok) return parse<AnalysisResult>(response);
  if (!response.body) throw new Error("KSPR no abrió el canal de eventos de análisis.");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let result: AnalysisResult | undefined;
  const consume = (chunk: string) => {
    buffer += chunk;
    const events = buffer.split("\n\n");
    buffer = events.pop() || "";
    for (const event of events) {
      const data = event.split("\n").find((line) => line.startsWith("data: "))?.slice(6);
      if (!data) continue;
      const payloadEvent = JSON.parse(data) as { type: string; progress?: AnalysisProgress; result?: AnalysisResult; message?: string; text?: string };
      if (payloadEvent.type === "progress" && payloadEvent.progress) onProgress?.(payloadEvent.progress);
      if (payloadEvent.type === "delta" && payloadEvent.text) onToken?.(payloadEvent.text);
      if (payloadEvent.type === "error") throw new Error(payloadEvent.message || "KSPR no pudo completar el análisis");
      if (payloadEvent.type === "result" && payloadEvent.result) result = payloadEvent.result;
    }
  };
  while (!result) {
    const read = await reader.read();
    if (read.done) break;
    consume(decoder.decode(read.value, { stream: true }));
  }
  if (!result) throw new Error("El canal de eventos de KSPR terminó sin resultado.");
  return result;
}

export async function runAnalysis(payload: AnalysisRequest, auth?: ProviderAuth, signal?: AbortSignal, onProgress?: (progress: AnalysisProgress) => void, onToken?: (delta: string) => void): Promise<AnalysisResult> {
  const contextSize = payload.files.reduce((total, file) => total + file.content.length, 0);
  if (payload.mode !== "async" && contextSize <= 250_000) {
    const streamed = await runAnalysisStream(payload, auth, signal, onProgress, onToken);
    if (streamed) return streamed;
  }
  const headers = providerHeaders(auth);
  const response = await fetch(API + "/api/v1/analyze", {
    method: "POST",
    headers,
    signal,
    body: JSON.stringify(payload),
  });
  if (response.status !== 409) return parse<AnalysisResult>(response);

  const jobResponse = await fetch(API + "/api/v1/jobs", {
    method: "POST",
    headers,
    signal,
    body: JSON.stringify({ ...payload, mode: "async" }),
  });
  const job = await parse<{ job_id: string }>(jobResponse);
  onProgress?.({ status: "queued", progress: 0, stage: "queued", message: "Esperando ejecución" });
  const cancelJob = () => {
    void fetch(API + "/api/v1/jobs/" + job.job_id, { method: "DELETE", headers }).catch(() => undefined);
  };
  signal?.addEventListener("abort", cancelJob, { once: true });
  try {
    for (;;) {
      await new Promise((resolve) => setTimeout(resolve, 700));
      const status = await parse<AnalysisProgress & { result?: AnalysisResult; error?: string }>(
        await fetch(API + "/api/v1/jobs/" + job.job_id, { headers, signal }),
      );
      onProgress?.(status);
      if (status.status === "completed" && status.result) return status.result;
      if (status.status === "failed") throw new Error(status.error || "El job falló");
      if (status.status === "cancelled") throw new DOMException("Job cancelado", "AbortError");
    }
  } finally {
    signal?.removeEventListener("abort", cancelJob);
  }
}

export async function ingestArchive(file: File): Promise<SourceFile[]> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(API + "/api/v1/ingest/archive", { method: "POST", body: form });
  const payload = await parse<{ files: SourceFile[] }>(response);
  return payload.files;
}

export async function transcribeAudio(blob: Blob, auth?: ProviderAuth): Promise<string> {
  const form = new FormData();
  form.append("file", blob, "kspr-recording.webm");
  const headers = providerHeaders(auth);
  delete headers["Content-Type"];
  const response = await fetch(API + "/api/v1/transcribe", { method: "POST", headers, body: form });
  const payload = await parse<{ text: string }>(response);
  return payload.text;
}

export type GeminiModel = {
  id: string;
  name: string;
  description: string;
  input_token_limit?: number;
  output_token_limit?: number;
};

export async function checkProviderStatus(auth?: ProviderAuth): Promise<{ connected: boolean; provider: string; models: GeminiModel[]; message: string }> {
  const headers = providerHeaders(auth);
  const params = new URLSearchParams({ provider: auth?.provider || "gemini" });
  if (auth?.baseUrl) params.set("base_url", auth.baseUrl);
  const response = await fetch(API + "/api/v1/providers/status?" + params.toString(), { headers });
  return parse(response);
}

export const checkGeminiStatus = (apiKey?: string) => checkProviderStatus({ provider: "gemini", apiKey });
