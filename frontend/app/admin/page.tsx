"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, apiGet, apiPost } from "../../lib/api";

type RagAnswer = {
  trace_id: string;
  answer: string;
  sources: { title: string; source_uri: string; confidence: number }[];
  confidence: number;
  origin: string;
  filters_used: Record<string, unknown>;
  latency_ms: Record<string, number>;
  usage: { provider: string; model: string; input_tokens: number; output_tokens: number; estimated_cost_usd: number };
};

type AdminSession = {
  authenticated: boolean;
  expires_at: number | null;
};

export default function AdminPage() {
  const router = useRouter();
  const [title, setTitle] = useState("Guia pedagógico inicial");
  const [content, setContent] = useState("Este documento descreve boas práticas para correção amigável em conversas de aprendizado de idiomas. A IA deve explicar erros com gentileza, manter o aluno motivado e adaptar exemplos ao nível do usuário.");
  const [question, setQuestion] = useState("Como a IA deve corrigir o aluno?");
  const [answer, setAnswer] = useState<RagAnswer | null>(null);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(false);
  const [checkingAuth, setCheckingAuth] = useState(true);

  useEffect(() => {
    apiGet<AdminSession>("/admin/auth/me")
      .then((session) => {
        if (!session.authenticated) router.push("/admin/login");
      })
      .catch(() => router.push("/admin/login"))
      .finally(() => setCheckingAuth(false));
  }, [router]);

  function handleAdminError(caught: unknown, fallback: string) {
    if (caught instanceof ApiError && caught.status === 401) {
      router.push("/admin/login");
      return;
    }
    setStatus(fallback);
  }

  async function ingest() {
    setLoading(true);
    setStatus("");
    try {
      const result = await apiPost<{ document_id: string; chunks_indexed: number }, unknown>("/admin/rag/documents", {
        title,
        source_uri: "manual://admin/guide",
        language: "pt",
        content,
        metadata: { permission: "admin" },
      });
      setStatus(`Missão concluída: documento ${result.document_id} indexado com ${result.chunks_indexed} chunk(s).`);
    } catch (caught) {
      handleAdminError(caught, "Não consegui indexar o documento. Revise a API e tente novamente.");
    } finally {
      setLoading(false);
    }
  }

  async function ask() {
    setLoading(true);
    setStatus("");
    try {
      const result = await apiPost<RagAnswer, unknown>("/admin/rag/ask", {
        question,
        language: "pt",
        include_analytics: true,
      });
      setAnswer(result);
    } catch (caught) {
      handleAdminError(caught, "Não consegui consultar o RAG. A sessão pode ter expirado ou a API caiu.");
    } finally {
      setLoading(false);
    }
  }

  if (checkingAuth) {
    return <section className="card stack"><span className="pill">Verificando acesso</span><h1>Carregando painel admin...</h1></section>;
  }

  return (
    <section className="stack">
      <div className="hero-panel">
        <span className="pill">Admin RAG • Conhecimento</span>
        <h1>Painel de inteligência documental</h1>
        <p className="muted">Indexe documentos, consulte evidências e acompanhe confiança, fontes, tokens e latência.</p>
      </div>

      {status && <div className="status-card">{status}</div>}

      <div className="mission-grid">
        <div className="card mission-card stack">
          <span className="mission-icon">01</span>
          <span className="pill">Etapa 1</span>
          <h2>Indexar conhecimento</h2>
          <label className="field-label">Título do documento</label>
          <input value={title} onChange={(event) => setTitle(event.target.value)} />
          <label className="field-label">Conteúdo</label>
          <textarea value={content} onChange={(event) => setContent(event.target.value)} />
          <div className="metric-row">
            <span>{content.length} caracteres</span>
            <span>{Math.max(1, Math.ceil(content.length / 900))} chunk(s) estimado(s)</span>
          </div>
          <button onClick={ingest} disabled={loading || content.length < 20}>{loading ? "Executando..." : "Indexar documento"}</button>
        </div>

        <div className="card mission-card stack">
          <span className="mission-icon">02</span>
          <span className="pill">Etapa 2</span>
          <h2>Consultar RAG</h2>
          <label className="field-label">Pergunta administrativa</label>
          <textarea value={question} onChange={(event) => setQuestion(event.target.value)} />
          <button onClick={ask} disabled={loading || question.length < 3}>{loading ? "Buscando evidências..." : "Perguntar ao RAG"}</button>
          <p className="muted">O guardrail evita PII operacional, conversas privadas e áudio bruto.</p>
        </div>
      </div>

      <div className="card stack">
        <div className="panel-heading">
          <span className="mission-icon">OK</span>
          <div>
            <span className="pill">Resultado</span>
            <h2>Resposta auditável</h2>
          </div>
        </div>
        {answer ? (
          <>
            <div className="confidence-meter">
              <span>Confiança</span>
              <div className="progress-track"><span style={{ width: `${Math.round(answer.confidence * 100)}%` }} /></div>
              <strong>{Math.round(answer.confidence * 100)}%</strong>
            </div>
            <div className="chat-bubble">{answer.answer}</div>
            <div className="grid">
              <div className="metric"><strong>Origem</strong><p>{answer.origin}</p></div>
              <div className="metric"><strong>Provider</strong><p>{answer.usage.provider} / {answer.usage.model}</p></div>
              <div className="metric"><strong>Tokens</strong><p>{answer.usage.input_tokens + answer.usage.output_tokens}</p></div>
            </div>
            <h3>Fontes</h3>
            <div className="source-grid">
              {answer.sources.length ? answer.sources.map((source) => (
                <div className="source-card" key={`${source.source_uri}-${source.confidence}`}>
                  <strong>{source.title}</strong>
                  <span>{source.source_uri}</span>
                  <small>Confiança {Math.round(source.confidence * 100)}%</small>
                </div>
              )) : <p className="muted">Nenhuma fonte acima do limiar. Indexe mais documentos para melhorar a resposta.</p>}
            </div>
            <small className="muted">Trace: {answer.trace_id} • Latência: {JSON.stringify(answer.latency_ms)}</small>
          </>
        ) : <p className="muted">Indexe um documento e faça uma pergunta para desbloquear a resposta auditável.</p>}
      </div>
    </section>
  );
}
