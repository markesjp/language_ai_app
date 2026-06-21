"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, apiPost } from "../../../lib/api";
import { notifySessionChanged } from "../../components/SessionProvider";

type AdminSession = {
  authenticated: boolean;
  expires_at: number | null;
};

export default function AdminLoginPage() {
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      await apiPost<AdminSession, { password: string }>("/admin/auth/login", { password });
      notifySessionChanged();
      router.push("/admin/settings");
      router.refresh();
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) {
        setError("Senha mestre inválida. Verifique o .env ou redefina a credencial no banco.");
      } else {
        setError("Não consegui abrir o portal admin agora. Confira se a API está rodando.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="login-shell">
      <div className="card login-card stack">
        <span className="pill">Portal Admin • Acesso protegido</span>
        <h1>Entrar no cockpit</h1>
        <p className="muted">
          Use a senha mestre para liberar RAG, analytics e configurações sensíveis. Em desenvolvimento,
          se você ainda não configurou o `.env`, a senha inicial é <strong>admin123</strong>.
        </p>
        <form className="stack" onSubmit={submit}>
          <label className="field-label" htmlFor="master-password">Senha mestre</label>
          <input
            id="master-password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Digite a senha mestre"
            autoComplete="current-password"
          />
          {error && <div className="status-card danger">{error}</div>}
          <button disabled={loading || !password}>{loading ? "Validando..." : "Desbloquear painel"}</button>
        </form>
      </div>
      <div className="card mission-card">
        <span className="mission-icon">SEC</span>
        <h2>Segurança do MVP</h2>
        <p className="muted">A senha é salva com hash PBKDF2 + salt no banco. A sessão usa cookie HTTP-only assinado.</p>
        <div className="progress-track"><span style={{ width: "78%" }} /></div>
        <small className="muted">Nível de proteção: bom para demo/local.</small>
      </div>
    </section>
  );
}
