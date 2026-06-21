"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { apiGet } from "../../lib/api";
import { useSessions } from "../components/SessionProvider";

type LearnerDashboard = {
  streak_days: number;
  practice_minutes: number;
  conversation_turns: number;
  skills_trained: string[];
  last_session_topic: string | null;
  recommendation: string;
};

export default function DashboardPage() {
  const router = useRouter();
  const { user, loading: sessionLoading, can } = useSessions();
  const [data, setData] = useState<LearnerDashboard | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (sessionLoading) return;
    if (!user.authenticated) {
      router.replace("/login?reason=expired");
      return;
    }
    if (!user.onboarding_completed) {
      router.replace("/onboarding");
      return;
    }
    if (!can("dashboard:read")) {
      setError("Seu perfil não permite acessar o dashboard.");
      setLoading(false);
      return;
    }
    apiGet<LearnerDashboard>("/profiles/me/dashboard")
      .then(setData)
      .catch(() => setError("Não consegui carregar seu progresso. Confira se a API está ligada."))
      .finally(() => setLoading(false));
  }, [can, router, sessionLoading, user.authenticated, user.onboarding_completed]);

  const maxValue = useMemo(
    () => Math.max(data?.practice_minutes ?? 0, data?.conversation_turns ?? 0, data?.streak_days ?? 0, 1),
    [data],
  );

  if (loading) {
    return <section className="card stack"><span className="pill">Progresso</span><h1>Carregando seu painel...</h1></section>;
  }

  return (
    <section className="stack">
      <div className="hero-panel">
        <span className="pill">Dashboard do aluno • Motivacional</span>
        <h1>Seu progresso de prática</h1>
        <p className="muted">{data?.recommendation ?? error}</p>
        {can("profile:read") && <Link className="session-chip" href="/profile">Alterar preferências</Link>}
      </div>

      {error && <div className="status-card danger">{error}</div>}

      <div className="grid">
        <div className="card xp-card">
          <span className="pill">Streak</span>
          <h2>{data?.streak_days ?? 0} dia(s)</h2>
          <div className="progress-track"><span style={{ width: `${Math.max(8, ((data?.streak_days ?? 0) / maxValue) * 100)}%` }} /></div>
        </div>
        <div className="card xp-card">
          <span className="pill">Minutos</span>
          <h2>{data?.practice_minutes ?? 0}</h2>
          <div className="progress-track"><span style={{ width: `${Math.max(8, ((data?.practice_minutes ?? 0) / maxValue) * 100)}%` }} /></div>
        </div>
        <div className="card xp-card">
          <span className="pill">Conversas</span>
          <h2>{data?.conversation_turns ?? 0}</h2>
          <div className="progress-track"><span style={{ width: `${Math.max(8, ((data?.conversation_turns ?? 0) / maxValue) * 100)}%` }} /></div>
        </div>
      </div>

      <div className="card stack">
        <div className="panel-heading">
          <span className="mission-icon">XP</span>
          <div>
            <span className="pill">Skills treinadas</span>
            <h2>Foco atual</h2>
          </div>
        </div>
        <div className="skill-picker">
          {(data?.skills_trained ?? ["conversação"]).map((skill) => <span className="badge" key={skill}>{skill}</span>)}
        </div>
        <div className="status-card">Última sessão: {data?.last_session_topic ?? "você ainda não iniciou uma conversa"}</div>
      </div>
    </section>
  );
}
