import { useIsRestoring, useMutationState, useQuery } from "@tanstack/react-query";
import { type ReactNode, useEffect, useRef, useState } from "react";
import { DiaryPage } from "./features/diary/DiaryPage";
import { AddPage } from "./features/diet/AddPage";
import { HealthPage } from "./features/health/HealthPage";
import { LoginForm } from "./features/home/LoginForm";
import { ProfilePage } from "./features/profile/ProfilePage";
import { TrainingPage } from "./features/training/TrainingPage";
import { type MealSlot, type Session, api } from "./lib/api";
import { applyUpdate, useUpdateReady } from "./lib/appUpdate";
import { toIsoDay } from "./lib/diary";

// Zakładki są stanem, a nie adresami URL: iOS potrafi ponownie pytać o zgodę na kamerę
// po zmianie adresu wewnątrz zainstalowanej aplikacji (dokumentacja 3.3).
// Dodawanie jedzenia nie jest osobną zakładką: otwiera się z posiłku w Diecie (19.11.2026).
const TABS = [
  { id: "diet", label: "Dieta" },
  { id: "training", label: "Trening" },
  { id: "health", label: "Zdrowie" },
  { id: "profile", label: "Profil" },
] as const;
type TabId = (typeof TABS)[number]["id"];

// Ikony obrysowe 24×24; kolor bierze z tekstu przycisku.
const TAB_ICONS: Record<TabId, ReactNode> = {
  diet: (
    <>
      <path d="M7 3v8a2 2 0 0 0 2 2v8" />
      <path d="M11 3v8a2 2 0 0 1-2 2" />
      <path d="M17 21V3c-2 1-3 4-3 8h3" />
    </>
  ),
  // Sztanga z boku: gryf i talerze (etap 4).
  training: <path d="M6 7v10M3 10v4M18 7v10M21 10v4M6 12h12" />,
  health: <path d="M3 12h4l2-5 4 10 2-5h6" />,
  profile: (
    <>
      <circle cx="12" cy="8" r="4" />
      <path d="M4 20c1.5-4 4.5-6 8-6s6.5 2 8 6" />
    </>
  ),
};

export function App() {
  const [tab, setTab] = useState<TabId>("diet");
  // Dzień oglądany w Diecie. Dodawanie dodaje produkty do tego dnia i wybranego posiłku.
  const [day, setDay] = useState(() => toIsoDay(new Date()));
  const [adding, setAdding] = useState<MealSlot | null>(null);
  const restoring = useIsRestoring();
  const session = useQuery({ queryKey: ["me"], queryFn: () => api.get<Session>("/api/auth/me") });
  const unsent = useMutationState({ filters: { status: "pending" } }).length;
  const updateReady = useUpdateReady();

  const needsLogin = session.data?.auth_required && !session.data.authenticated;
  const main = useRef<HTMLElement>(null);

  // Nowy ekran (zakładka albo dodawanie) zaczyna się od góry, a nie od miejsca przewinięcia.
  useEffect(() => {
    main.current?.scrollTo(0, 0);
  }, [tab, adding]);

  function openTab(next: TabId) {
    // Stuknięcie „Dieta" w trakcie dodawania wraca do listy posiłków.
    setAdding(null);
    setTab(next);
  }

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

      <main ref={main}>
        {restoring ? (
          <p className="muted">Wczytywanie…</p>
        ) : needsLogin ? (
          <LoginForm />
        ) : (
          <>
            {tab === "diet" &&
              (adding ? (
                <AddPage day={day} slot={adding} onClose={() => setAdding(null)} />
              ) : (
                <DiaryPage
                  day={day}
                  onDayChange={setDay}
                  onAdd={setAdding}
                  onOpenProfile={() => openTab("profile")}
                />
              ))}
            {tab === "training" && <TrainingPage />}
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
            onClick={() => openTab(t.id)}
          >
            <svg
              aria-hidden="true"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
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
