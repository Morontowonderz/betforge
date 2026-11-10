export const API_BASE = process.env.BETFORGE_API_URL || 'http://127.0.0.1:8000';

/** Server-side fetch of the FastAPI backend directly (no CORS server→server). */
export async function bfServer<T = unknown>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}/api/${path}`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`betforge backend /api/${path} -> HTTP ${res.status}`);
  return (await res.json()) as T;
}

/** Client-side fetch through the Next BFF proxy (avoids CORS). */
export async function bf<T = unknown>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api/betforge/${path}`, init);
  if (!res.ok) throw new Error(`betforge API ${path} -> HTTP ${res.status}`);
  return (await res.json()) as T;
}
