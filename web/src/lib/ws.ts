import { API_BASE } from "./api";
export function wsUrl(path: string) {
  const u = new URL(API_BASE);
  u.protocol = u.protocol.replace("http", "ws");
  u.pathname = path.startsWith("/") ? path : `/${path}`;
  return u.toString();
}