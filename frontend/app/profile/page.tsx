"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiGet, apiPatch } from "../../lib/api";
import { notifySessionChanged, useSessions } from "../components/SessionProvider";

type Profile = {
  user_id: string;
  email: string;
  display_name: string;
  native_language: string;
  target_language: string;
  proficiency_level: string;
  correction_preference: string;
  voice_preference: string | null;
  learning_goal: string | null;
  practice_preference: string | null;
  onboarding_completed: boolean;
  recommended_scenario_id: string | null;
};

const languageOptions = [
  { value: "en", label: "Inglês" },
  { value: "es", label: "Espanhol" },
  { value: "fr", label: "Francês" },
  { value: "pt", label: "Português" },
];

export default function ProfilePage() {
  const router = useRouter();
  const { user, loading: sessionLoading, can, refreshSessions } = useSessions();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (sessionLoading) return;
    if (!user.authenticated) {
      router.replace("/login?reason=expired");
      return;
    }
    apiGet<Profile>("/profiles/me")
      .then(setProfile)
      .catch(() => setMessage("Não consegui carregar seu perfil agora."));
  }, [router, sessionLoading, user.authenticated]);

  function update<K extends keyof Profile>(key: K, value: Profile[K]) {
    setProfile((current) => (current ? { ...current, [key]: value } : current));
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!profile) return;
    setSaving(true);
    setMessage("");
    try {
      const updated = await apiPatch<Profile, unknown>("/profiles/me", {
        display_name: profile.display_name,
        native_language: profile.native_language,
        target_language: profile.target_language,
        proficiency_level: profile.proficiency_level,
        correction_preference: profile.correction_preference,
        voice_preference: profile.voice_preference,
        learning_goal: profile.learning_goal,
        practice_preference: profile.practice_preference,
      });
      setProfile(updated);
      window.localStorage.removeItem("linguaflow_recommended_scenario_id");
      window.localStorage.removeItem("linguaflow_recommended_scenario_title");
      notifySessionChanged();
      await refreshSessions();
      setMessage("Preferências salvas. O chat já vai usar idioma, cenários e vozes compatíveis.");
    } catch (caught) {
      setMessage(caught instanceof Error ? caught.message : "Não consegui salvar suas preferências.");
    } finally {
      setSaving(false);
    }
  }

  if (!profile) {
    return <section className="card stack"><span className="pill">Perfil</span><h1>Carregando preferências...</h1></section>;
  }

  if (!can("profile:read")) {
    return <section className="card stack"><span className="pill">Acesso negado</span><h1>Seu perfil não permite ver preferências.</h1></section>;
  }

  return (
    <section className="stack">
      <div className="hero-panel">
        <span className="pill">Perfil do aluno • Preferências</span>
        <h1>Ajuste seu treino quando quiser</h1>
        <p className="muted">Seu idioma-alvo controla cenários, voz, reconhecimento de fala e recomendações.</p>
      </div>
      <form className="card stack" onSubmit={submit}>
        <div className="conversation-grid">
          <label className="stack">
            <span className="field-label">Nome</span>
            <input value={profile.display_name} onChange={(event) => update("display_name", event.target.value)} />
          </label>
          <label className="stack">
            <span className="field-label">Email</span>
            <input value={profile.email} disabled />
          </label>
        </div>
        <div className="conversation-grid">
          <label className="stack">
            <span className="field-label">Idioma alvo</span>
            <select value={profile.target_language} onChange={(event) => update("target_language", event.target.value)}>
              {languageOptions.map((option) => <option value={option.value} key={option.value}>{option.label}</option>)}
            </select>
          </label>
          <label className="stack">
            <span className="field-label">Nível</span>
            <select value={profile.proficiency_level} onChange={(event) => update("proficiency_level", event.target.value)}>
              <option value="beginner">Iniciante</option>
              <option value="intermediate">Intermediário</option>
              <option value="advanced">Avançado</option>
            </select>
          </label>
        </div>
        <div className="conversation-grid">
          <label className="stack">
            <span className="field-label">Objetivo</span>
            <select value={profile.learning_goal ?? "conversation"} onChange={(event) => update("learning_goal", event.target.value)}>
              <option value="conversation">Conversação</option>
              <option value="travel">Viagem</option>
              <option value="work">Trabalho e entrevista</option>
              <option value="pronunciation">Pronúncia</option>
            </select>
          </label>
          <label className="stack">
            <span className="field-label">Estilo de treino</span>
            <select value={profile.practice_preference ?? "guided"} onChange={(event) => update("practice_preference", event.target.value)}>
              <option value="guided">Guiado com correções leves</option>
              <option value="free-talk">Conversa livre</option>
              <option value="pronunciation-first">Foco em pronúncia</option>
              <option value="vocabulary-first">Foco em vocabulário</option>
            </select>
          </label>
        </div>
        {message && <div className="status-card">{message}</div>}
        <button disabled={saving || !can("profile:write")}>{saving ? "Salvando..." : "Salvar preferências"}</button>
      </form>
    </section>
  );
}
