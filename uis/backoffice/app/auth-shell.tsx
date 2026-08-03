"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { getStoredToken } from "@/lib/auth-client";

const PUBLIC_PATHS = new Set(["/login", "/register"]);

export function AuthShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const token = getStoredToken();
  const isPublic = PUBLIC_PATHS.has(pathname);

  useEffect(() => {
    if (!token && !isPublic) {
      router.replace("/login");
      return;
    }

    if (token && isPublic) {
      router.replace("/");
    }
  }, [isPublic, router, token]);

  if ((!token && !isPublic) || (token && isPublic)) {
    return (
      <main className="mx-auto flex w-full max-w-6xl flex-1 items-center justify-center px-4 py-12 sm:px-6 lg:px-8">
        <p className="rounded-lg bg-slate-100 px-4 py-3 text-sm text-slate-700">Loading secure workspace...</p>
      </main>
    );
  }

  return <>{children}</>;
}
