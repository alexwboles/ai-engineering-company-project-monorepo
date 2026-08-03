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
  return process.env.NEXT_PUBLIC_AUTH_API_URL || process.env.NEXT_PUBLIC_API_URL || "http://api:8000";
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
    const message =
      typeof (item as { msg?: unknown }).msg === "string"
        ? (item as { msg: string }).msg
        : "Invalid value.";

    const key = loc.length > 0 ? loc[loc.length - 1] : "form";
    acc[key] = message;
    return acc;
  }, {});
}

function isSafeUserMessage(detail: string): boolean {
  const trimmed = detail.trim();
  if (!trimmed || trimmed.length > 200) {
    return false;
  }
  if (/traceback|exception|stack|at\s+\w+\.|File "|line \d+/i.test(trimmed)) {
    return false;
  }
  if (/^\s*\{[\s\S]*\}\s*$/.test(trimmed) || /unexpected token/i.test(trimmed)) {
    return false;
  }
  return true;
}

function toUserFacingAuthMessage(status: number, detail?: unknown): string {
  if (typeof detail === "string" && isSafeUserMessage(detail)) {
    return detail;
  }

  if (status === 400 || status === 422) {
    return "Please check your input and try again.";
  }
  if (status === 401) {
    return "Invalid email or password.";
  }
  if (status === 409) {
    return "An account with this email already exists.";
  }
  if (status >= 500) {
    return "Something went wrong on our side. Please try again in a moment.";
  }

  return "Unable to complete the request. Please try again.";
}

export async function authApiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${getAuthBaseUrl()}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init.headers ?? {}),
      },
      cache: "no-store",
    });
  } catch {
    throw new AuthApiError("Unable to reach the server. Check your connection and try again.", 0);
  }

  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    const detail =
      payload && typeof payload === "object" ? (payload as { detail?: unknown }).detail : undefined;
    throw new AuthApiError(toUserFacingAuthMessage(response.status, detail), response.status, toFieldErrors(detail));
  }

  if (payload === null) {
    throw new AuthApiError("Received an unexpected response from the server. Please try again.", response.status);
  }

  return payload as T;
}
