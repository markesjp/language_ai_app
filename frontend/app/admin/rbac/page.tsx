"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, apiGet, apiPost, apiPut } from "../../../lib/api";
import { useSessions } from "../../components/SessionProvider";

type Permission = { key: string; description: string };
type RbacProfile = {
  id: string;
  name: string;
  description: string;
  is_system: boolean;
  is_active: boolean;
  permissions: Permission[];
};
type RbacUser = {
  id: string;
  email: string;
  display_name: string;
  profile_ids: string[];
  profile_names: string[];
  permissions: string[];
};
type Overview = {
  profiles: RbacProfile[];
  permissions: Permission[];
  users: RbacUser[];
};

export default function AdminRbacPage() {
  const router = useRouter();
  const { admin, can } = useSessions();
  const [data, setData] = useState<Overview | null>(null);
  const [selectedProfileId, setSelectedProfileId] = useState("");
  const [selectedPermissionKeys, setSelectedPermissionKeys] = useState<string[]>([]);
  const [newProfileName, setNewProfileName] = useState("");
  const [newProfileDescription, setNewProfileDescription] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const canWriteRbac = admin.authenticated || can("admin.rbac:write");
  const canWriteUsers = admin.authenticated || can("admin.users:write");

  useEffect(() => {
    void load();
  }, []);

  async function guarded<T>(work: () => Promise<T>): Promise<T | null> {
    try {
      return await work();
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) router.push("/login?reason=expired");
      else if (caught instanceof ApiError && caught.status === 403) setMessage("Acesso negado para gestão RBAC.");
      else setMessage("Não consegui carregar RBAC agora.");
      return null;
    }
  }

  async function load() {
    setLoading(true);
    const overview = await guarded(() => apiGet<Overview>("/admin/rbac/overview"));
    if (overview) {
      setData(overview);
      const firstProfile = overview.profiles[0];
      if (firstProfile) {
        setSelectedProfileId(firstProfile.id);
        setSelectedPermissionKeys(firstProfile.permissions.map((permission) => permission.key));
      }
    }
    setLoading(false);
  }

  const selectedProfile = useMemo(
    () => data?.profiles.find((profile) => profile.id === selectedProfileId) ?? null,
    [data?.profiles, selectedProfileId],
  );

  function selectProfile(profile: RbacProfile) {
    setSelectedProfileId(profile.id);
    setSelectedPermissionKeys(profile.permissions.map((permission) => permission.key));
  }

  function togglePermission(key: string) {
    setSelectedPermissionKeys((current) => current.includes(key) ? current.filter((item) => item !== key) : [...current, key]);
  }

  async function saveProfile() {
    if (!selectedProfile) return;
    const updated = await guarded(() => apiPut<RbacProfile, unknown>(`/admin/rbac/profiles/${selectedProfile.id}`, {
      name: selectedProfile.name,
      description: selectedProfile.description,
      is_active: selectedProfile.is_active,
      permission_keys: selectedPermissionKeys,
    }));
    if (updated) {
      setMessage(`Perfil ${updated.name} atualizado.`);
      await load();
    }
  }

  async function createProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const created = await guarded(() => apiPost<RbacProfile, unknown>("/admin/rbac/profiles", {
      name: newProfileName,
      description: newProfileDescription,
      is_active: true,
      permission_keys: [],
    }));
    if (created) {
      setNewProfileName("");
      setNewProfileDescription("");
      setMessage(`Perfil ${created.name} criado.`);
      await load();
    }
  }

  async function toggleUserProfile(user: RbacUser, profileId: string) {
    const profileIds = user.profile_ids.includes(profileId)
      ? user.profile_ids.filter((id) => id !== profileId)
      : [...user.profile_ids, profileId];
    const updated = await guarded(() => apiPut<RbacUser, { profile_ids: string[] }>(`/admin/rbac/users/${user.id}/profiles`, { profile_ids: profileIds }));
    if (updated) {
      setMessage(`Perfis de ${updated.email} atualizados.`);
      await load();
    }
  }

  if (loading) {
    return <section className="card stack"><span className="pill">RBAC</span><h1>Carregando permissões...</h1></section>;
  }

  if (!data) {
    return <section className="card stack"><span className="pill">RBAC</span><h1>Acesso indisponível</h1><p className="muted">{message}</p></section>;
  }

  return (
    <section className="stack">
      <div className="hero-panel">
        <span className="pill">Admin RBAC • Perfis e permissões</span>
        <h1>Gestão de acesso</h1>
        <p className="muted">Crie perfis, combine permissões e associe usuários a um ou mais perfis.</p>
      </div>
      {message && <div className="status-card">{message}</div>}

      <div className="settings-grid">
        <div className="card stack">
          <h2>Perfis</h2>
          {data.profiles.map((profile) => (
            <button
              className={`choice-card ${selectedProfileId === profile.id ? "selected" : ""}`}
              type="button"
              key={profile.id}
              onClick={() => selectProfile(profile)}
            >
              <strong>{profile.name}</strong>
              <span>{profile.description} · {profile.permissions.length} permissão(ões)</span>
            </button>
          ))}
          {canWriteRbac && (
            <form className="stack" onSubmit={createProfile}>
              <input value={newProfileName} onChange={(event) => setNewProfileName(event.target.value)} placeholder="Novo perfil" />
              <input value={newProfileDescription} onChange={(event) => setNewProfileDescription(event.target.value)} placeholder="Descrição" />
              <button disabled={!newProfileName}>Criar perfil</button>
            </form>
          )}
        </div>

        <div className="card stack">
          <h2>Permissões de {selectedProfile?.name ?? "perfil"}</h2>
          <div className="skill-picker">
            {data.permissions.map((permission) => (
              <button
                className={`chip-button ${selectedPermissionKeys.includes(permission.key) ? "selected" : ""}`}
                disabled={!canWriteRbac}
                type="button"
                key={permission.key}
                onClick={() => togglePermission(permission.key)}
                title={permission.description}
              >
                {permission.key}
              </button>
            ))}
          </div>
          <button onClick={saveProfile} disabled={!canWriteRbac || !selectedProfile}>Salvar permissões</button>
        </div>
      </div>

      <div className="card stack">
        <div className="panel-heading">
          <span className="mission-icon">USR</span>
          <div>
            <span className="pill">Usuários</span>
            <h2>Vínculos com perfis</h2>
          </div>
        </div>
        {data.users.map((user) => (
          <div className="setting-row" key={user.id}>
            <div>
              <strong>{user.display_name}</strong>
              <p className="muted">{user.email}</p>
              <small className="muted">Permissões: {user.permissions.length}</small>
            </div>
            <div className="skill-picker">
              {data.profiles.map((profile) => (
                <button
                  className={`chip-button ${user.profile_ids.includes(profile.id) ? "selected" : ""}`}
                  disabled={!canWriteUsers}
                  type="button"
                  key={profile.id}
                  onClick={() => toggleUserProfile(user, profile.id)}
                >
                  {profile.name}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
