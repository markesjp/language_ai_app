"use client";

import { useState } from "react";
import { apiPost } from "../../lib/api";

type ChatResponse = {
  trace_id: string;
  conversation_turn_id: string;
  session_id: string;
  answer: string;
  feedback: { explanation: string; encouragement: string; focus_points: string[] };
  latency_ms: Record<string, number>;
  usage: { provider: string; model: string; input_tokens: number; output_tokens: number; estimated_cost_usd: number };
};

export default function ChatPage() {
  const [userId, setUserId] = useState("");
  const [message, setMessage] = useState("I want to practice ordering coffee in English.");
  const [response, setResponse] = useState<ChatResponse | null>(null);
  const [loading, setLoading] = useState(false);

  async function sendMessage() {
    setLoading(true);
    try {
      const result = await apiPost<ChatResponse, unknown>("/conversation/chat", {
        user_id: userId || "demo-user",
        topic: "daily conversation",
        native_language: "pt",
        target_language: "en",
        message,
        mode: "text",
        voice_enabled: false,
      });
      setResponse(result);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="stack">
      <div className="card stack">
        <span className="pill">Conversação auditável</span>
        <h1>Chat professor</h1>
        <input value={userId} onChange={(event) => setUserId(event.target.value)} placeholder="User ID cadastrado" />
        <textarea value={message} onChange={(event) => setMessage(event.target.value)} />
        <button onClick={sendMessage} disabled={loading}>{loading ? "Pensando..." : "Enviar"}</button>
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
