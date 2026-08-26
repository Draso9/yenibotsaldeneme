const defaultApiUrl = "https://izfin-api-469145462773.europe-west1.run.app";

export const DEFAULT_API_TIMEOUT_MS = 20_000;

type AuthRecoveryHandlers = {
  refreshToken: () => Promise<string | null>;
  onSessionExpired?: () => Promise<void> | void;
};

let authRecoveryHandlers: AuthRecoveryHandlers | null = null;

export function configureAuthRecovery(handlers: AuthRecoveryHandlers | null): void {
  authRecoveryHandlers = handlers;
}

async function refreshAuthToken(): Promise<string | null> {
  return authRecoveryHandlers?.refreshToken() ?? null;
}

export class IzfinApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
    this.name = "IzfinApiError";
  }
}

export function isRetryableApiError(error: unknown): error is IzfinApiError {
  return error instanceof IzfinApiError && [408, 429, 502, 503, 504].includes(error.status);
}

function apiBaseUrl(): string {
  return (process.env.NEXT_PUBLIC_IZFIN_API_URL ?? defaultApiUrl).replace(/\/$/, "");
}

function timeoutSignal(init: RequestInit, enabled: boolean): AbortSignal | undefined {
  if (init.signal) return init.signal;
  return enabled ? AbortSignal.timeout(DEFAULT_API_TIMEOUT_MS) : undefined;
}

function normalizeFetchFailure(error: unknown): never {
  if (error instanceof DOMException && (error.name === "AbortError" || error.name === "TimeoutError")) {
    throw new IzfinApiError("İstek zaman aşımına uğradı. Lütfen tekrar deneyin.", 408);
  }
  throw new IzfinApiError("Servise geçici olarak ulaşılamıyor. Lütfen tekrar deneyin.", 503);
}

async function fetchWithBoundary(url: string, init: RequestInit, useTimeout = true): Promise<Response> {
  try {
    return await fetch(url, { ...init, signal: timeoutSignal(init, useTimeout) });
  } catch (error) {
    normalizeFetchFailure(error);
  }
}

async function readApiResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    if (response.status === 401) {
      throw new IzfinApiError("Oturum doğrulanamadı. Lütfen yeniden giriş yapın.", 401);
    }
    if (response.status === 403) {
      throw new IzfinApiError("Bu işlem için yetkin bulunmuyor.", 403);
    }
    if ([502, 503, 504].includes(response.status)) {
      throw new IzfinApiError("Servis geçici olarak kullanılamıyor. Lütfen tekrar deneyin.", response.status);
    }
    throw new IzfinApiError(payload?.error?.message ?? payload?.detail ?? "API isteği tamamlanamadı.", response.status);
  }
  return response.json() as Promise<T>;
}

async function authenticatedFetch(
  path: string,
  idToken: string,
  init: RequestInit,
  accept: string,
  useTimeout: boolean,
): Promise<Response> {
  const send = (token: string) => fetchWithBoundary(`${apiBaseUrl()}${path}`, {
    ...init,
    headers: { Accept: accept, Authorization: `Bearer ${token}`, ...init.headers },
  }, useTimeout);

  let response = await send(idToken);
  if (response.status !== 401) return response;

  const freshToken = await refreshAuthToken();
  if (freshToken) response = await send(freshToken);
  if (response.status === 401) await authRecoveryHandlers?.onSessionExpired?.();
  return response;
}

export async function izfinPublicApiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetchWithBoundary(`${apiBaseUrl()}${path}`, {
    ...init,
    headers: { Accept: "application/json", ...init.headers },
  });
  return readApiResponse<T>(response);
}

export async function izfinApiFetch<T>(path: string, idToken: string, init: RequestInit = {}): Promise<T> {
  const response = await authenticatedFetch(path, idToken, init, "application/json", true);
  return readApiResponse<T>(response);
}

export async function izfinApiStream<T>(
  path: string,
  idToken: string,
  init: RequestInit,
  onEvent: (value: T) => void,
): Promise<T> {
  const response = await authenticatedFetch(path, idToken, init, "application/x-ndjson", false);
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