import { clearStoredToken, getStoredToken } from "@/lib/auth-client";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

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
    const message = typeof (item as { msg?: unknown }).msg === "string"
      ? ((item as { msg: string }).msg)
      : "Invalid value.";

    const key = loc.length > 0 ? loc[loc.length - 1] : "form";
    acc[key] = message;
    return acc;
  }, {});
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
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: buildHeaders(authRequired, init.headers),
    cache: "no-store",
  });

  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    if (response.status === 401) {
      clearStoredToken();
      if (typeof window !== "undefined") {
        window.location.assign("/login");
      }
    }

    const detail = payload && typeof payload === "object" ? (payload as { detail?: unknown }).detail : undefined;
    const message = typeof detail === "string" ? detail : `Request failed (${response.status})`;
    const fieldErrors = toFieldErrors(detail);

    throw new ApiError(message, response.status, fieldErrors);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return payload as T;
}
