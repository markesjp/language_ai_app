import Link from "next/link";

const pillars = [
  "IA conversacional plugável",
  "RAG aluno + RAG admin",
  "STT/TTS com auditoria",
  "Tokens, custos e latência",
  "Analytics sem PII",
  "Backend pronto para mobile",
];

export default function Home() {
  return (
    <section className="hero">
      <div className="card stack">
        <span className="pill">Web first • Mobile-ready • MCP-style</span>
        <h1>Aprendizado de línguas com IA humanizada, memória longa e auditoria real.</h1>
        <p className="muted">
          Pratique inglês, espanhol, português e francês com conversa, correção gentil, voz opcional,
          ofensiva, dashboards e RAG administrativo para documentos e insights agregados.
        </p>
        <Link href="/chat"><button>Começar conversa</button></Link>
      </div>
      <div className="card stack">
        <h2>Módulos</h2>
        {pillars.map((pillar) => <div className="metric" key={pillar}>{pillar}</div>)}
      </div>
    </section>
  );
}
