import { useQuery } from "@tanstack/react-query";
import { type ChangeEvent, type FormEvent, useEffect, useRef, useState } from "react";
import { type Food, api } from "../../lib/api";
import { isValidEan } from "../../lib/ean";
import { decodeImageFile, decodeVideoFrame } from "../../lib/scanner";

const SCAN_INTERVAL_MS = 200;

const MACRO_ROWS: [string, string, string][] = [
  ["kcal", "Energia", "kcal"],
  ["protein_g", "Białko", "g"],
  ["fat_g", "Tłuszcz", "g"],
  ["sat_fat_g", "w tym nasycone", "g"],
  ["carbs_g", "Węglowodany", "g"],
  ["sugars_g", "w tym cukry", "g"],
  ["fiber_g", "Błonnik", "g"],
  ["salt_g", "Sól", "g"],
];

/** Próba A: skan kodu kreskowego w zainstalowanej PWA, potem produkt z bazy lub z OFF. */
export function ScanPage() {
  const [barcode, setBarcode] = useState<string | null>(null);
  return barcode ? (
    <FoodResult barcode={barcode} onAgain={() => setBarcode(null)} />
  ) : (
    <Scanner onDetected={setBarcode} />
  );
}

function Scanner({ onDetected }: { onDetected: (barcode: string) => void }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [active, setActive] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [manual, setManual] = useState("");

  useEffect(() => {
    if (!active) return;
    let stream: MediaStream | undefined;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let cancelled = false;

    async function tick() {
      if (cancelled || !videoRef.current || !canvasRef.current) return;
      try {
        const code = await decodeVideoFrame(videoRef.current, canvasRef.current);
        if (code && !cancelled) return onDetected(code);
      } catch (error) {
        setMessage(`Błąd czytnika: ${String(error)}`);
      }
      timer = setTimeout(tick, SCAN_INTERVAL_MS);
    }

    navigator.mediaDevices
      .getUserMedia({ video: { facingMode: { ideal: "environment" } }, audio: false })
      .then(async (s) => {
        if (cancelled) return s.getTracks().forEach((t) => t.stop());
        stream = s;
        const video = videoRef.current!;
        video.srcObject = s;
        await video.play();
        tick();
      })
      .catch((error: Error) => {
        setMessage(`Brak dostępu do kamery (${error.name}). Użyj zdjęcia albo wpisz kod.`);
        setActive(false);
      });

    return () => {
      cancelled = true;
      clearTimeout(timer);
      stream?.getTracks().forEach((t) => t.stop());
    };
  }, [active, onDetected]);

  async function onPhoto(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    const code = await decodeImageFile(file);
    if (code) onDetected(code);
    else setMessage("Nie znalazłem kodu na zdjęciu. Zbliż aparat i spróbuj ponownie.");
  }

  function onManual(event: FormEvent) {
    event.preventDefault();
    if (isValidEan(manual)) onDetected(manual);
    else setMessage("To nie jest poprawny kod EAN (błędna cyfra kontrolna lub długość).");
  }

  return (
    <section className="card">
      <h2>Skan kodu</h2>
      {active ? (
        <>
          {/* playsInline i muted są wymagane, żeby iOS nie otworzył podglądu na pełnym ekranie */}
          <video ref={videoRef} className="viewfinder" playsInline muted />
          <canvas ref={canvasRef} hidden />
          <button type="button" onClick={() => setActive(false)}>
            Zatrzymaj kamerę
          </button>
        </>
      ) : (
        <button type="button" className="primary" onClick={() => setActive(true)}>
          Włącz kamerę
        </button>
      )}

      <label className="file">
        Zrób zdjęcie kodu
        <input type="file" accept="image/*" capture="environment" onChange={onPhoto} />
      </label>

      <form className="row" onSubmit={onManual}>
        <input
          inputMode="numeric"
          placeholder="albo wpisz kod EAN"
          value={manual}
          onChange={(e) => setManual(e.target.value.trim())}
        />
        <button type="submit" disabled={!manual}>
          Szukaj
        </button>
      </form>
      {message && <p className="error">{message}</p>}
    </section>
  );
}

function FoodResult({ barcode, onAgain }: { barcode: string; onAgain: () => void }) {
  const food = useQuery({
    queryKey: ["food", barcode],
    queryFn: () => api.get<Food>(`/api/foods/barcode/${barcode}`),
    retry: false,
    staleTime: Number.POSITIVE_INFINITY,
  });

  return (
    <section className="card">
      <h2>{food.data?.name ?? barcode}</h2>
      <p className="muted">
        {food.data?.brand ? `${food.data.brand} · ` : ""}EAN {barcode}
      </p>
      {food.isPending && <p className="muted">Szukam produktu…</p>}
      {food.error && <p className="error">{food.error.message}</p>}
      {food.data && (
        <>
          <table>
            <caption>Wartości na 100 g</caption>
            <tbody>
              {MACRO_ROWS.map(([key, label, unit]) => {
                const value = food.data.per_100g[key];
                return (
                  <tr key={key}>
                    <th scope="row">{label}</th>
                    <td>{value == null ? "brak danych" : `${formatNumber(value)} ${unit}`}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <p className="muted">
            Źródło: {food.data.cached ? "własna baza" : "Open Food Facts (zapisano w bazie)"}.
            Mikroskładniki z etykiety: {food.data.micros.length}.
          </p>
        </>
      )}
      <button type="button" className="primary" onClick={onAgain}>
        Skanuj kolejny
      </button>
    </section>
  );
}

function formatNumber(value: number): string {
  return value.toLocaleString("pl-PL", { maximumFractionDigits: 1 });
}
