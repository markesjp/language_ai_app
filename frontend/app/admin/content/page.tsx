"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, apiDelete, apiGet, apiPost, apiPut } from "../../../lib/api";
import { useSessions } from "../../components/SessionProvider";

type Skill = {
  id: string;
  name: string;
  description: string;
  target_language: string | null;
  level: string | null;
  is_active: boolean;
};

type Scenario = {
  id: string;
  title: string;
  description: string;
  prompt_template: string;
  target_language: string | null;
  level: string | null;
  is_active: boolean;
  skills: Skill[];
};

type VoicePreset = {
  id: string;
  name: string;
  provider: string;
  model: string;
  voice: string;
  language: string;
  speed: number;
  pitch: number;
  is_default: boolean;
  is_active: boolean;
};

type SkillDraft = Pick<Skill, "name" | "description" | "target_language" | "level" | "is_active">;
type ScenarioDraft = Pick<Scenario, "title" | "description" | "prompt_template" | "target_language" | "level" | "is_active"> & { skill_ids: string[] };
type VoiceDraft = Omit<VoicePreset, "id">;

const emptySkill: SkillDraft = { name: "", description: "", target_language: "en", level: "beginner", is_active: true };
const emptyScenario: ScenarioDraft = {
  title: "",
  description: "",
  prompt_template: "Act as a friendly live tutor in this scenario.",
  target_language: "en",
  level: "beginner",
  is_active: true,
  skill_ids: [],
};
const emptyVoice: VoiceDraft = {
  name: "",
  provider: "browser",
  model: "browser-speech-synthesis",
  voice: "",
  language: "en-US",
  speed: 0.96,
  pitch: 1,
  is_default: false,
  is_active: true,
};

