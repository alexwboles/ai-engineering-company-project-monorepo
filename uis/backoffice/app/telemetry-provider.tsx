"use client";

import { useEffect, useRef } from "react";
import { usePathname } from "next/navigation";
import { noteTelemetryNavigation, startTelemetry, track } from "@/lib/telemetry";

const WORKFLOW_ROUTES: Record<string, string> = {
  "/login": "authentication",
  "/register": "registration",
  "/forgot-password": "password_recovery",
  "/reset-password": "password_reset",
  "/account/change-password": "password_change",
  "/suppliers": "supplier_management",
  "/incidents": "incident_management",
};

function getWorkflowName(pathname: string): string | null {
  if (WORKFLOW_ROUTES[pathname]) {
    return WORKFLOW_ROUTES[pathname];
  }

  if (pathname.startsWith("/suppliers/")) {
    return "supplier_management";
  }

  if (pathname.startsWith("/incidents/")) {
    return "incident_management";
  }

  return null;
}

export function TelemetryProvider() {
  const pathname = usePathname();
  const previousRouteRef = useRef<string | null>(null);

  useEffect(() => {
    startTelemetry();
  }, []);

  useEffect(() => {
    noteTelemetryNavigation(pathname, previousRouteRef.current);
    previousRouteRef.current = pathname;
  }, [pathname]);

  useEffect(() => {
    const flowName = getWorkflowName(pathname);
    if (!flowName) {
      return;
    }

    const startedAt = Date.now();
    let emitted = false;

    const emitAbandonment = (exitRoute: string) => {
      if (emitted) {
        return;
      }

      emitted = true;
      track("workflow_abandoned", {
        flowName,
        stepName: "form",
        lastCompletedStep: "route_loaded",
        timeSinceStartSeconds: Math.round((Date.now() - startedAt) / 1000),
        exitRoute,
      });
    };

    const inactivityTimer = window.setTimeout(() => {
      emitAbandonment(pathname);
    }, 15_000);

    return () => {
      window.clearTimeout(inactivityTimer);

      if (Date.now() - startedAt >= 15_000) {
        emitAbandonment(pathname);
      }
    };
  }, [pathname]);

  return null;
}
