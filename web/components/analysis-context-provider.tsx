"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { fetchScanHistory, latestCompletedScan } from "../lib/scan-context";
import { useIzfinAuth } from "./auth-provider";

type CachedAnalysisContext = {
  activeScanJobId?: string;
  selectedTicker?: string;
  activeUniverseProfile?: string;
  lastVisitedAnalysisRoute?: string;
};

export type AnalysisContextValue = {
  latestCompletedScanJobId: string;
  activeScanJobId: string;
  selectedTicker: string;
  activeUniverseProfile: string;
  lastVisitedAnalysisRoute: string;
  setActiveScan: (jobId: string) => void;
  setSelectedTicker: (ticker: string) => void;
  setActiveUniverseProfile: (profile: string) => void;
  setLastVisitedAnalysisRoute: (route: string) => void;
  refreshLatestCompletedScan: () => Promise<void>;
};

const AnalysisContext = createContext<AnalysisContextValue | null>(null);

function parseCachedContext(raw: string | null): CachedAnalysisContext {
  if (!raw) return {};
  try {
    const parsed = JSON.parse(raw) as CachedAnalysisContext;
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

export function AnalysisContextProvider({ children }: Readonly<{ children: React.ReactNode }>) {
  const { loading, user, getIdToken } = useIzfinAuth();
  const [latestCompletedScanJobId, setLatestCompletedScanJobId] = useState("");
  const [activeScanJobId, setActiveScanJobId] = useState("");
  const [selectedTicker, setSelectedTickerState] = useState("");
  const [activeUniverseProfile, setActiveUniverseProfileState] = useState("Kendi Listem");
  const [lastVisitedAnalysisRoute, setLastVisitedAnalysisRouteState] = useState("");
  const [hydratedUserId, setHydratedUserId] = useState("");

  const refreshLatestCompletedScan = useCallback(async () => {
    if (!user) {
      setLatestCompletedScanJobId("");
      return;
    }
    const token = await getIdToken();
    if (!token) return;
    const history = await fetchScanHistory(token);
    const latest = latestCompletedScan(history);
    const latestId = latest?.job_id ?? "";
    const completedJobIds = new Set(history.filter((item) => item.status === "completed").map((item) => item.job_id));
    setLatestCompletedScanJobId(latestId);
    setActiveScanJobId((current) => {
      if (current && completedJobIds.has(current)) return current;
      return latestId;
    });
  }, [getIdToken, user]);

  useEffect(() => {
    if (loading) return;
    if (!user) {
      setLatestCompletedScanJobId("");
      setActiveScanJobId("");
      setSelectedTickerState("");
      setActiveUniverseProfileState("Kendi Listem");
      setLastVisitedAnalysisRouteState("");
      setHydratedUserId("");
      return;
    }

    const storageKey = `izfin:analysis-context:${user.uid}`;
    const cached = parseCachedContext(window.localStorage.getItem(storageKey));
    setActiveScanJobId(String(cached.activeScanJobId ?? ""));
    setSelectedTickerState(String(cached.selectedTicker ?? "").trim().toUpperCase());
    setActiveUniverseProfileState(String(cached.activeUniverseProfile ?? "Kendi Listem"));
    setLastVisitedAnalysisRouteState(String(cached.lastVisitedAnalysisRoute ?? ""));
    setHydratedUserId(user.uid);
    void refreshLatestCompletedScan();
  }, [loading, refreshLatestCompletedScan, user]);

  useEffect(() => {
    if (!user || hydratedUserId !== user.uid) return;
    const storageKey = `izfin:analysis-context:${user.uid}`;
    window.localStorage.setItem(storageKey, JSON.stringify({
      activeScanJobId,
      selectedTicker,
      activeUniverseProfile,
      lastVisitedAnalysisRoute,
    }));
  }, [activeScanJobId, activeUniverseProfile, hydratedUserId, lastVisitedAnalysisRoute, selectedTicker, user]);

  const value = useMemo<AnalysisContextValue>(() => ({
    latestCompletedScanJobId,
    activeScanJobId,
    selectedTicker,
    activeUniverseProfile,
    lastVisitedAnalysisRoute,
    setActiveScan: (jobId: string) => setActiveScanJobId(jobId.trim()),
    setSelectedTicker: (ticker: string) => setSelectedTickerState(ticker.trim().toUpperCase()),
    setActiveUniverseProfile: (profile: string) => setActiveUniverseProfileState(profile.trim() || "Kendi Listem"),
    setLastVisitedAnalysisRoute: (route: string) => setLastVisitedAnalysisRouteState(route.trim()),
    refreshLatestCompletedScan,
  }), [activeScanJobId, activeUniverseProfile, lastVisitedAnalysisRoute, latestCompletedScanJobId, refreshLatestCompletedScan, selectedTicker]);

  return <AnalysisContext.Provider value={value}>{children}</AnalysisContext.Provider>;
}

export function useAnalysisContext(): AnalysisContextValue {
  const context = useContext(AnalysisContext);
  if (!context) throw new Error("useAnalysisContext AnalysisContextProvider içinde kullanılmalı.");
  return context;
}
