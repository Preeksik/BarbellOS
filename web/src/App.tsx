import { useIsRestoring, useMutationState, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { DiaryPage } from "./features/diary/DiaryPage";
import { AddPage } from "./features/diet/AddPage";
import { HealthPage } from "./features/health/HealthPage";
import { LoginForm } from "./features/home/LoginForm";
import { ProfilePage } from "./features/profile/ProfilePage";
import { type Session, api } from "./lib/api";
import { applyUpdate, useUpdateReady } from "./lib/appUpdate";
import { toIsoDay } from "./lib/diary";

// Zakładki są stanem, a nie adresami URL: iOS potrafi ponownie pytać o zgodę na kamerę
// po zmianie adresu wewnątrz zainstalowanej aplikacji (dokumentacja 3.3).
const TABS = [
  { id: "diary", label: "Dziennik" },
  { id: "add", label: "Dodaj" },
  { id: "health", label: "Zdrowie" },
  { id: "profile", label: "Profil" },
] as const;
type TabId = (typeof TABS)[number]["id"];

export function App() {
  const [tab, setTab] = useState<TabId>("diary");
  // Dzień oglądany w dzienniku. Zakładka „Dodaj" dodaje produkty do tego samego dnia.
  const [day, setDay] = useState(() => toIsoDay(new Date()));
  const restoring = useIsRestoring();
  const session = useQuery({ queryKey: ["me"], queryFn: () => api.get<Session>("/api/auth/me") });
  const unsent = useMutationState({ filters: { status: "pending" } }).length;
  const updateReady = useUpdateReady();

  const needsLogin = session.data?.auth_required && !session.data.authenticated;

  return (
    <div className="app">
      <header className="topbar">
        <h1>BarbellOS</h1>
        {unsent > 0 && <span className="badge">niewysłane: {unsent}</span>}
      </header>
      {updateReady && (
        <button type="button" className="update" onClick={applyUpdate}>
          Nowa wersja aplikacji · stuknij, żeby odświeżyć
        </button>
      )}

      <main>
        {restoring ? (
          <p className="muted">Wczytywanie…</p>
        ) : needsLogin ? (
          <LoginForm />
        ) : (
          <>
            {tab === "diary" && (
              <DiaryPage
                day={day}
                onDayChange={setDay}
                onAdd={() => setTab("add")}
                onOpenProfile={() => setTab("profile")}
              />
            )}
            {tab === "add" && <AddPage day={day} onShowDiary={() => setTab("diary")} />}
            {tab === "health" && <HealthPage />}
            {tab === "profile" && <ProfilePage />}
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
