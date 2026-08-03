import { clearStoredToken, getStoredToken } from "@/lib/auth-client";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function getBaseUrl() {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://api:8000";

  return baseUrl;
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

  if (Array.isArray(detail) && detail[0] && typeof detail[0] === "object") {
    const msg = (detail[0] as { msg?: unknown }).msg;
    if (typeof msg === "string" && isSafeUserMessage(msg)) {
      return msg;
    }
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
  if (status >= 500) {
    return "Something went wrong on our side. Please try again in a moment.";
  }

  return fallback ?? "Unable to complete the request. Please try again.";
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers ?? {});
  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const token = getStoredToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  let response: Response;
  try {
    response = await fetch(`${getBaseUrl()}${path}`, {
      ...init,
      headers,
      cache: "no-store",
    });
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError("Unable to reach the server. Check your connection and try again.", 0);
  }

  if (!response.ok) {
    if (response.status === 401) {
      clearStoredToken();
      if (typeof window !== "undefined") {
        window.location.assign("/login");
      }
    }

    let detail: unknown;
    try {
      const data = await response.json();
      detail = data?.detail;
    } catch {
      detail = undefined;
    }

    throw new ApiError(toUserFacingApiMessage(response.status, detail), response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  try {
    return (await response.json()) as T;
  } catch {
    throw new ApiError("Received an unexpected response from the server. Please try again.", response.status);
  }
}
