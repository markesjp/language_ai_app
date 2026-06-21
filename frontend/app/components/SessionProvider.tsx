"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { apiGet } from "../../lib/api";

export type UserSession = {
  authenticated: boolean;
  user_id: string | null;
  email: string | null;
  display_name: string | null;
  onboarding_completed: boolean;
  recommended_scenario_id: string | null;
  target_language: string | null;
  proficiency_level: string | null;
  learning_goal: string | null;
  practice_preference: string | null;
  voice_preference: string | null;
  profiles: string[];
  permissions: string[];
};

export type AdminSession = {
  authenticated: boolean;
  expires_at: number | null;
};

type SessionContextValue = {
  user: UserSession;
  admin: AdminSession;
  loading: boolean;
  can: (permission: string) => boolean;
  refreshSessions: () => Promise<void>;
};

const anonymousUser: UserSession = {
  authenticated: false,
  user_id: null,
  email: null,
  display_name: null,
  onboarding_completed: false,
  recommended_scenario_id: null,
  target_language: null,
  proficiency_level: null,
  learning_goal: null,
  practice_preference: null,
  voice_preference: null,
  profiles: [],
  permissions: [],
};

const anonymousAdmin: AdminSession = { authenticated: false, expires_at: null };

const SessionContext = createContext<SessionContextValue | null>(null);

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserSession>(anonymousUser);
  const [admin, setAdmin] = useState<AdminSession>(anonymousAdmin);
  const [loading, setLoading] = useState(true);

  const refreshSessions = useCallback(async () => {
    setLoading(true);
    const [userResult, adminResult] = await Promise.allSettled([
      apiGet<UserSession>("/auth/me"),
      apiGet<AdminSession>("/admin/auth/me"),
    ]);
    setUser(userResult.status === "fulfilled" ? userResult.value : anonymousUser);
    setAdmin(adminResult.status === "fulfilled" ? adminResult.value : anonymousAdmin);
    setLoading(false);
  }, []);

  useEffect(() => {
    void refreshSessions();
    function onFocus() {
      void refreshSessions();
    }
    function onSessionChanged() {
      void refreshSessions();
    }
    window.addEventListener("focus", onFocus);
    window.addEventListener("linguaflow-session-changed", onSessionChanged);
    return () => {
      window.removeEventListener("focus", onFocus);
      window.removeEventListener("linguaflow-session-changed", onSessionChanged);
    };
  }, [refreshSessions]);

  const can = useCallback((permission: string) => user.permissions.includes(permission), [user.permissions]);
  const value = useMemo(() => ({ user, admin, loading, can, refreshSessions }), [user, admin, loading, can, refreshSessions]);

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSessions() {
  const value = useContext(SessionContext);
  if (!value) {
    throw new Error("useSessions must be used inside SessionProvider");
  }
  return value;
}

export function notifySessionChanged() {
  window.dispatchEvent(new Event("linguaflow-session-changed"));
}
