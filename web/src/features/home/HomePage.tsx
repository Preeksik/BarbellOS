import { onlineManager, useMutation, useMutationState, useQuery } from "@tanstack/react-query";
import { useState, useSyncExternalStore } from "react";
import { type Probe, api } from "../../lib/api";
import { BUILD_TIME } from "../../lib/appUpdate";
import { type ProbeInput, mutationKeys } from "../../lib/offline";

const VERSION_FORMAT: Intl.DateTimeFormatOptions = { dateStyle: "short", timeStyle: "short" };

/** Ekran etapu 0: stan serwera, instalacja PWA i próba D (zapis offline). */
export function HomePage() {
  return (
    <>
      <ServerStatus />
      <InstallStatus />
      <OfflineProbe />
    </>
  );
}

function ServerStatus() {
  const [elapsedMs, setElapsedMs] = useState<number | null>(null);
  const ping = useQuery({
    queryKey: ["healthz"],
    queryFn: async () => {
      const started = performance.now();
      const result = await api.get<{ status: string; version: string }>("/api/healthz");
      setElapsedMs(Math.round(performance.now() - started));
      return result;
    },
    gcTime: 0,
    staleTime: 0,
    retry: false,
  });

  return (
    <section className="card">
      <h2>Serwer</h2>
      {ping.isFetching ? (
        <p className="muted">Sprawdzam… (uśpiony serwer budzi się do minuty)</p>
      ) : ping.error ? (
        <p className="error">{ping.error.message}</p>
      ) : (
        <p>
          Działa, wersja {ping.data?.version}. Odpowiedź po <strong>{elapsedMs} ms</strong>.
        </p>
      )}
      <button type="button" onClick={() => ping.refetch()} disabled={ping.isFetching}>
        Sprawdź ponownie
      </button>
    </section>
  );
}

function InstallStatus() {
  const standalone =
    window.matchMedia("(display-mode: standalone)").matches ||
    (navigator as Navigator & { standalone?: boolean }).standalone === true;
  return (
    <section className="card">
      <h2>Instalacja</h2>
      {standalone ? (
        <p>Aplikacja działa z ekranu początkowego.</p>
      ) : (
        <p>
          Otwarta w przeglądarce. Na iPhonie: Safari → Udostępnij → „Do ekranu początkowego".
          Próby A, B i D wykonuj w zainstalowanej wersji.
        </p>
      )}
      {/* Po tej dacie widać, czy telefon ma już kod z ostatniego wdrożenia. */}
      <p className="muted">
        Wersja aplikacji: {new Date(BUILD_TIME).toLocaleString("pl-PL", VERSION_FORMAT)}
      </p>
    </section>
  );
}

function OfflineProbe() {
  const online = useSyncExternalStore(
    (notify) => onlineManager.subscribe(notify),
    () => onlineManager.isOnline(),
  );
  const probes = useQuery({ queryKey: ["probes"], queryFn: () => api.get<Probe[]>("/api/probe") });
  // Funkcja zapisu pochodzi z rejestru w lib/offline.ts, dzięki czemu działa po restarcie.
  const save = useMutation<Probe, Error, ProbeInput>({ mutationKey: mutationKeys.probe });
  const waiting = useMutationState({
    filters: { mutationKey: mutationKeys.probe, status: "pending" },
    select: (mutation) => mutation.state.variables as ProbeInput,
  });

  function addProbe() {
    save.mutate({
      id: crypto.randomUUID(),
      client_created_at: new Date().toISOString(),
      note: online ? "online" : "offline",
    });
  }

  return (
    <section className="card">
      <h2>Próba D: zapis offline</h2>
      <p className="muted">
        Tryb samolotowy → „Zapisz próbkę" → zamknij aplikację z przełącznika aplikacji → wyłącz
        tryb samolotowy → otwórz ponownie. Próbka ma się pojawić na liście poniżej.
      </p>
      <p>
        Połączenie z serwerem: <strong>{online ? "jest" : "brak"}</strong>. W kolejce:{" "}
        <strong>{waiting.length}</strong>.
      </p>
      <button type="button" className="primary" onClick={addProbe}>
        Zapisz próbkę
      </button>
      {save.error && <p className="error">{save.error.message}</p>}

      {waiting.length > 0 && (
        <ul className="list">
          {waiting.map((p) => (
            <li key={p.id}>
              <span>{formatTime(p.client_created_at)}</span>
              <span className="muted">czeka na wysłanie</span>
            </li>
          ))}
        </ul>
      )}
      <h3>Na serwerze</h3>
      {probes.data?.length ? (
        <ul className="list">
          {probes.data.map((p) => (
            <li key={p.id}>
              <span>
                {formatTime(p.client_created_at)} <span className="muted">({p.note})</span>
              </span>
              <span className="muted">dotarła {formatTime(p.received_at)}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted">Jeszcze nic.</p>
      )}
    </section>
  );
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString("pl-PL", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}
