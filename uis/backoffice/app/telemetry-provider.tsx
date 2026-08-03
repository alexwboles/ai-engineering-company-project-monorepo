"use client";

import { useEffect, useRef } from "react";
import { usePathname } from "next/navigation";
import { noteTelemetryNavigation, startTelemetry } from "@/lib/telemetry";

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

  return null;
}
