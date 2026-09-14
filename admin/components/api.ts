export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8004/api/v1";
const ACCESS_KEY = "scosmetics_staff_access";
const REFRESH_KEY = "scosmetics_staff_refresh";

export type Tokens = { access_token: string; refresh_token: string };

export function saveTokens(tokens: Tokens) {
  sessionStorage.setItem(ACCESS_KEY, tokens.access_token);
  sessionStorage.setItem(REFRESH_KEY, tokens.refresh_token);
}

export function clearTokens() {
  sessionStorage.removeItem(ACCESS_KEY);
  sessionStorage.removeItem(REFRESH_KEY);
}

export function hasTokens() { return Boolean(sessionStorage.getItem(ACCESS_KEY)); }

let refreshInFlight: Promise<string | null> | null = null;
async function refreshToken(): Promise<string | null> {
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      const refresh = sessionStorage.getItem(REFRESH_KEY);
      if (!refresh) return null;
      const response = await fetch(`${API_BASE}/auth/refresh`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refresh }),
      });
      if (!response.ok) { clearTokens(); return null; }
      const tokens = (await response.json()) as Tokens;
      saveTokens(tokens);
      return tokens.access_token;
    })().finally(() => { refreshInFlight = null; });
  }
  return refreshInFlight;
}

async function send(path: string, options: RequestInit, token?: string | null) {
  const headers = new Headers(options.headers);
  if (options.body) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  return fetch(`${API_BASE}${path}`, { ...options, headers, cache: "no-store" });
}

export async function request(path: string, options: RequestInit = {}, protectedRoute = true): Promise<Response> {
  let token = protectedRoute ? sessionStorage.getItem(ACCESS_KEY) : null;
  if (protectedRoute && !token) throw new Error("יש להתחבר תחילה.");
  let response = await send(path, options, token);
  if (protectedRoute && response.status === 401) {
    const latest = sessionStorage.getItem(ACCESS_KEY);
    token = latest && latest !== token ? latest : await refreshToken();
    if (token) response = await send(path, options, token);
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(typeof body.detail === "string" ? body.detail : `שגיאה ${response.status}`);
  }
  return response;
}

export async function api<T>(path: string, options: RequestInit = {}, protectedRoute = true): Promise<T> {
  return (await request(path, options, protectedRoute)).json() as Promise<T>;
}
