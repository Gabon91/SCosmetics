export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8004/api/v1";

const ACCESS_KEY = "scosmetics_demo_access";
const REFRESH_KEY = "scosmetics_demo_refresh";
let refreshInFlight: Promise<string | null> | null = null;

export type TokenPair = { access_token: string; refresh_token: string };

export function saveTokens(tokens: TokenPair) {
  sessionStorage.setItem(ACCESS_KEY, tokens.access_token);
  sessionStorage.setItem(REFRESH_KEY, tokens.refresh_token);
}

export function clearTokens() {
  sessionStorage.removeItem(ACCESS_KEY);
  sessionStorage.removeItem(REFRESH_KEY);
}

export function hasSession() {
  return Boolean(sessionStorage.getItem(ACCESS_KEY));
}

function refreshAccessToken(): Promise<string | null> {
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      const refreshToken = sessionStorage.getItem(REFRESH_KEY);
      if (!refreshToken) return null;
      const response = await fetch(`${API_BASE}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!response.ok) {
        clearTokens();
        return null;
      }
      const tokens = (await response.json()) as TokenPair;
      saveTokens(tokens);
      return tokens.access_token;
    })().finally(() => { refreshInFlight = null; });
  }
  return refreshInFlight;
}

function errorText(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((item) => item.msg).join("; ");
  return "הבקשה נכשלה. נסי שוב.";
}

export async function api<T>(
  path: string,
  options: RequestInit = {},
  authenticated = false,
): Promise<T> {
  const send = (accessToken?: string | null) => {
    const headers = new Headers(options.headers);
    if (options.body) headers.set("Content-Type", "application/json");
    if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
    return fetch(`${API_BASE}${path}`, {
      ...options,
      headers,
      cache: "no-store",
    });
  };

  let accessToken = authenticated ? sessionStorage.getItem(ACCESS_KEY) : null;
  if (authenticated && !accessToken) throw new Error("יש להתחבר תחילה.");
  let response = await send(accessToken);

  if (authenticated && response.status === 401) {
    const latestToken = sessionStorage.getItem(ACCESS_KEY);
    accessToken = latestToken && latestToken !== accessToken
      ? latestToken
      : await refreshAccessToken();
    if (accessToken) response = await send(accessToken);
  }

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(errorText(body.detail));
  }
  return (await response.json()) as T;
}
