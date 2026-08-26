const defaultApiUrl = "https://izfin-api-469145462773.europe-west1.run.app";

export class IzfinApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
    this.name = "IzfinApiError";
  }
}

function apiBaseUrl(): string {
  return (process.env.NEXT_PUBLIC_IZFIN_API_URL ?? defaultApiUrl).replace(/\/$/, "");
}

async function readApiResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new IzfinApiError(payload?.error?.message ?? payload?.detail ?? "API isteği tamamlanamadı.", response.status);
  }
  return response.json() as Promise<T>;
}

export async function izfinPublicApiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${apiBaseUrl()}${path}`, {
    ...init,
    headers: { Accept: "application/json", ...init.headers },
  });
  return readApiResponse<T>(response);
}

export async function izfinApiFetch<T>(path: string, idToken: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${apiBaseUrl()}${path}`, {
    ...init,
    headers: { Accept: "application/json", Authorization: `Bearer ${idToken}`, ...init.headers },
  });
  return readApiResponse<T>(response);
}

export async function izfinApiStream<T>(
  path: string,
  idToken: string,
  init: RequestInit,
  onEvent: (value: T) => void,
): Promise<T> {
  const response = await fetch(`${apiBaseUrl()}${path}`, {
    ...init,
    headers: { Accept: "application/x-ndjson", Authorization: `Bearer ${idToken}`, ...init.headers },
  });
  if (!response.ok) return readApiResponse<T>(response);
  if (!response.body) throw new IzfinApiError("Canlı tarama akışı başlatılamadı.", response.status);

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let latest: T | null = null;
  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (!line.trim()) continue;
      latest = JSON.parse(line) as T;
      onEvent(latest);
    }
    if (done) break;
  }
  if (buffer.trim()) {
    latest = JSON.parse(buffer) as T;
    onEvent(latest);
  }
  if (!latest) throw new IzfinApiError("Tarama akışı sonuç üretmeden kapandı.", response.status);
  return latest;
}
