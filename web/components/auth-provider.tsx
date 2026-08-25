"use client";

import { onIdTokenChanged, signOut, User } from "firebase/auth";
import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { firebaseAuth, firebaseIsConfigured } from "../lib/firebase";

type AuthContextValue = { configured: boolean; loading: boolean; user: User | null; getIdToken: () => Promise<string | null>; logout: () => Promise<void> };
const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: Readonly<{ children: React.ReactNode }>) {
  const configured = firebaseIsConfigured();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(configured);
  useEffect(() => {
    if (!configured) return;
    return onIdTokenChanged(firebaseAuth(), (nextUser) => { setUser(nextUser); setLoading(false); });
  }, [configured]);
  const value = useMemo<AuthContextValue>(() => ({
    configured, loading, user,
    getIdToken: async () => user?.getIdToken() ?? null,
    logout: async () => { if (configured) await signOut(firebaseAuth()); },
  }), [configured, loading, user]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useIzfinAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useIzfinAuth AuthProvider içinde kullanılmalı.");
  return context;
}
