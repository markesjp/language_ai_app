"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { apiPost } from "../../lib/api";
import { notifySessionChanged, useSessions, type UserSession } from "./SessionProvider";

export function UserSessionControls() {
  const router = useRouter();
  const { user, loading, refreshSessions } = useSessions();

  async function logout() {
    await apiPost<UserSession, Record<string, never>>("/auth/logout", {});
    notifySessionChanged();
    await refreshSessions();
    router.push("/login");
  }

  if (loading) {
    return <span className="session-chip">Verificando...</span>;
  }

  if (!user.authenticated) {
    return <Link className="session-chip" href="/login">Entrar/Criar conta</Link>;
  }

  return (
    <div className="session-cluster">
      <span className="session-chip is-online">{user.display_name ?? user.email}</span>
      <button className="ghost-button compact" onClick={logout}>Sair aluno</button>
    </div>
  );
}
