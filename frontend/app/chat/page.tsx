"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { apiGet, apiPatch, apiPost } from "../../lib/api";
import { notifySessionChanged, useSessions } from "../components/SessionProvider";

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

type CatalogResponse = {
  skills: Skill[];
  scenarios: Scenario[];
  voice_presets: VoicePreset[];
};

type ChatResponse = {
  trace_id: string;
  conversation_turn_id: string;
  session_id: string;
  answer: string;
  feedback: { explanation: string; encouragement: string; focus_points: string[] };
  latency_ms: Record<string, number>;
  usage: { provider: string; model: string; input_tokens: number; output_tokens: number; estimated_cost_usd: number };
};

type BrowserSpeechRecognition = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start: () => void;
  stop: () => void;
  abort: () => void;
  onstart: (() => void) | null;
  onend: (() => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
};

type SpeechRecognitionConstructor = new () => BrowserSpeechRecognition;

declare global {
  interface Window {
    SpeechRecognition?: SpeechRecognitionConstructor;
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
  }

  interface SpeechRecognitionAlternative {
    readonly transcript: string;
  }

  interface SpeechRecognitionResult {
    readonly isFinal: boolean;
    readonly length: number;
    item(index: number): SpeechRecognitionAlternative;
    [index: number]: SpeechRecognitionAlternative;
  }

  interface SpeechRecognitionResultList {
    readonly length: number;
    item(index: number): SpeechRecognitionResult;
    [index: number]: SpeechRecognitionResult;
  }

  interface SpeechRecognitionEvent extends Event {
    readonly resultIndex: number;
    readonly results: SpeechRecognitionResultList;
  }
}

const languageOptions = [
  { label: "Inglês", target: "en", speech: "en-US", starter: "I want to introduce myself and practice a short conversation." },
  { label: "Espanhol", target: "es", speech: "es-ES", starter: "Quiero presentarme y practicar una conversación corta." },
  { label: "Francês", target: "fr", speech: "fr-FR", starter: "Je veux me présenter et pratiquer une courte conversation." },
  { label: "Português", target: "pt", speech: "pt-BR", starter: "Quero me apresentar e praticar uma conversa curta." },
];

const fallbackCatalog: CatalogResponse = { skills: [], scenarios: [], voice_presets: [] };

