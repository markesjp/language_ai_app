"use client";

import Link from "next/link";
import { useSessions } from "./SessionProvider";

export function AppNav() {
  const { user, admin, loading, can } = useSessions();

  return (
    <nav>
      {loading && <span className="session-chip">Carregando sessão</span>}
      {!loading && user.authenticated && can("chat:read") && <Link href="/chat">Chat</Link>}
      {!loading && user.authenticated && can("dashboard:read") && <Link href="/dashboard">Dashboard</Link>}
      {!loading && user.authenticated && can("profile:read") && <Link href="/profile">Perfil</Link>}
      {!loading && !user.authenticated && <Link href="/login">Conta</Link>}
      {!loading && (admin.authenticated || can("admin.rag:read")) && <Link href="/admin">Admin RAG</Link>}
      {!loading && (admin.authenticated || can("admin.catalog:read")) && <Link href="/admin/content">Conteúdo</Link>}
      {!loading && (admin.authenticated || can("admin.settings:read")) && <Link href="/admin/settings">Configurações</Link>}
      {!loading && (admin.authenticated || can("admin.rbac:read")) && <Link href="/admin/rbac">RBAC</Link>}
    </nav>
  );
}
