export const ACCESS_TOKEN_KEY = "healthcore_access_token";

export function getStoredToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }

  return window.localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function storeToken(token: string): void {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(ACCESS_TOKEN_KEY, token);
}

export function clearStoredToken(): void {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
}

function getAuthBaseUrl() {
  return process.env.NEXT_PUBLIC_AUTH_API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
}

export class AuthApiError extends Error {
  status: number;
  fieldErrors: Record<string, string>;

  constructor(message: string, status: number, fieldErrors: Record<string, string> = {}) {
    super(message);
    this.name = "AuthApiError";
    this.status = status;
    this.fieldErrors = fieldErrors;
  }
}

function toFieldErrors(detail: unknown): Record<string, string> {
  if (!Array.isArray(detail)) {
    return {};
  }

  return detail.reduce<Record<string, string>>((acc, item) => {
    if (!item || typeof item !== "object") {
      return acc;
    }

    const loc = Array.isArray((item as { loc?: unknown }).loc)
      ? ((item as { loc?: string[] }).loc as string[])
      : [];
    const message = typeof (item as { msg?: unknown }).msg === "string"
      ? ((item as { msg: string }).msg)
      : "Invalid value.";

    const key = loc.length > 0 ? loc[loc.length - 1] : "form";
    acc[key] = message;
    return acc;
  }, {});
}

export async function authApiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${getAuthBaseUrl()}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init.headers ?? {}),
    },
    cache: "no-store",
  });

  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    const detail = payload && typeof payload === "object" ? (payload as { detail?: unknown }).detail : undefined;
    const message = typeof detail === "string" ? detail : `Request failed (${response.status})`;
    throw new AuthApiError(message, response.status, toFieldErrors(detail));
  }

  return payload as T;
}
