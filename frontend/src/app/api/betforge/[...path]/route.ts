import { NextRequest, NextResponse } from 'next/server';
import { API_BASE } from '@/lib/api';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

/** BFF proxy: forwards /api/betforge/<...> to the FastAPI backend (no CORS). */
export async function GET(_req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const { path } = await params;
  return proxy('GET', path);
}

export async function POST(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const { path } = await params;
  const body = await req.json().catch(() => ({}));
  return proxy('POST', path, body);
}

async function proxy(method: string, path: string[], body?: unknown) {
  const url = `${API_BASE}/api/${path.join('/')}`;
  try {
    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: body !== undefined ? JSON.stringify(body) : undefined,
      cache: 'no-store',
    });
    const text = await res.text();
    const data = text ? JSON.parse(text) : {};
    return NextResponse.json(data, { status: res.status });
  } catch (e) {
    return NextResponse.json({ error: `backend unreachable (${url})`, detail: String(e) }, { status: 502 });
  }
}
