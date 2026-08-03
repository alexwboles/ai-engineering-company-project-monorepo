import { clearStoredToken, getStoredToken } from "@/lib/auth-client";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://api:8000";

export class ApiError extends Error {
  status: number;
  fieldErrors: Record<string, string>;

  constructor(message: string, status: number, fieldErrors: Record<string, string> = {}) {
    super(message);
    this.name = "ApiError";
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

export function toUserFacingApiMessage(status: number, detail?: unknown, fallback?: string): string {
  if (typeof detail === "string" && isSafeUserMessage(detail)) {
    return detail;
  }

  if (status === 400 || status === 422) {
    return fallback ?? "Please check your input and try again.";
  }
  if (status === 401) {
    return "Invalid credentials. Please sign in again.";
  }
  if (status === 403) {
    return "You do not have permission to perform this action.";
  }
  if (status === 404) {
    return "The requested resource was not found.";
  }
  if (status === 409) {
    return "This record already exists. Please use different details.";
  }
  if (status >= 500) {
    return "Something went wrong on our side. Please try again in a moment.";
  }

  return fallback ?? "Unable to complete the request. Please try again.";
}

function buildHeaders(authRequired: boolean, headers?: HeadersInit): Headers {
  const merged = new Headers(headers ?? {});

  if (!merged.has("Content-Type")) {
    merged.set("Content-Type", "application/json");
  }

  if (authRequired) {
    const token = getStoredToken();
    if (!token) {
      clearStoredToken();
      if (typeof window !== "undefined") {
        window.location.assign("/login");
      }
      throw new ApiError("No active session. Please log in.", 401);
    }

    merged.set("Authorization", `Bearer ${token}`);
  }

  return merged;
}

export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
  options: { authRequired?: boolean } = {}
): Promise<T> {
  const authRequired = options.authRequired ?? true;

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: buildHeaders(authRequired, init.headers),
      cache: "no-store",
    });
  } catch {
    throw new ApiError("Unable to reach the server. Check your connection and try again.", 0);
  }

  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    if (response.status === 401) {
      clearStoredToken();
      if (typeof window !== "undefined" && authRequired) {
        window.location.assign("/login");
      }
    }

    const detail =
      payload && typeof payload === "object" ? (payload as { detail?: unknown }).detail : undefined;
    const message = toUserFacingApiMessage(response.status, detail);
    const fieldErrors = toFieldErrors(detail);

    throw new ApiError(message, response.status, fieldErrors);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  if (payload === null) {
    throw new ApiError("Received an unexpected response from the server. Please try again.", response.status);
  }

  return payload as T;
}
