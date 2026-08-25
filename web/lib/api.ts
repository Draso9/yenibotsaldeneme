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

export async function izfinApiFetch<T>(path: string, idToken: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${apiBaseUrl()}${path}`, {
    ...init,
    headers: { Accept: "application/json", Authorization: `Bearer ${idToken}`, ...init.headers },
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new IzfinApiError(payload?.error?.message ?? payload?.detail ?? "API isteği tamamlanamadı.", response.status);
  }
  return response.json() as Promise<T>;
}
