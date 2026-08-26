"use client";

import { onIdTokenChanged, signOut, User } from "firebase/auth";
import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { configureAuthRecovery } from "../lib/api";
import { firebaseAuth, firebaseIsConfigured } from "../lib/firebase";

type AuthContextValue = {
  configured: boolean;
  loading: boolean;
  user: User | null;
  getIdToken: (forceRefresh?: boolean) => Promise<string | null>;
  logout: () => Promise<void>;
};
const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: Readonly<{ children: React.ReactNode }>) {
  const configured = firebaseIsConfigured();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(configured);

  useEffect(() => {
    if (!configured) {
      configureAuthRecovery(null);
      return;
    }

    const auth = firebaseAuth();
    configureAuthRecovery({
      refreshToken: async () => auth.currentUser?.getIdToken(true) ?? null,
      onSessionExpired: async () => { await signOut(auth); },
    });
    const unsubscribe = onIdTokenChanged(auth, (nextUser) => {
      setUser(nextUser);
      setLoading(false);
    });
    return () => {
      configureAuthRecovery(null);
      unsubscribe();
    };
  }, [configured]);

  const value = useMemo<AuthContextValue>(() => ({
    configured,
    loading,
    user,
    getIdToken: async (forceRefresh = false) => user?.getIdToken(forceRefresh) ?? null,
    logout: async () => { if (configured) await signOut(firebaseAuth()); },
  }), [configured, loading, user]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useIzfinAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useIzfinAuth AuthProvider içinde kullanılmalı.");
  return context;
}
