import { type ChangeEvent, type FormEvent, useEffect, useRef, useState } from "react";
import { isValidEan } from "../../lib/ean";
import { decodeImageFile, decodeVideoFrame } from "../../lib/scanner";
import { FoodCard } from "./FoodCard";

const SCAN_INTERVAL_MS = 200;

/** Skan kodu kreskowego, potem karta produktu (własna baza albo Open Food Facts). */
export function ScanPage({ day, onShowDiary }: { day: string; onShowDiary: () => void }) {
  const [barcode, setBarcode] = useState<string | null>(null);
  return barcode ? (
    // `key`: kolejny skan zaczyna od czystej karty (bez „Dodano" z poprzedniego produktu).
    <FoodCard
      key={barcode}
      barcode={barcode}
      day={day}
      onAgain={() => setBarcode(null)}
      onShowDiary={onShowDiary}
    />
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
