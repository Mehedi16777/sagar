const API = process.env.NEXT_PUBLIC_API || "http://localhost:8000";
export const taka = (n: number) => "৳" + Math.round(n).toLocaleString("en-US");
export const DEST: Record<string, [string, string]> = { cxb: ["Cox’s Bazar", "🏖️"], sm: ["Saint Martin’s Island", "🏝️"], saj: ["Sajek Valley", "⛰️"], ban: ["Bandarban", "🌄"] };
export async function api<T = any>(path: string, o: { method?: string; body?: unknown; headers?: Record<string, string> } = {}): Promise<T> {
  const tok = typeof window !== "undefined" ? localStorage.getItem("tok") : null;
  const r = await fetch(API + path, {
    method: o.method || (o.body ? "POST" : "GET"),
    headers: { "Content-Type": "application/json", ...(tok ? { Authorization: `Bearer ${tok}` } : {}), ...(o.headers || {}) },
    body: o.body ? JSON.stringify(o.body) : undefined,
  });
  if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(typeof e.detail === "string" ? e.detail : r.statusText); }
  return r.json();
}
