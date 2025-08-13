export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

export async function apiFetch<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const url = `${API_BASE}${path}`;

  // Only set content-type when we have a body to send
  const hasBody = init?.body != null;
  const headers = {
    ...(hasBody ? { "content-type": "application/json" } : {}),
    ...(init?.headers || {}),
  };

  const res = await fetch(url, {
    ...init,
    headers,
    cache: "no-store",
    mode: "cors",
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status} ${res.statusText} – ${url}\n${text}`);
  }

  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return (await res.json()) as T;
  return (await res.text()) as unknown as T;
}
