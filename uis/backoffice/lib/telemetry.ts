"use client";

import { getStoredToken } from "@/lib/auth-client";

const TELEMETRY_ENDPOINT =
  process.env.NEXT_PUBLIC_TELEMETRY_ENDPOINT ?? "http://localhost:8000/telemetry/events";
const TELEMETRY_SCHEMA_VERSION = "1.0.0";
const TELEMETRY_SESSION_KEY = "healthcore_telemetry_session_id";
const TELEMETRY_STARTED_KEY = "healthcore_telemetry_started_at";
const TELEMETRY_QUEUE_LIMIT = 20;
const TELEMETRY_FLUSH_INTERVAL_MS = 10_000;
const TELEMETRY_NAVIGATION_SUPPRESSION_MS = 30_000;
const TELEMETRY_ERROR_DEDUP_MS = 5 * 60 * 1000;
const TELEMETRY_API_LATENCY_WINDOW_MS = 60_000;
const TELEMETRY_API_LATENCY_DRAIN_MS = 10_000;

const TELEMETRY_PROPERTY_ALLOWLISTS = {
  claim_submitted: ["claimId", "locationId", "payerId", "payerName", "serviceType", "claimAmount", "resubmitted", "submissionChannel"],
  claim_denied: ["claimId", "locationId", "payerId", "denialReason", "resubmitted", "claimAmount", "daysSinceSubmission", "appealEligible"],
  claim_validation_failed: ["claimId", "locationId", "validationErrors", "invalidFields", "source", "severity"],
  appointment_scheduled: ["appointmentId", "locationId", "serviceType", "scheduledDate", "scheduledTime", "channel", "leadTimeHours"],
  appointment_no_show_marked: ["appointmentId", "locationId", "serviceType", "noShowReasonCode", "reminderCount", "rescheduled"],
  appointment_completed: ["appointmentId", "locationId", "serviceType", "visitDurationMinutes", "confirmedAtDeltaMinutes", "staffedByRole"],
  clinician_cme_logged: ["clinicianId", "role", "cmeHoursLogged", "cmeHoursRequired", "source", "cycleYear"],
  clinician_compliance_calculated: ["clinicianId", "role", "cmeHoursLogged", "cmeHoursRequired", "complianceStatus", "hoursRemaining", "daysUntilLicenceExpiry"],
  billing_denial_rate_calculated: ["payerId", "payerName", "locationId", "periodStart", "periodEnd", "totalClaims", "deniedClaims", "denialRate"],
  no_show_impact_calculated: ["locationId", "periodStart", "periodEnd", "scheduledAppointments", "noShowCount", "noShowRate", "estimatedLostRevenue"],
  auth_login_attempted: ["authMethod", "clientApp", "userRole", "authProvider", "mfaUsed"],
  auth_login_failed: ["authMethod", "clientApp", "userRole", "failureReason", "lockoutTriggered", "attemptCount"],
  auth_session_expired: ["sessionAgeMinutes", "authMethod", "clientApp", "expiryReason"],
  navigation_section_opened: ["sectionName", "route", "previousRoute", "userRole", "entryPoint"],
  workflow_abandoned: ["flowName", "stepName", "lastCompletedStep", "timeSinceStartSeconds", "exitRoute", "userRole"],
  api_latency_recorded: ["route", "method", "statusCode", "durationMs", "domain", "requestSizeBytes", "responseSizeBytes"],
  frontend_error_occurred: ["pageRoute", "componentName", "errorClass", "errorFingerprint", "recoverable", "actionTaken"],
  backend_unhandled_exception: ["route", "exceptionClass", "errorFingerprint", "requestMethod", "statusCode", "workerId"],
  supplier_rate_updated: ["supplierId", "previousRate", "newRate", "country", "category", "updatedByRole"],
  incident_status_changed: ["incidentId", "previousStatus", "nextStatus", "origin", "category", "actorRole", "timeInPreviousStatusHours"],
} as const;

type TelemetryEventType = keyof typeof TELEMETRY_PROPERTY_ALLOWLISTS;
type TelemetryProperties = Record<string, unknown>;

type TelemetryEnvelope = {
  eventId: string;
  timestamp: string;
  sessionId: string;
  userId: string | null;
  event_type: TelemetryEventType;
  schemaVersion: string;
  requestId: string;
  properties: TelemetryProperties;
};

type PendingApiLatency = {
  route: string;
  method: string;
  statusCode: number;
  domain?: string;
  windowStart: number;
  count: number;
  durationTotal: number;
  requestSizeTotal: number;
  responseSizeTotal: number;
};

type TelemetryBatch = {
  events: TelemetryEnvelope[];
};

function isBrowser(): boolean {
  return typeof window !== "undefined";
}

function nowIso(): string {
  return new Date().toISOString();
}

