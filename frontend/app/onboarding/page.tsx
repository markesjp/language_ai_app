"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiGet, apiPatch } from "../../lib/api";
import { notifySessionChanged } from "../components/SessionProvider";

type UserSession = {
  authenticated: boolean;
  onboarding_completed: boolean;
};

type OnboardingResponse = {
  onboarding_completed: boolean;
  recommended_scenario_id: string | null;
  recommended_scenario_title: string | null;
};

const goals = [
  { value: "conversation", label: "Conversação do dia a dia", hint: "Ganhar naturalidade em situações comuns." },
  { value: "travel", label: "Viagem", hint: "Hotel, aeroporto, restaurantes e deslocamento." },
  { value: "work", label: "Trabalho e entrevista", hint: "Reuniões, apresentações e carreira." },
  { value: "pronunciation", label: "Pronúncia", hint: "Falar com mais clareza e ritmo." },
];

export default function OnboardingPage() {
  const router = useRouter();
  const [targetLanguage, setTargetLanguage] = useState("en");
  const [proficiencyLevel, setProficiencyLevel] = useState("beginner");
  const [learningGoal, setLearningGoal] = useState("conversation");
  const [practicePreference, setPracticePreference] = useState("guided");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    apiGet<UserSession>("/auth/me")
      .then((session) => {
        if (!session.authenticated) router.replace("/login?reason=expired");
        else if (session.onboarding_completed) router.replace("/chat");
      })
      .catch(() => router.replace("/login"));
  }, [router]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setMessage("");
    try {
      const result = await apiPatch<OnboardingResponse, unknown>("/profiles/me/onboarding", {
        target_language: targetLanguage,
        proficiency_level: proficiencyLevel,
        learning_goal: learningGoal,
        practice_preference: practicePreference,
      });
      if (result.recommended_scenario_id) {
        window.localStorage.setItem("linguaflow_recommended_scenario_id", result.recommended_scenario_id);
        window.localStorage.setItem("linguaflow_recommended_scenario_title", result.recommended_scenario_title ?? "Missão recomendada");
      }
      notifySessionChanged();
      router.push("/chat");
    } catch (caught) {
      setMessage(caught instanceof Error ? caught.message : "Não consegui salvar seu onboarding agora.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="stack">
      <div className="hero-panel">
        <span className="pill">Primeira missão • 60 segundos</span>
        <h1>Vamos ajustar o LinguaFlow para você</h1>
        <p className="muted">Responda rapidinho e eu te levo para uma missão de prática já configurada.</p>
      </div>

      <form className="card stack" onSubmit={submit}>
        <div className="conversation-grid">
          <label className="stack">
            <span className="field-label">Idioma alvo</span>
            <select value={targetLanguage} onChange={(event) => setTargetLanguage(event.target.value)}>
              <option value="en">Inglês</option>
              <option value="es">Espanhol</option>
              <option value="fr">Francês</option>
              <option value="pt">Português</option>
            </select>
          </label>
          <label className="stack">
            <span className="field-label">Nível atual</span>
            <select value={proficiencyLevel} onChange={(event) => setProficiencyLevel(event.target.value)}>
              <option value="beginner">Iniciante</option>
              <option value="intermediate">Intermediário</option>
              <option value="advanced">Avançado</option>
            </select>
          </label>
        </div>

        <div className="stack">
          <span className="field-label">Objetivo principal</span>
          <div className="mission-grid">
            {goals.map((goal) => (
              <button
                type="button"
                className={`choice-card ${learningGoal === goal.value ? "selected" : ""}`}
                key={goal.value}
                onClick={() => setLearningGoal(goal.value)}
              >
                <strong>{goal.label}</strong>
                <span>{goal.hint}</span>
              </button>
            ))}
          </div>
        </div>

        <label className="stack">
          <span className="field-label">Estilo de treino</span>
          <select value={practicePreference} onChange={(event) => setPracticePreference(event.target.value)}>
            <option value="guided">Guiado e com correções leves</option>
            <option value="free-talk">Conversa mais livre</option>
            <option value="pronunciation-first">Foco em fala e pronúncia</option>
            <option value="vocabulary-first">Foco em vocabulário novo</option>
          </select>
        </label>

        {message && <div className="status-card danger">{message}</div>}
        <button disabled={loading}>{loading ? "Preparando missão..." : "Começar minha primeira missão"}</button>
      </form>
    </section>
  );
}
