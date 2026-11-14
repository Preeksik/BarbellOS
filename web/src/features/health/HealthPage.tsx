import { useQuery } from "@tanstack/react-query";
import { type HealthTypeSummary, api } from "../../lib/api";

// Nazwa musi być identyczna z nazwą skrótu w aplikacji Skróty (shortcuts/README.md).
const SHORTCUT_NAME = "BarbellOS Sync";
const SHORTCUT_URL = `shortcuts://run-shortcut?name=${encodeURIComponent(SHORTCUT_NAME)}`;

const TYPE_LABELS: Record<string, string> = {
  weight: "Masa ciała",
  body_fat: "Tkanka tłuszczowa",
  steps: "Kroki",
  active_energy: "Energia aktywna",
  sleep: "Sen",
  hrv: "HRV",
  resting_hr: "Tętno spoczynkowe",
  heart_rate: "Tętno",
  spo2: "SpO2",
};

/** Próba B: co i kiedy dotarło z Apple Health przez automatyzację Skrótów. */
export function HealthPage() {
  const summary = useQuery({
    queryKey: ["health-summary"],
    queryFn: () => api.get<HealthTypeSummary[]>("/api/health/summary"),
  });

  return (
    <section className="card">
      <h2>Dane z Apple Health</h2>
      <p className="muted">
        Dane wysyła skrót „{SHORTCUT_NAME}". Instrukcja budowy skrótu jest w repozytorium,
        w pliku shortcuts/README.md.
      </p>
      <div className="row">
        <a className="button primary" href={SHORTCUT_URL}>
          Uruchom skrót
        </a>
        <button type="button" onClick={() => summary.refetch()} disabled={summary.isFetching}>
          Odśwież
        </button>
      </div>

      {summary.error && <p className="error">{summary.error.message}</p>}
      {summary.data?.length === 0 && <p className="muted">Serwer nie dostał jeszcze żadnych danych.</p>}
      {summary.data && summary.data.length > 0 && (
        <table>
          <thead>
            <tr>
              <th scope="col">Typ</th>
              <th scope="col">Próbek</th>
              <th scope="col">Ostatnia</th>
              <th scope="col">Źródło</th>
            </tr>
          </thead>
          <tbody>
            {summary.data.map((row) => (
              <tr key={row.type}>
                <th scope="row">{TYPE_LABELS[row.type] ?? row.type}</th>
                <td>{row.count}</td>
                <td>
                  {row.last_value ?? row.last_label ?? "–"} {row.unit ?? ""}
                  <br />
                  <span className="muted">{formatDate(row.last_starts_at)}</span>
                </td>
                <td>{row.source}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

function formatDate(iso: string | null): string {
  if (!iso) return "";
  return new Date(iso).toLocaleString("pl-PL", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}