export default function AdminContentPage() {
  const router = useRouter();
  const { admin, can } = useSessions();
  const canWriteCatalog = admin.authenticated || can("admin.catalog:write");
  const [skills, setSkills] = useState<Skill[]>([]);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [voices, setVoices] = useState<VoicePreset[]>([]);
  const [skillDraft, setSkillDraft] = useState<SkillDraft>(emptySkill);
  const [scenarioDraft, setScenarioDraft] = useState<ScenarioDraft>(emptyScenario);
  const [voiceDraft, setVoiceDraft] = useState<VoiceDraft>(emptyVoice);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    void loadAll();
  }, []);

  async function guarded<T>(work: () => Promise<T>): Promise<T | null> {
    try {
      return await work();
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) router.push("/admin/login");
      else setMessage("Não consegui falar com a API admin.");
      return null;
    }
  }

  async function loadAll() {
    setLoading(true);
    const payload = await guarded(async () => {
      const [loadedSkills, loadedScenarios, loadedVoices] = await Promise.all([
        apiGet<Skill[]>("/admin/skills"),
        apiGet<Scenario[]>("/admin/scenarios"),
        apiGet<VoicePreset[]>("/admin/voice-presets"),
      ]);
      return { loadedSkills, loadedScenarios, loadedVoices };
    });
    if (payload) {
      setSkills(payload.loadedSkills);
      setScenarios(payload.loadedScenarios);
      setVoices(payload.loadedVoices);
    }
    setLoading(false);
  }

  async function createSkill(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const created = await guarded(() => apiPost<Skill, SkillDraft>("/admin/skills", skillDraft));
    if (created) {
      setSkills((current) => [...current, created].sort((a, b) => a.name.localeCompare(b.name)));
      setSkillDraft(emptySkill);
      setMessage("Skill criada.");
    }
  }

  async function createScenario(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const created = await guarded(() => apiPost<Scenario, ScenarioDraft>("/admin/scenarios", scenarioDraft));
    if (created) {
      setScenarios((current) => [...current, created].sort((a, b) => a.title.localeCompare(b.title)));
      setScenarioDraft(emptyScenario);
      setMessage("Cenário criado.");
    }
  }

  async function createVoice(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const created = await guarded(() => apiPost<VoicePreset, VoiceDraft>("/admin/voice-presets", voiceDraft));
    if (created) {
      await loadAll();
      setVoiceDraft(emptyVoice);
      setMessage(`Preset de voz "${created.name}" criado.`);
    }
  }

  async function toggleSkill(skill: Skill) {
    const updated = await guarded(() => apiPut<Skill, Partial<Skill>>(`/admin/skills/${skill.id}`, { is_active: !skill.is_active }));
    if (updated) setSkills((current) => current.map((item) => (item.id === updated.id ? updated : item)));
  }

  async function toggleScenario(scenario: Scenario) {
    const updated = await guarded(() => apiPut<Scenario, Partial<ScenarioDraft>>(`/admin/scenarios/${scenario.id}`, { is_active: !scenario.is_active }));
    if (updated) setScenarios((current) => current.map((item) => (item.id === updated.id ? updated : item)));
  }

  async function toggleVoice(voice: VoicePreset) {
    const updated = await guarded(() => apiPut<VoicePreset, Partial<VoiceDraft>>(`/admin/voice-presets/${voice.id}`, { is_active: !voice.is_active }));
    if (updated) setVoices((current) => current.map((item) => (item.id === updated.id ? updated : item)));
  }

  async function softDelete(path: string) {
    await guarded(() => apiDelete<unknown>(path));
    await loadAll();
    setMessage("Item desativado.");
  }

  function toggleScenarioSkill(skillId: string) {
    setScenarioDraft((current) => ({
      ...current,
      skill_ids: current.skill_ids.includes(skillId) ? current.skill_ids.filter((id) => id !== skillId) : [...current.skill_ids, skillId],
    }));
  }

  if (loading) {
    return <section className="card stack"><span className="pill">Admin Conteúdo</span><h1>Carregando catálogo...</h1></section>;
  }

  return (
    <section className="stack">
      <div className="hero-panel">
        <span className="pill">Admin Conteúdo • Skills, cenários e vozes</span>
        <h1>Catálogo de prática</h1>
        <p className="muted">Configure missões prontas para o chat e presets locais de voz sem depender de API paga.</p>
      </div>
      {message && <div className="status-card">{message}</div>}

      <div className="settings-grid">
        <div className="card stack">
          <h2>Skills</h2>
          <form className="stack" onSubmit={createSkill}>
            <input value={skillDraft.name} onChange={(event) => setSkillDraft({ ...skillDraft, name: event.target.value })} placeholder="Nome da skill" />
            <textarea value={skillDraft.description} onChange={(event) => setSkillDraft({ ...skillDraft, description: event.target.value })} placeholder="Descrição" />
            <div className="conversation-grid">
              <input value={skillDraft.target_language ?? ""} onChange={(event) => setSkillDraft({ ...skillDraft, target_language: event.target.value })} placeholder="Idioma alvo" />
              <input value={skillDraft.level ?? ""} onChange={(event) => setSkillDraft({ ...skillDraft, level: event.target.value })} placeholder="Nível" />
            </div>
            <button disabled={!canWriteCatalog || !skillDraft.name}>Adicionar skill</button>
          </form>
          {skills.map((skill) => (
            <div className="setting-row" key={skill.id}>
              <div><strong>{skill.name}</strong><p className="muted">{skill.description || "Sem descrição"}</p></div>
              <button className="ghost-button" disabled={!canWriteCatalog} onClick={() => toggleSkill(skill)}>{skill.is_active ? "Ativa" : "Inativa"}</button>
            </div>
          ))}
        </div>

        <div className="card stack">
          <h2>Cenários</h2>
          <form className="stack" onSubmit={createScenario}>
            <input value={scenarioDraft.title} onChange={(event) => setScenarioDraft({ ...scenarioDraft, title: event.target.value })} placeholder="Título do cenário" />
            <textarea value={scenarioDraft.description} onChange={(event) => setScenarioDraft({ ...scenarioDraft, description: event.target.value })} placeholder="Descrição" />
            <textarea value={scenarioDraft.prompt_template} onChange={(event) => setScenarioDraft({ ...scenarioDraft, prompt_template: event.target.value })} placeholder="Prompt/instrução" />
            <div className="skill-picker">
              {skills.map((skill) => (
                <button className={`chip-button ${scenarioDraft.skill_ids.includes(skill.id) ? "selected" : ""}`} type="button" key={skill.id} onClick={() => toggleScenarioSkill(skill.id)}>
                  {skill.name}
                </button>
              ))}
            </div>
            <button disabled={!canWriteCatalog || !scenarioDraft.title}>Adicionar cenário</button>
          </form>
          {scenarios.map((scenario) => (
            <div className="setting-row" key={scenario.id}>
              <div><strong>{scenario.title}</strong><p className="muted">{scenario.skills.map((skill) => skill.name).join(", ") || "Sem skills vinculadas"}</p></div>
              <button className="ghost-button" disabled={!canWriteCatalog} onClick={() => toggleScenario(scenario)}>{scenario.is_active ? "Ativo" : "Inativo"}</button>
            </div>
          ))}
        </div>

        <div className="card stack">
          <h2>Presets de voz</h2>
          <form className="stack" onSubmit={createVoice}>
            <input value={voiceDraft.name} onChange={(event) => setVoiceDraft({ ...voiceDraft, name: event.target.value })} placeholder="Nome do preset" />
            <div className="conversation-grid">
              <input value={voiceDraft.voice} onChange={(event) => setVoiceDraft({ ...voiceDraft, voice: event.target.value })} placeholder="Nome da voz do navegador (opcional)" />
              <input value={voiceDraft.language} onChange={(event) => setVoiceDraft({ ...voiceDraft, language: event.target.value })} placeholder="Idioma, ex.: en-US" />
            </div>
            <label className="stack">
              <span className="field-label">Velocidade: {voiceDraft.speed.toFixed(2)}x</span>
              <input type="range" min="0.5" max="1.6" step="0.02" value={voiceDraft.speed} onChange={(event) => setVoiceDraft({ ...voiceDraft, speed: Number(event.target.value) })} />
            </label>
            <button disabled={!canWriteCatalog || !voiceDraft.name}>Adicionar preset</button>
          </form>
          {voices.map((voice) => (
            <div className="setting-row" key={voice.id}>
              <div><strong>{voice.name}</strong><p className="muted">{voice.language} · {voice.speed}x · {voice.is_default ? "padrão" : "alternativo"}</p></div>
              <div className="stack">
                <button className="ghost-button" disabled={!canWriteCatalog} onClick={() => toggleVoice(voice)}>{voice.is_active ? "Ativo" : "Inativo"}</button>
                <button className="ghost-button" disabled={!canWriteCatalog} onClick={() => softDelete(`/admin/voice-presets/${voice.id}`)}>Desativar</button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