function randomId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }

  return `telemetry-${Math.random().toString(36).slice(2)}-${Date.now()}`;
}

function safeNumber(value: unknown): number | undefined {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }

  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }

  return undefined;
}

function getSessionId(): string {
  if (!isBrowser()) {
    return "server-session";
  }

  const existing = window.sessionStorage.getItem(TELEMETRY_SESSION_KEY);
  if (existing) {
    return existing;
  }

  const sessionId = randomId();
  window.sessionStorage.setItem(TELEMETRY_SESSION_KEY, sessionId);
  window.sessionStorage.setItem(TELEMETRY_STARTED_KEY, new Date().toISOString());
  return sessionId;
}

function getSessionAgeMinutes(): number | undefined {
  if (!isBrowser()) {
    return undefined;
  }

  const startedAt = window.sessionStorage.getItem(TELEMETRY_STARTED_KEY);
  if (!startedAt) {
    return undefined;
  }

  const started = new Date(startedAt).getTime();
  const elapsed = Date.now() - started;
  if (!Number.isFinite(elapsed) || elapsed < 0) {
    return undefined;
  }

  return Number((elapsed / 60000).toFixed(2));
}

function decodeBase64Url(value: string): string {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
  const padding = "=".repeat((4 - (normalized.length % 4)) % 4);
  return atob(`${normalized}${padding}`);
}

function getTokenClaims(): Record<string, unknown> | null {
  if (!isBrowser()) {
    return null;
  }

  const token = getStoredToken();
  if (!token) {
    return null;
  }

  const parts = token.split(".");
  if (parts.length < 2) {
    return null;
  }

  try {
    return JSON.parse(decodeBase64Url(parts[1])) as Record<string, unknown>;
  } catch {
    return null;
  }
}

function getUserId(): string | null {
  const claims = getTokenClaims();
  const subject = claims?.sub;
  if (typeof subject === "string" && subject.trim()) {
    return subject;
  }

  if (typeof subject === "number" && Number.isFinite(subject)) {
    return String(subject);
  }

  return null;
}

function getUserRole(): string | undefined {
  const claims = getTokenClaims();
  const role = claims?.role;
  return typeof role === "string" && role.trim() ? role : undefined;
}

function normalizeProperties(eventType: TelemetryEventType, properties: TelemetryProperties): TelemetryProperties {
  const allowlist = new Set<string>(TELEMETRY_PROPERTY_ALLOWLISTS[eventType]);
  const normalized: TelemetryProperties = {};

  for (const [key, value] of Object.entries(properties)) {
    if (allowlist.has(key) && value !== undefined) {
      normalized[key] = value;
    }
  }

  return normalized;
}

