import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import { api } from "./api";

const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);

  async function refresh() {
    const token = localStorage.getItem("token");
    if (!token) {
      setUser(null);
      setReady(true);
      return;
    }
    try {
      const me = await api("/auth/me");
      setUser(me);
    } catch {
      localStorage.removeItem("token");
      setUser(null);
    } finally {
      setReady(true);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  const value = useMemo(
    () => ({
      user,
      ready,
      setUser,
      async login(email, password) {
        const data = await api("/auth/login", { method: "POST", body: { email, password } });
        localStorage.setItem("token", data.access_token);
        setUser(data.user);
        return data.user;
      },
      async register(payload) {
        const data = await api("/auth/register", { method: "POST", body: payload });
        localStorage.setItem("token", data.access_token);
        setUser(data.user);
        return data.user;
      },
      logout() {
        localStorage.removeItem("token");
        setUser(null);
      },
      refresh,
    }),
    [user, ready]
  );

  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}

export function useAuth() {
  return useContext(AuthCtx);
}
