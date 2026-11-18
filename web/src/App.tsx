import { useIsRestoring, useMutationState, useQuery } from "@tanstack/react-query";
import { type ReactNode, useState } from "react";
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

// Ikony obrysowe 24×24; kolor bierze z tekstu przycisku.
const TAB_ICONS: Record<TabId, ReactNode> = {
  diary: (
    <>
      <path d="M5 4h11a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3z" />
      <path d="M5 17a3 3 0 0 1 3-3h11" />
    </>
  ),
  add: <path d="M12 5v14M5 12h14" />,
  health: <path d="M3 12h4l2-5 4 10 2-5h6" />,
  profile: (
    <>
      <circle cx="12" cy="8" r="4" />
      <path d="M4 20c1.5-4 4.5-6 8-6s6.5 2 8 6" />
    </>
  ),
};

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
            className={[t.id === "add" ? "add" : "", t.id === tab ? "active" : ""].join(" ").trim()}
            aria-current={t.id === tab ? "page" : undefined}
            onClick={() => setTab(t.id)}
          >
            <svg
              aria-hidden="true"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={t.id === "add" ? 2.4 : 2}
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              {TAB_ICONS[t.id]}
            </svg>
            {t.label}
          </button>
        ))}
      </nav>
    </div>
  );
}