function getNavigationSection(pathname: string): string {
  if (pathname === "/") {
    return "operations";
  }
  if (pathname.startsWith("/suppliers")) {
    return "suppliers";
  }
  if (pathname.startsWith("/incidents")) {
    return "incidents";
  }
  if (pathname.startsWith("/account/profile")) {
    return "profile";
  }
  if (pathname.startsWith("/account/change-password")) {
    return "change_password";
  }
  if (pathname === "/login") {
    return "login";
  }
  if (pathname === "/register") {
    return "register";
  }
  if (pathname === "/forgot-password") {
    return "forgot_password";
  }
  if (pathname === "/reset-password") {
    return "reset_password";
  }

  return pathname.replace(/^\//, "").replaceAll("/", "_") || "unknown";
}

function getErrorFingerprint(errorClass: string, message: string): string {
  const normalizedMessage = message.replace(/\s+/g, " ").trim().slice(0, 120);
  return `${errorClass}:${normalizedMessage}`.toLowerCase();
}

function getRouteDomain(route: string): string {
  if (route.startsWith("/auth")) {
    return "auth";
  }
  if (route.startsWith("/suppliers")) {
    return "procurement";
  }
  if (route.startsWith("/api/incidents") || route.startsWith("/incidents")) {
    return "incidents";
  }
  if (route.startsWith("/profiles")) {
    return "accounts";
  }
  return "operations";
}

function toJsonBatch(events: TelemetryEnvelope[]): TelemetryBatch {
  return { events };
}

class TelemetryService {
  private queue: TelemetryEnvelope[] = [];

  private started = false;

  private flushTimer: number | null = null;

  private lastNavigationEmission = new Map<string, number>();

  private lastErrorEmission = new Map<string, number>();

  private apiLatencyBuckets = new Map<string, PendingApiLatency>();

  start(): void {
    if (!isBrowser() || this.started) {
      return;
    }

    this.started = true;
    window.addEventListener("pagehide", this.handlePageHide);
    window.addEventListener("visibilitychange", this.handleVisibilityChange);
    window.addEventListener("error", this.handleWindowError);
    window.addEventListener("unhandledrejection", this.handleUnhandledRejection);

    this.flushTimer = window.setInterval(() => {
      void this.flush();
    }, TELEMETRY_FLUSH_INTERVAL_MS);
  }

  stop(): void {
    if (!isBrowser() || !this.started) {
      return;
    }

    this.started = false;
    window.removeEventListener("pagehide", this.handlePageHide);
    window.removeEventListener("visibilitychange", this.handleVisibilityChange);
    window.removeEventListener("error", this.handleWindowError);
    window.removeEventListener("unhandledrejection", this.handleUnhandledRejection);

    if (this.flushTimer !== null) {
      window.clearInterval(this.flushTimer);
      this.flushTimer = null;
    }
  }

  track(eventType: TelemetryEventType, properties: TelemetryProperties = {}): void {
    const normalizedProperties = normalizeProperties(eventType, properties);

    if (eventType === "navigation_section_opened") {
      const sectionName = String(normalizedProperties.sectionName ?? "");
      const route = String(normalizedProperties.route ?? "");
      const cacheKey = `${sectionName}|${route}`;
      const lastSeen = this.lastNavigationEmission.get(cacheKey) ?? 0;
      const now = Date.now();
      if (now - lastSeen < TELEMETRY_NAVIGATION_SUPPRESSION_MS) {
        return;
      }

      this.lastNavigationEmission.set(cacheKey, now);
      this.enqueue(eventType, normalizedProperties);
      return;
    }

    if (eventType === "frontend_error_occurred" || eventType === "backend_unhandled_exception") {
      const fingerprint = String(normalizedProperties.errorFingerprint ?? "");
      const cacheKey = `${eventType}|${fingerprint}`;
      const lastSeen = this.lastErrorEmission.get(cacheKey) ?? 0;
      const now = Date.now();
      if (now - lastSeen < TELEMETRY_ERROR_DEDUP_MS) {
        return;
      }

      this.lastErrorEmission.set(cacheKey, now);
      this.enqueue(eventType, normalizedProperties);
      return;
    }

    if (eventType === "api_latency_recorded") {
      this.recordApiLatency(normalizedProperties);
      return;
    }

    this.enqueue(eventType, normalizedProperties);
  }

  private recordApiLatency(properties: TelemetryProperties): void {
    const route = String(properties.route ?? "").trim();
    const method = String(properties.method ?? "GET").trim().toUpperCase() || "GET";
    const statusCode = Number(properties.statusCode ?? 0);
    const domain = typeof properties.domain === "string" ? properties.domain : getRouteDomain(route);
    const durationMs = safeNumber(properties.durationMs) ?? 0;
    const requestSizeBytes = safeNumber(properties.requestSizeBytes) ?? 0;
    const responseSizeBytes = safeNumber(properties.responseSizeBytes) ?? 0;

    if (!route) {
      return;
    }

    const windowStart = Math.floor(Date.now() / TELEMETRY_API_LATENCY_WINDOW_MS) * TELEMETRY_API_LATENCY_WINDOW_MS;
    const key = `${route}|${method}|${statusCode}|${windowStart}`;
    const current = this.apiLatencyBuckets.get(key);

    if (current) {
      current.count += 1;
      current.durationTotal += durationMs;
      current.requestSizeTotal += requestSizeBytes;
      current.responseSizeTotal += responseSizeBytes;
      current.domain = domain;
      return;
    }

    this.apiLatencyBuckets.set(key, {
      route,
      method,
      statusCode,
      domain,
      windowStart,
      count: 1,
      durationTotal: durationMs,
      requestSizeTotal: requestSizeBytes,
      responseSizeTotal: responseSizeBytes,
    });
  }

  private drainApiLatencyBuckets(force: boolean): void {
    const now = Date.now();

    for (const [key, bucket] of this.apiLatencyBuckets.entries()) {
      const bucketAge = now - bucket.windowStart;
      if (!force && bucketAge < TELEMETRY_API_LATENCY_WINDOW_MS + TELEMETRY_API_LATENCY_DRAIN_MS) {
        continue;
      }

      const count = Math.max(bucket.count, 1);
      this.queue.push(
        this.buildEnvelope("api_latency_recorded", {
          route: bucket.route,
          method: bucket.method,
          statusCode: bucket.statusCode,
          domain: bucket.domain,
          durationMs: Number((bucket.durationTotal / count).toFixed(2)),
          requestSizeBytes: Number((bucket.requestSizeTotal / count).toFixed(2)),
          responseSizeBytes: Number((bucket.responseSizeTotal / count).toFixed(2)),
        })
      );

      this.apiLatencyBuckets.delete(key);
    }
  }

  private enqueue(eventType: TelemetryEventType, properties: TelemetryProperties): void {
    this.queue.push(this.buildEnvelope(eventType, properties));

    if (this.queue.length >= TELEMETRY_QUEUE_LIMIT) {
      void this.flush();
    }
  }

  private buildEnvelope(eventType: TelemetryEventType, properties: TelemetryProperties): TelemetryEnvelope {
    return {
      eventId: randomId(),
      timestamp: nowIso(),
      sessionId: getSessionId(),
      userId: getUserId(),
      event_type: eventType,
      schemaVersion: TELEMETRY_SCHEMA_VERSION,
      requestId: randomId(),
      properties: normalizeProperties(eventType, properties),
    };
  }

  private async flush(options: { useBeacon?: boolean; force?: boolean } = {}): Promise<void> {
    if (!isBrowser()) {
      return;
    }

    const force = options.force ?? false;
    this.drainApiLatencyBuckets(force);

    if (this.queue.length === 0) {
      return;
    }

    const batch = this.queue.splice(0, this.queue.length);
    const payload = JSON.stringify(toJsonBatch(batch));

    if (options.useBeacon && navigator.sendBeacon) {
      const sent = navigator.sendBeacon(TELEMETRY_ENDPOINT, new Blob([payload], { type: "application/json" }));
      if (sent) {
        return;
      }
    }

    for (let attempt = 1; attempt <= 3; attempt += 1) {
      try {
        const response = await fetch(TELEMETRY_ENDPOINT, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: payload,
          keepalive: options.useBeacon ?? false,
        });

        if (response.ok) {
          return;
        }
      } catch {
        // retry below
      }

      if (attempt < 3) {
        await new Promise((resolve) => window.setTimeout(resolve, 250 * 2 ** (attempt - 1)));
      }
    }
  }

  private handlePageHide = (): void => {
    void this.flush({ useBeacon: true, force: true });
  };

  private handleVisibilityChange = (): void => {
    if (document.visibilityState === "hidden") {
      void this.flush({ useBeacon: true, force: true });
    }
  };

  private handleWindowError = (event: ErrorEvent): void => {
    const errorClass = event.error instanceof Error ? event.error.name : "Error";
    const message = event.error instanceof Error ? event.error.message : event.message;

    this.track("frontend_error_occurred", {
      pageRoute: window.location.pathname,
      componentName: "window",
      errorClass,
      errorFingerprint: getErrorFingerprint(errorClass, message || "window_error"),
      recoverable: false,
      actionTaken: "window_error_listener",
    });
  };

  private handleUnhandledRejection = (event: PromiseRejectionEvent): void => {
    const reason = event.reason;
    const errorClass = reason instanceof Error ? reason.name : "UnhandledRejection";
    const message = reason instanceof Error ? reason.message : typeof reason === "string" ? reason : "promise_rejection";

    this.track("frontend_error_occurred", {
      pageRoute: window.location.pathname,
      componentName: "promise",
      errorClass,
      errorFingerprint: getErrorFingerprint(errorClass, message),
      recoverable: false,
      actionTaken: "unhandledrejection_listener",
    });
  };

  noteAuthSessionExpiry(): void {
    this.track("auth_session_expired", {
      sessionAgeMinutes: getSessionAgeMinutes(),
      authMethod: "password",
      clientApp: "backoffice",
      expiryReason: "unauthorized_response",
    });
  }

  noteBackendException(requestMethod: string, route: string, statusCode: number, fingerprint: string): void {
    this.track("backend_unhandled_exception", {
      route,
      exceptionClass: "HttpError",
      errorFingerprint: fingerprint,
      requestMethod,
      statusCode,
      workerId: "backoffice-client",
    });
  }

  noteNavigation(pathname: string, previousRoute: string | null): void {
    this.track("navigation_section_opened", {
      sectionName: getNavigationSection(pathname),
      route: pathname,
      previousRoute,
      userRole: getUserRole(),
      entryPoint: previousRoute ? "route_change" : "initial_load",
    });
  }
}

export const telemetryService = new TelemetryService();

export function track(eventType: TelemetryEventType, properties: TelemetryProperties = {}): void {
  telemetryService.track(eventType, properties);
}

export function startTelemetry(): void {
  telemetryService.start();
}

export function stopTelemetry(): void {
  telemetryService.stop();
}

export function noteTelemetryNavigation(pathname: string, previousRoute: string | null): void {
  telemetryService.noteNavigation(pathname, previousRoute);
}

export function noteTelemetryAuthSessionExpiry(): void {
  telemetryService.noteAuthSessionExpiry();
}

export function noteTelemetryBackendException(
  requestMethod: string,
  route: string,
  statusCode: number,
  fingerprint: string
): void {
  telemetryService.noteBackendException(requestMethod, route, statusCode, fingerprint);
}
