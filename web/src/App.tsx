import { useIsRestoring, useMutationState, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { ScanPage } from "./features/diet/ScanPage";
import { HealthPage } from "./features/health/HealthPage";
import { HomePage } from "./features/home/HomePage";
import { LoginForm } from "./features/home/LoginForm";
import { type Session, api } from "./lib/api";

// Zakładki są stanem, a nie adresami URL: iOS potrafi ponownie pytać o zgodę na kamerę
// po zmianie adresu wewnątrz zainstalowanej aplikacji (dokumentacja 3.3).
const TABS = [
  { id: "home", label: "Start" },
  { id: "scan", label: "Skan" },
  { id: "health", label: "Zdrowie" },
] as const;
type TabId = (typeof TABS)[number]["id"];

export function App() {
  const [tab, setTab] = useState<TabId>("home");
  const restoring = useIsRestoring();
  const session = useQuery({ queryKey: ["me"], queryFn: () => api.get<Session>("/api/auth/me") });
  const unsent = useMutationState({ filters: { status: "pending" } }).length;

  const needsLogin = session.data?.auth_required && !session.data.authenticated;

  return (
    <div className="app">
      <header className="topbar">
        <h1>BarbellOS</h1>
        {unsent > 0 && <span className="badge">niewysłane: {unsent}</span>}
      </header>

      <main>
        {restoring ? (
          <p className="muted">Wczytywanie…</p>
        ) : needsLogin ? (
          <LoginForm />
        ) : (
          <>
            {tab === "home" && <HomePage />}
            {tab === "scan" && <ScanPage />}
            {tab === "health" && <HealthPage />}
          </>
        )}
      </main>

      <nav className="tabs" aria-label="Sekcje">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            className={t.id === tab ? "active" : ""}
            aria-current={t.id === tab ? "page" : undefined}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </nav>
    </div>
  );
}
