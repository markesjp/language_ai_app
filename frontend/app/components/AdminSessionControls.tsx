"use client";

import { useRouter } from "next/navigation";
import { apiPost } from "../../lib/api";
import { notifySessionChanged, useSessions, type AdminSession } from "./SessionProvider";

export function AdminSessionControls() {
  const router = useRouter();
  const { admin, refreshSessions } = useSessions();

  async function logout() {
    await apiPost<AdminSession, Record<string, never>>("/admin/auth/logout", {});
    notifySessionChanged();
    await refreshSessions();
    router.push("/admin/login");
  }

  if (!admin.authenticated) {
    return null;
  }

  return (
    <div className="session-cluster">
      <span className="session-chip is-online">Admin online</span>
      <button className="ghost-button compact" onClick={logout}>Sair admin</button>
    </div>
  );
}
