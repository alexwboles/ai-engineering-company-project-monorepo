"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { clearStoredToken, getStoredToken } from "@/lib/auth-client";

export function NavClient() {
  const pathname = usePathname();
  const router = useRouter();
  const token = getStoredToken();
  const isAuthView =
    pathname === "/login" ||
    pathname === "/register" ||
    pathname === "/forgot-password" ||
    pathname === "/reset-password";

  if (isAuthView) {
    return (
      <div className="flex items-center gap-2 text-sm">
        <Link href="/login" className="rounded-full bg-slate-100 px-3 py-1 text-slate-700 hover:bg-slate-200">
          Login
        </Link>
        <Link href="/register" className="rounded-full bg-teal-100 px-3 py-1 font-medium text-teal-800 hover:bg-teal-200">
          Register
        </Link>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 text-sm">
      <Link href="/" className="rounded-full bg-slate-100 px-3 py-1 text-slate-700 hover:bg-slate-200">
        Operations
      </Link>
      <Link href="/suppliers" className="rounded-full bg-teal-100 px-3 py-1 font-medium text-teal-800 hover:bg-teal-200">
        Suppliers
      </Link>
      <Link href="/incidents" className="rounded-full bg-cyan-100 px-3 py-1 font-medium text-cyan-800 hover:bg-cyan-200">
        Incidents
      </Link>
      <Link href="/telemetry" className="rounded-full bg-slate-900 px-3 py-1 font-medium text-white hover:bg-slate-700">
        Telemetry
      </Link>
      <Link href="/reporting" className="rounded-full bg-orange-100 px-3 py-1 font-medium text-orange-800 hover:bg-orange-200">
        Business Report
      </Link>
      <Link href="/inventory/products" className="rounded-full bg-emerald-100 px-3 py-1 font-medium text-emerald-800 hover:bg-emerald-200">
        Inventory
      </Link>
      <Link href="/rfp" className="rounded-full bg-violet-100 px-3 py-1 font-medium text-violet-800 hover:bg-violet-200">
        RFP Intake
      </Link>
      <Link href="/knowledge" className="rounded-full bg-teal-100 px-3 py-1 font-medium text-teal-800 hover:bg-teal-200">
        Knowledge
      </Link>
      <Link href="/chat" className="rounded-full bg-sky-100 px-3 py-1 font-medium text-sky-800 hover:bg-sky-200">
        Support Chat
      </Link>
      <Link href="/account/profile" className="rounded-full bg-indigo-100 px-3 py-1 font-medium text-indigo-800 hover:bg-indigo-200">
        Profile
      </Link>
      <Link href="/account/change-password" className="rounded-full bg-amber-100 px-3 py-1 font-medium text-amber-800 hover:bg-amber-200">
        Change Password
      </Link>
      {token ? (
        <button
          className="rounded-full bg-rose-100 px-3 py-1 font-medium text-rose-800 hover:bg-rose-200"
          onClick={() => {
            clearStoredToken();
            router.replace("/login");
          }}
          type="button"
        >
          Logout
        </button>
      ) : null}
    </div>
  );
}
