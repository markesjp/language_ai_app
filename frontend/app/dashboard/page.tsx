import { apiGet } from "../../lib/api";

type DashboardResponse = {
  metrics: { name: string; value: number; dimensions: Record<string, string> }[];
  privacy_note: string;
};

export default async function DashboardPage() {
  let data: DashboardResponse | null = null;
  try {
    data = await apiGet<DashboardResponse>("/admin/analytics/dashboard");
  } catch {
    data = null;
  }

  return (
    <section className="stack">
      <div className="card">
        <span className="pill">Analytics agregado</span>
        <h1>Dashboard</h1>
        <p className="muted">{data?.privacy_note ?? "API indisponível. Suba o backend para carregar métricas reais."}</p>
      </div>
      <div className="grid">
        {(data?.metrics ?? [
          { name: "learners_total", value: 0, dimensions: {} },
          { name: "conversation_turns_total", value: 0, dimensions: {} },
          { name: "estimated_cost_usd_total", value: 0, dimensions: {} },
        ]).map((metric, index) => (
          <div className="metric" key={`${metric.name}-${index}`}>
            <strong>{metric.name}</strong>
            <h2>{metric.value}</h2>
            <p className="muted">{JSON.stringify(metric.dimensions)}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
