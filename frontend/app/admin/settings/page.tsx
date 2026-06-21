"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, apiGet, apiPatch } from "../../../lib/api";
import { useSessions } from "../../components/SessionProvider";

type SettingItem = {
  key: string;
  label: string;
  category: string;
  value: unknown;
  masked_value: string | null;
  editable: boolean;
  secret: boolean;
  requires_restart: boolean;
  description: string;
  options: string[];
};

type SettingsResponse = {
  settings: SettingItem[];
  warnings: string[];
};

const categoryLabels: Record<string, string> = {
  ia: "IA e providers",
  rag: "RAG e memória",
  sistema: "Sistema",
  seguranca: "Segurança",
};

export default function AdminSettingsPage() {
  const router = useRouter();
  const { admin, can } = useSessions();
  const canWriteSettings = admin.authenticated || can("admin.settings:write");
  const [data, setData] = useState<SettingsResponse | null>(null);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    apiGet<SettingsResponse>("/admin/settings")
      .then((payload) => {
        setData(payload);
        setDrafts(Object.fromEntries(payload.settings.filter((item) => item.editable && !item.secret).map((item) => [item.key, String(item.value ?? "")])));
      })
      .catch((caught) => {
        if (caught instanceof ApiError && caught.status === 401) router.push("/admin/login");
        else setMessage("API indisponível. Não consegui carregar configurações.");
      })
      .finally(() => setLoading(false));
  }, [router]);

  const grouped = useMemo(() => {
    return (data?.settings ?? []).reduce<Record<string, SettingItem[]>>((groups, item) => {
      groups[item.category] = [...(groups[item.category] ?? []), item];
      return groups;
    }, {});
  }, [data]);

  function updateDraft(key: string, value: string) {
    setDrafts((current) => ({ ...current, [key]: value }));
  }

  async function save() {
    if (!data) return;
    setSaving(true);
    setMessage("");
    const values: Record<string, unknown> = {};
    for (const item of data.settings) {
      if (!item.editable) continue;
      if (item.secret) {
        if (drafts[item.key]?.trim()) values[item.key] = drafts[item.key].trim();
        continue;
      }
      values[item.key] = drafts[item.key] ?? item.value;
    }
    try {
      const updated = await apiPatch<SettingsResponse, { values: Record<string, unknown> }>("/admin/settings", { values });
      setData(updated);
      setDrafts(Object.fromEntries(updated.settings.filter((item) => item.editable && !item.secret).map((item) => [item.key, String(item.value ?? "")])));
      setMessage("Configurações salvas. Providers novos já valem para as próximas chamadas.");
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) router.push("/admin/login");
      else setMessage("Não consegui salvar. Revise os campos e tente novamente.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <section className="card stack"><span className="pill">Carregando</span><h1>Preparando cockpit...</h1></section>;
  }

  return (
    <section className="stack">
      <div className="hero-panel">
        <span className="pill">Admin Config • Sistema todo</span>
        <h1>Painel de configurações</h1>
        <p className="muted">Ajuste providers de IA/RAG em runtime e monitore infraestrutura crítica em modo seguro.</p>
      </div>

      {data?.warnings.map((warning) => <div className="status-card warning" key={warning}>{warning}</div>)}
      {message && <div className="status-card">{message}</div>}

      <div className="settings-grid">
        {Object.entries(grouped).map(([category, items]) => (
          <div className="card settings-panel stack" key={category}>
            <div className="panel-heading">
              <span className="mission-icon">{category === "ia" ? "IA" : category === "rag" ? "RAG" : category === "seguranca" ? "SEC" : "SYS"}</span>
              <div>
                <span className="pill">{categoryLabels[category] ?? category}</span>
                <h2>{categoryLabels[category] ?? category}</h2>
              </div>
            </div>
            {items.map((item) => (
              <div className="setting-row" key={item.key}>
                <div>
                  <strong>{item.label}</strong>
                  <p className="muted">{item.description}</p>
                  {item.requires_restart && <small className="badge warning-badge">Requer migração/restart</small>}
                </div>
                {item.editable ? (
                  item.options.length ? (
                    <select value={drafts[item.key] ?? String(item.value ?? "")} onChange={(event) => updateDraft(item.key, event.target.value)}>
                      {item.options.map((option) => <option key={option} value={option}>{option}</option>)}
                    </select>
                  ) : typeof item.value === "boolean" ? (
                    <select value={drafts[item.key] ?? String(item.value)} onChange={(event) => updateDraft(item.key, event.target.value)}>
                      <option value="false">false</option>
                      <option value="true">true</option>
                    </select>
                  ) : (
                    <input
                      type={item.secret ? "password" : "text"}
                      value={drafts[item.key] ?? ""}
                      onChange={(event) => updateDraft(item.key, event.target.value)}
                      placeholder={item.secret ? item.masked_value ?? "valor secreto" : String(item.value ?? "")}
                    />
                  )
                ) : (
                  <code>{item.masked_value ?? JSON.stringify(item.value)}</code>
                )}
              </div>
            ))}
          </div>
        ))}
      </div>

      <div className="action-bar">
        <button onClick={save} disabled={saving || !data || !canWriteSettings}>{saving ? "Salvando..." : "Salvar configurações"}</button>
      </div>
    </section>
  );
}