export default function ChatPage() {
  const router = useRouter();
  const { user, loading: sessionLoading, can, refreshSessions } = useSessions();
  const [catalog, setCatalog] = useState<CatalogResponse>(fallbackCatalog);
  const [targetLanguage, setTargetLanguage] = useState(user.target_language ?? "en");
  const [selectedScenarioId, setSelectedScenarioId] = useState("");
  const [selectedSkillIds, setSelectedSkillIds] = useState<string[]>([]);
  const [selectedVoicePresetId, setSelectedVoicePresetId] = useState("");
  const [voiceSpeed, setVoiceSpeed] = useState(0.96);
  const [message, setMessage] = useState(languageOptions[0].starter);
  const [customScenario, setCustomScenario] = useState("");
  const [customSkills, setCustomSkills] = useState("");
  const [response, setResponse] = useState<ChatResponse | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [status, setStatus] = useState<"idle" | "listening" | "thinking" | "speaking" | "unsupported">("idle");
  const [conversationEnabled, setConversationEnabled] = useState(false);
  const [transcriptPreview, setTranscriptPreview] = useState("");
  const [missionBanner, setMissionBanner] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [checkingSession, setCheckingSession] = useState(true);
  const recognitionRef = useRef<BrowserSpeechRecognition | null>(null);
  const loadingRef = useRef(false);
  const statusRef = useRef(status);
  const sessionIdRef = useRef<string | null>(null);
  const conversationEnabledRef = useRef(false);
  const selectedVoiceRef = useRef<VoicePreset | null>(null);
  const lastSubmittedRef = useRef("");

  const language = useMemo(
    () => languageOptions.find((option) => option.target === targetLanguage) ?? languageOptions[0],
    [targetLanguage],
  );
  const selectedScenario = catalog.scenarios.find((scenario) => scenario.id === selectedScenarioId) ?? null;
  const selectedVoice = catalog.voice_presets.find((preset) => preset.id === selectedVoicePresetId) ?? catalog.voice_presets[0] ?? null;

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
    setTargetLanguage(user.target_language ?? "en");
    const savedSessionId = window.localStorage.getItem("linguaflow_last_session_id");
    if (savedSessionId) {
      setSessionId(savedSessionId);
      sessionIdRef.current = savedSessionId;
    }
    setCheckingSession(false);
  }, [router, sessionLoading, user.authenticated, user.onboarding_completed, user.target_language]);

  useEffect(() => {
    if (checkingSession) return;
    apiGet<CatalogResponse>(`/practice/catalog?target_language=${targetLanguage}`)
      .then((payload) => {
        setCatalog(payload);
        const recommendedScenarioId = window.localStorage.getItem("linguaflow_recommended_scenario_id");
        const recommendedScenarioTitle = window.localStorage.getItem("linguaflow_recommended_scenario_title");
        const scenario =
          payload.scenarios.find((item) => item.id === recommendedScenarioId) ??
          payload.scenarios.find((item) => item.id === user.recommended_scenario_id) ??
          payload.scenarios[0] ??
          null;
        setSelectedScenarioId(scenario?.id ?? "");
        setSelectedSkillIds(scenario?.skills.map((skill) => skill.id) ?? []);
        if (recommendedScenarioId && scenario?.id === recommendedScenarioId) {
          setMissionBanner(`Missão recomendada: ${recommendedScenarioTitle ?? scenario.title}`);
        } else {
          setMissionBanner("");
        }
        const voice = payload.voice_presets.find((preset) => preset.id === user.voice_preference) ?? payload.voice_presets[0] ?? null;
        setSelectedVoicePresetId(voice?.id ?? "");
        setVoiceSpeed(voice?.speed ?? 0.96);
        setMessage(language.starter);
        setError(null);
      })
      .catch(() => setError("Catálogo indisponível. Confira se a API está rodando."));
  }, [checkingSession, language.starter, targetLanguage, user.recommended_scenario_id, user.voice_preference]);

  useEffect(() => {
    loadingRef.current = loading;
  }, [loading]);

  useEffect(() => {
    statusRef.current = status;
  }, [status]);

  useEffect(() => {
    sessionIdRef.current = sessionId;
  }, [sessionId]);

  useEffect(() => {
    conversationEnabledRef.current = conversationEnabled;
  }, [conversationEnabled]);

  useEffect(() => {
    selectedVoiceRef.current = selectedVoice;
  }, [selectedVoice]);

  useEffect(() => {
    return () => {
      recognitionRef.current?.abort();
      window.speechSynthesis?.cancel();
    };
  }, []);

  async function saveTargetLanguage(nextLanguage: string) {
    setTargetLanguage(nextLanguage);
    setSelectedScenarioId("");
    setSelectedVoicePresetId("");
    setSelectedSkillIds([]);
    await apiPatch("/profiles/me", { target_language: nextLanguage });
    notifySessionChanged();
    await refreshSessions();
  }

  function getSpeechRecognition() {
    return window.SpeechRecognition ?? window.webkitSpeechRecognition;
  }

  function toggleSkill(skillId: string) {
    setSelectedSkillIds((current) => (current.includes(skillId) ? current.filter((id) => id !== skillId) : [...current, skillId]));
  }

  function buildScenarioMessage(spokenMessage: string) {
    const skillNames = catalog.skills.filter((skill) => selectedSkillIds.includes(skill.id)).map((skill) => skill.name);
    return [
      `Scenario: ${(selectedScenario?.title ?? customScenario) || "free conversation"}`,
      `Skills to train: ${[...skillNames, customSkills].filter(Boolean).join(", ") || "fluency"}`,
      `Target language: ${language.label}.`,
      "Act as a live language tutor. Keep the answer short, natural, and ask one simple follow-up.",
      `Learner said: ${spokenMessage}`,
    ].join("\n");
  }

  function speakAnswer(text: string) {
    if (!("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    const preset = selectedVoiceRef.current;
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = preset?.language ?? language.speech;
    utterance.rate = voiceSpeed;
    utterance.pitch = preset?.pitch ?? 1;
    const voice = window.speechSynthesis.getVoices().find((item) => item.name === preset?.voice);
    if (voice) utterance.voice = voice;
    utterance.onstart = () => setStatus("speaking");
    utterance.onend = () => {
      setStatus("idle");
      if (conversationEnabledRef.current) window.setTimeout(() => startListening(), 450);
    };
    utterance.onerror = () => setStatus("idle");
    window.speechSynthesis.speak(utterance);
  }

  async function sendMessage(messageToSend = message, shouldSpeak = false) {
    const cleanMessage = messageToSend.trim();
    if (!cleanMessage || loadingRef.current || !user.user_id) return;
    lastSubmittedRef.current = cleanMessage;
    setLoading(true);
    setStatus("thinking");
    setError(null);
    try {
      const result = await apiPost<ChatResponse, unknown>("/conversation/chat", {
        user_id: user.user_id,
        session_id: sessionIdRef.current,
        topic: (selectedScenario?.title ?? customScenario) || "free conversation",
        native_language: "pt",
        target_language: targetLanguage,
        message: buildScenarioMessage(cleanMessage),
        mode: shouldSpeak ? "voice" : "text",
        voice_enabled: shouldSpeak,
        scenario_id: selectedScenario?.id ?? null,
        skill_ids: selectedSkillIds,
        custom_scenario: selectedScenario ? null : customScenario,
        custom_skills: customSkills,
        voice_preset_id: selectedVoice?.id ?? null,
        voice_speed: voiceSpeed,
      });
      setResponse(result);
      setSessionId(result.session_id);
      sessionIdRef.current = result.session_id;
      window.localStorage.setItem("linguaflow_last_session_id", result.session_id);
      if (shouldSpeak) speakAnswer(result.answer);
      else setStatus("idle");
    } catch (caught) {
      setStatus("idle");
      setError(caught instanceof Error ? caught.message : "Não consegui falar com a IA agora.");
    } finally {
      setLoading(false);
    }
  }

  function startListening() {
    const SpeechRecognition = getSpeechRecognition();
    if (!SpeechRecognition) {
      setStatus("unsupported");
      setError("Seu navegador não expõe reconhecimento de voz. Use Chrome ou Edge para o modo conversa.");
      return;
    }
    window.speechSynthesis?.cancel();
    recognitionRef.current?.abort();
    const recognition = new SpeechRecognition();
    recognitionRef.current = recognition;
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = selectedVoice?.language ?? language.speech;
    recognition.onstart = () => {
      setError(null);
      setTranscriptPreview("");
      setStatus("listening");
    };
    recognition.onerror = (event) => {
      setStatus("idle");
      if (event.error !== "aborted" && event.error !== "no-speech") setError(`Microfone: ${event.error}`);
    };
    recognition.onend = () => {
      if (statusRef.current === "listening") setStatus("idle");
    };
    recognition.onresult = (event) => {
      let interimTranscript = "";
      let finalTranscript = "";
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const transcript = event.results[index][0].transcript;
        if (event.results[index].isFinal) finalTranscript += transcript;
        else interimTranscript += transcript;
      }
      const spokenText = finalTranscript.trim();
      setTranscriptPreview(interimTranscript || spokenText);
      if (spokenText && spokenText !== lastSubmittedRef.current) {
        setMessage(spokenText);
        recognition.stop();
        void sendMessage(spokenText, true);
      }
    };
    recognition.start();
  }

  function toggleConversation() {
    if (conversationEnabled) {
      setConversationEnabled(false);
      recognitionRef.current?.abort();
      window.speechSynthesis?.cancel();
      setStatus("idle");
      return;
    }
    setConversationEnabled(true);
    startListening();
  }

  if (checkingSession) {
    return <section className="card stack"><span className="pill">Sessão</span><h1>Verificando seu acesso...</h1></section>;
  }

  if (!can("chat:write")) {
    return <section className="card stack"><span className="pill">Acesso negado</span><h1>Seu perfil não permite usar o chat.</h1></section>;
  }

  const statusLabel = {
    idle: conversationEnabled ? "Pronto para ouvir" : "Modo conversa desligado",
    listening: `Ouvindo em ${selectedVoice?.language ?? language.speech}...`,
    thinking: "Raciocinando com cenário e skills...",
    speaking: "Respondendo em voz...",
    unsupported: "Voz indisponível neste navegador",
  }[status];

  return (
    <section className="stack">
      <div className="hero-panel">
        <span className="pill">Chat guiado • {language.label}</span>
        <h1>Prática intuitiva e consistente</h1>
        <p className="muted">Idioma, voz, cenários e reconhecimento de fala ficam sincronizados para evitar combinações estranhas.</p>
      </div>

      {missionBanner && <div className="status-card">{missionBanner}</div>}
      {error && <div className="status-card warning">{error}</div>}

      <div className="settings-grid">
        <div className="card stack">
          <div className="panel-heading">
            <span className="mission-icon">1</span>
            <div><span className="pill">Minha missão</span><h2>Cenário</h2></div>
          </div>
          {catalog.scenarios.length ? (
            <div className="scenario-card-grid">
              {catalog.scenarios.map((scenario) => (
                <button
                  className={`choice-card ${selectedScenarioId === scenario.id ? "selected" : ""}`}
                  type="button"
                  key={scenario.id}
                  onClick={() => {
                    setSelectedScenarioId(scenario.id);
                    setSelectedSkillIds(scenario.skills.map((skill) => skill.id));
                  }}
                >
                  <strong>{scenario.title}</strong>
                  <span>{scenario.description}</span>
                </button>
              ))}
            </div>
          ) : (
            <div className="status-card warning">Nenhum cenário ativo para este idioma. Use cenário customizado ou cadastre no admin.</div>
          )}
          <input value={customScenario} onChange={(event) => setCustomScenario(event.target.value)} placeholder="Cenário customizado opcional" />
        </div>

        <div className="card stack">
          <div className="panel-heading">
            <span className="mission-icon">2</span>
            <div><span className="pill">Idioma e voz</span><h2>Configuração</h2></div>
          </div>
          <label className="stack">
            <span className="field-label">Idioma alvo</span>
            <select value={targetLanguage} onChange={(event) => void saveTargetLanguage(event.target.value)}>
              {languageOptions.map((option) => <option value={option.target} key={option.target}>{option.label}</option>)}
            </select>
          </label>
          <label className="stack">
            <span className="field-label">Voz compatível</span>
            <select value={selectedVoicePresetId} onChange={(event) => setSelectedVoicePresetId(event.target.value)} disabled={!catalog.voice_presets.length}>
              {catalog.voice_presets.map((preset) => <option value={preset.id} key={preset.id}>{preset.name} · {preset.language}</option>)}
            </select>
          </label>
          {!catalog.voice_presets.length && <div className="status-card warning">Sem voz compatível para este idioma.</div>}
          <label className="stack">
            <span className="field-label">Velocidade da voz: {voiceSpeed.toFixed(2)}x</span>
            <input type="range" min="0.5" max="1.6" step="0.02" value={voiceSpeed} onChange={(event) => setVoiceSpeed(Number(event.target.value))} />
          </label>
          <Link className="session-chip" href="/profile">Alterar preferências completas</Link>
        </div>
      </div>

      <div className="card stack">
        <div className="panel-heading">
          <span className="mission-icon">3</span>
          <div><span className="pill">Skills</span><h2>Foco do treino</h2></div>
        </div>
        <div className="skill-picker">
          {catalog.skills.map((skill) => (
            <button className={`chip-button ${selectedSkillIds.includes(skill.id) ? "selected" : ""}`} type="button" key={skill.id} onClick={() => toggleSkill(skill.id)}>
              {skill.name}
            </button>
          ))}
        </div>
        <input value={customSkills} onChange={(event) => setCustomSkills(event.target.value)} placeholder="Skills customizadas opcionais" />
      </div>

      <div className="card stack">
        <div className="panel-heading">
          <span className="mission-icon">4</span>
          <div><span className="pill">Mensagem/conversa</span><h2>Vamos praticar</h2></div>
        </div>
        {sessionId && <button className="ghost-button" type="button" onClick={() => setMessage("Let's continue where we stopped.")}>Continuar de onde parei</button>}
        <textarea value={message} onChange={(event) => setMessage(event.target.value)} />
        <div className="voice-controls">
          <button onClick={toggleConversation} disabled={loading && status !== "speaking"}>
            {conversationEnabled ? "Parar conversa" : "🎙️ Iniciar conversa"}
          </button>
          <button className="ghost-button" onClick={() => sendMessage(message, true)} disabled={loading}>Enviar e falar resposta</button>
        </div>
        <div className={`status-card ${status === "unsupported" || error ? "warning" : ""}`}>
          <strong>{statusLabel}</strong>
          {transcriptPreview && <p className="muted">Você: {transcriptPreview}</p>}
        </div>
      </div>

      {response && (
        <div className="grid">
          <div className="card stack">
            <h2>Resposta</h2>
            <div className="chat-bubble">{response.answer}</div>
            <p className="muted">{response.feedback.encouragement}</p>
          </div>
          <div className="card stack">
            <h2>Latência</h2>
            {Object.entries(response.latency_ms).map(([key, value]) => <div className="metric" key={key}>{key}: {value}ms</div>)}
          </div>
          <div className="card stack">
            <h2>Uso</h2>
            <div className="metric">Provider: {response.usage.provider}</div>
            <div className="metric">Modelo: {response.usage.model}</div>
            <div className="metric">Tokens: {response.usage.input_tokens + response.usage.output_tokens}</div>
            <div className="metric">Trace: {response.trace_id}</div>
          </div>
        </div>
      )}
    </section>
  );
}
