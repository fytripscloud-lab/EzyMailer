const TOKEN_KEY = "eazyvalidator_auth_token";

/**
 * Normally opened from EzyMailer's desktop app with the user's existing JWT
 * in the URL (?token=...) - no separate login needed. This reads it once,
 * persists it for the tab's lifetime, and scrubs it from the visible
 * URL/history so it doesn't linger in the address bar. If the page is opened
 * directly (no token), the login form (see LoginForm.tsx) gets one the same
 * way the desktop app itself does - by calling EzyMailer's /api/login.
 */
export function initAuthToken(): string | null {
  if (typeof window === "undefined") return null;

  const params = new URLSearchParams(window.location.search);
  const fromUrl = params.get("token");
  if (fromUrl) {
    window.sessionStorage.setItem(TOKEN_KEY, fromUrl);
    params.delete("token");
    const rest = params.toString();
    const cleanUrl = window.location.pathname + (rest ? `?${rest}` : "") + window.location.hash;
    window.history.replaceState({}, "", cleanUrl);
    return fromUrl;
  }

  return window.sessionStorage.getItem(TOKEN_KEY);
}

export function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.sessionStorage.getItem(TOKEN_KEY);
}

export function setAuthToken(token: string): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem(TOKEN_KEY, token);
}

export function clearAuthToken(): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.removeItem(TOKEN_KEY);
}

export const UNAUTHORIZED_EVENT = "eazyvalidator:unauthorized";

export function notifyUnauthorized(): void {
  if (typeof window === "undefined") return;
  clearAuthToken();
  window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * This backend only ever runs bundled inside EzyMailer's own desktop
 * process (see ensure_validator_server() in main.py), so if its user is
 * already signed in there, /api/v1/session/local hands out a token without
 * making them sign in a second time - this is what makes a direct open
 * (no ?token= from the "Mail Validator" button) skip the login form too.
 */
export async function tryLocalAutoLogin(): Promise<string | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/session/local`);
    if (!res.ok) return null;
    const data = await res.json().catch(() => ({}));
    return typeof data?.token === "string" && data.token ? data.token : null;
  } catch {
    return null;
  }
}
