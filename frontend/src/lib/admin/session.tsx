"use client";

import { useRouter } from "next/navigation";
import { createContext, type ReactNode, useContext, useEffect, useState } from "react";

import { ApiError } from "@/lib/api/client";
import { adminApi } from "./api";
import type { AdminMe } from "./types";

export type Permission =
  | "admin:access"
  | "catalog:manage"
  | "content:manage"
  | "media:manage"
  | "inventory:manage"
  | "orders:manage"
  | "customers:manage"
  | "settings:manage"
  | "users:manage"
  | "audit:read";

interface AdminSession {
  user: AdminMe;
  can: (permission: Permission) => boolean;
  signOut: () => Promise<void>;
}

const SessionContext = createContext<AdminSession | null>(null);

type State = { status: "loading" } | { status: "ready"; user: AdminMe } | { status: "forbidden" } | { status: "error"; message: string };

/**
 * Loads the signed-in staff member from FastAPI (/admin/me). The UI uses permissions only to
 * hide what the user cannot do — the backend still authorises every request.
 */
export function AdminSessionProvider({
  children,
  renderState,
}: {
  children: ReactNode;
  renderState: (state: "loading" | "forbidden" | { error: string }, signOut: () => Promise<void>) => ReactNode;
}) {
  const router = useRouter();
  const [state, setState] = useState<State>({ status: "loading" });

  const signOut = async () => {
    try {
      await adminApi.logout();
    } finally {
      router.replace("/admin/login");
      router.refresh();
    }
  };

  useEffect(() => {
    let cancelled = false;
    adminApi
      .me()
      .then((user) => !cancelled && setState({ status: "ready", user }))
      .catch((error: unknown) => {
        if (cancelled) return;
        if (error instanceof ApiError && error.status === 401) {
          const next = encodeURIComponent(window.location.pathname + window.location.search);
          router.replace(`/admin/login?next=${next}`);
        } else if (error instanceof ApiError && error.status === 403) {
          setState({ status: "forbidden" });
        } else {
          setState({ status: "error", message: error instanceof Error ? error.message : "Unavailable" });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [router]);

  if (state.status === "loading") return renderState("loading", signOut);
  if (state.status === "forbidden") return renderState("forbidden", signOut);
  if (state.status === "error") return renderState({ error: state.message }, signOut);

  const session: AdminSession = {
    user: state.user,
    can: (permission) => state.user.permissions.includes(permission),
    signOut,
  };
  return <SessionContext.Provider value={session}>{children}</SessionContext.Provider>;
}

export function useAdminSession(): AdminSession {
  const session = useContext(SessionContext);
  if (!session) throw new Error("useAdminSession must be used inside <AdminSessionProvider>");
  return session;
}
