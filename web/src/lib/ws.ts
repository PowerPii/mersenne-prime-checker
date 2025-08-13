export function wsUrl(path: string) {
  const api = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";
  const u = new URL(path, api);
  u.protocol = u.protocol.replace("http", "ws");
  return u.toString();
}
