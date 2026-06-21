"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiGet, apiPost, API_BASE_URL } from "../../lib/api";
import { notifySessionChanged } from "../components/SessionProvider";

type UserSession = {
  authenticated: boolean;
  user_id: string | null;
  email: string | null;
  display_name: string | null;
  onboarding_completed: boolean;
  recommended_scenario_id: string | null;
};

type ResetResponse = {
  accepted: boolean;
  reset_token: string | null;
  message: string;
};

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register" | "reset">("login");
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const reason = new URLSearchParams(window.location.search).get("reason");
    if (reason === "expired") {
      setMessage("Sua sessão expirou. Entre novamente para continuar sua prática.");
    }
    apiGet<UserSession>("/auth/me")
      .then((session) => {
        if (!session.authenticated) return;
        router.replace(session.onboarding_completed ? "/chat" : "/onboarding");
      })
      .catch(() => setMessage("API indisponível. Confira se backend e Docker estão ligados."));
  }, [router]);

  function goNext(session: UserSession) {
    notifySessionChanged();
    router.push(session.onboarding_completed ? "/chat" : "/onboarding");
    router.refresh();
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setMessage("");
    try {
      if (mode === "register") {
        const result = await apiPost<UserSession, unknown>("/auth/register", {
          email,
          password,
          display_name: displayName || email.split("@")[0],
          native_language: "pt",
          target_language: "en",
          proficiency_level: "beginner",
        });
        goNext(result);
      }
      if (mode === "login") {
        const result = await apiPost<UserSession, unknown>("/auth/login", { email, password });
        goNext(result);
      }
      if (mode === "reset") {
        if (!resetToken) {
          const result = await apiPost<ResetResponse, { email: string }>("/auth/password-reset/request", { email });
          setResetToken(result.reset_token ?? "");
          setMessage(result.reset_token ? `Token local gerado: ${result.reset_token}` : result.message);
        } else {
          await apiPost<UserSession, unknown>("/auth/password-reset/confirm", { token: resetToken, new_password: newPassword });
          setMessage("Senha redefinida. Agora entre com a nova senha.");
          setMode("login");
          setPassword("");
          setNewPassword("");
        }
      }
    } catch (caught) {
      setMessage(caught instanceof Error ? caught.message : "Não consegui concluir a operação.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="login-shell">
      <div className="card login-card stack">
        <span className="pill">LinguaFlow • Acesso do aluno</span>
        <h1>Entre e continue praticando</h1>
        <p className="muted">Use email e senha, crie sua conta em segundos ou entre com Google para começar direto no treino guiado.</p>

        <a className="google-button" href={`${API_BASE_URL}/auth/google/start`}>
          Entrar com Google
        </a>

        <div className="tab-row" role="tablist" aria-label="Modo de autenticação">
          <button type="button" className={mode === "login" ? "" : "ghost-button"} onClick={() => setMode("login")}>Entrar</button>
          <button type="button" className={mode === "register" ? "" : "ghost-button"} onClick={() => setMode("register")}>Criar conta</button>
          <button type="button" className={mode === "reset" ? "" : "ghost-button"} onClick={() => setMode("reset")}>Redefinir senha</button>
        </div>

        <form className="stack" onSubmit={submit}>
          <label className="field-label" htmlFor="email">Email</label>
          <input id="email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="voce@email.com" autoComplete="email" />

          {mode === "register" && (
            <>
              <label className="field-label" htmlFor="display-name">Nome</label>
              <input id="display-name" value={displayName} onChange={(event) => setDisplayName(event.target.value)} placeholder="Como quer aparecer no app" autoComplete="name" />
            </>
          )}

          {mode !== "reset" && (
            <>
              <label className="field-label" htmlFor="password">Senha</label>
              <input id="password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Mínimo de 8 caracteres" autoComplete={mode === "login" ? "current-password" : "new-password"} />
            </>
          )}

          {mode === "reset" && resetToken && (
            <>
              <label className="field-label" htmlFor="reset-token">Token de redefinição</label>
              <input id="reset-token" value={resetToken} onChange={(event) => setResetToken(event.target.value)} />
              <label className="field-label" htmlFor="new-password">Nova senha</label>
              <input id="new-password" type="password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} placeholder="Nova senha" autoComplete="new-password" />
            </>
          )}

          {message && <div className="status-card">{message}</div>}
          <button disabled={loading || !email || (mode !== "reset" && !password)}>
            {loading ? "Processando..." : mode === "register" ? "Criar conta" : mode === "login" ? "Entrar" : resetToken ? "Salvar nova senha" : "Gerar token"}
          </button>
        </form>
      </div>
      <div className="card mission-card stack">
        <span className="mission-icon">GO</span>
        <h2>Primeiro acesso guiado</h2>
        <p className="muted">Depois do login, você passa por uma configuração rápida e recebe uma missão recomendada automaticamente.</p>
        <div className="progress-track"><span style={{ width: "68%" }} /></div>
        <small className="muted">Sem sessão ativa, o app sempre volta para esta tela.</small>
      </div>
    </section>
  );
}
