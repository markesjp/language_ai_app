"use client";

import { useState } from "react";
import { apiPost } from "../../lib/api";

type RagAnswer = {
  trace_id: string;
  answer: string;
  sources: { title: string; source_uri: string; confidence: number }[];
  confidence: number;
  latency_ms: Record<string, number>;
};

export default function AdminPage() {
  const [title, setTitle] = useState("Guia pedagógico inicial");
  const [content, setContent] = useState("Este documento descreve boas práticas para correção amigável em conversas de aprendizado de idiomas. A IA deve explicar erros com gentileza, manter o aluno motivado e adaptar exemplos ao nível do usuário.");
  const [question, setQuestion] = useState("Como a IA deve corrigir o aluno?");
  const [answer, setAnswer] = useState<RagAnswer | null>(null);
  const [status, setStatus] = useState("");

  async function ingest() {
    const result = await apiPost<{ document_id: string; chunks_indexed: number }, unknown>("/admin/rag/documents", {
      title,
      source_uri: "manual://admin/guide",
      language: "pt",
      content,
      metadata: { permission: "admin" },
    });
    setStatus(`Documento ${result.document_id} indexado com ${result.chunks_indexed} chunk(s).`);
  }

  async function ask() {
    const result = await apiPost<RagAnswer, unknown>("/admin/rag/ask", {
      question,
      language: "pt",
      include_analytics: true,
    });
    setAnswer(result);
  }

  return (
    <section className="grid">
      <div className="card stack">
        <span className="pill">Admin RAG documental</span>
        <h1>Indexar documento</h1>
        <input value={title} onChange={(event) => setTitle(event.target.value)} />
        <textarea value={content} onChange={(event) => setContent(event.target.value)} />
        <button onClick={ingest}>Indexar</button>
        <p className="muted">{status}</p>
      </div>
      <div className="card stack">
        <span className="pill">Perguntas sem PII</span>
        <h1>Perguntar ao RAG</h1>
        <textarea value={question} onChange={(event) => setQuestion(event.target.value)} />
        <button onClick={ask}>Perguntar</button>
      </div>
      <div className="card stack">
        <h2>Resposta</h2>
        {answer ? (
          <>
            <div className="chat-bubble">{answer.answer}</div>
            <div className="metric">Confiança: {answer.confidence}</div>
            <div className="metric">Trace: {answer.trace_id}</div>
            {answer.sources.map((source) => (
              <div className="metric" key={source.source_uri}>{source.title} • {source.confidence}</div>
            ))}
          </>
        ) : <p className="muted">Indexe e pergunte algo para ver fontes, confiança e latência.</p>}
      </div>
    </section>
  );
}
