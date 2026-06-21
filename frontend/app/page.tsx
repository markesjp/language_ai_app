"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiGet } from "../lib/api";

type UserSession = {
  authenticated: boolean;
  onboarding_completed: boolean;
};

export default function HomeGatePage() {
  const router = useRouter();
  const [message, setMessage] = useState("Verificando sua sessão...");

  useEffect(() => {
    apiGet<UserSession>("/auth/me")
      .then((session) => {
        if (!session.authenticated) {
          router.replace("/login");
          return;
        }
        router.replace(session.onboarding_completed ? "/chat" : "/onboarding");
      })
      .catch(() => {
        setMessage("Não consegui validar sua sessão. Indo para o login...");
        window.setTimeout(() => router.replace("/login"), 700);
      });
  }, [router]);

  return (
    <section className="hero">
      <div className="card stack">
        <span className="pill">LinguaFlow AI</span>
        <h1>{message}</h1>
        <p className="muted">Se o token ainda estiver válido, você entra automaticamente. Se expirou, volta para o login.</p>
      </div>
      <div className="card stack">
        <h2>Fluxo inteligente</h2>
        <div className="metric">Sessão ativa → Chat</div>
        <div className="metric">Primeiro acesso → Onboarding</div>
        <div className="metric">Sessão expirada → Login</div>
      </div>
    </section>
  );
}
