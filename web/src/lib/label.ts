/**
 * Zdjęcie etykiety -> szkic wartości do formularza produktu (etap 1, krok 3).
 *
 * Odczyt robi serwer (model AI przepisuje tabelę, kod sprawdza zakresy). Telefon tylko
 * zmniejsza zdjęcie przed wysyłką i wpisuje wynik w pola formularza. Nic nie zapisuje się
 * bez zatwierdzenia przez użytkownika.
 */

import { type LabelDraft, type MacroKey, api } from "./api";
import { formatDecimal } from "./number";

/** Dłuższy bok wysyłanego zdjęcia. Tabela zostaje czytelna, a plik ma kilkaset kB. */
export const LABEL_MAX_EDGE = 2000;
const JPEG_QUALITY = 0.85;

/** Wymiary po zmniejszeniu z zachowaniem proporcji. Małych zdjęć nie powiększamy. */
export function fitWithin(
  width: number,
  height: number,
  maxEdge: number,
): { width: number; height: number } {
  const scale = Math.min(1, maxEdge / Math.max(width, height));
  return {
    width: Math.max(1, Math.round(width * scale)),
    height: Math.max(1, Math.round(height * scale)),
  };
}

/** Wartości, które model odczytał z etykiety (w kolejności pól formularza). */
export function labelKeys(draft: LabelDraft, order: readonly MacroKey[]): MacroKey[] {
  return order.filter((key) => draft.per_100[key] != null);
}

/**
 * Wpisuje odczytane wartości w pola formularza. Pole, którego model nie odczytał,
 * zostaje bez zmian: brak odczytu nie kasuje tego, co już było wpisane.
 */
export function applyLabelDraft(
  texts: Record<MacroKey, string>,
  draft: LabelDraft,
): Record<MacroKey, string> {
  const next = { ...texts };
  for (const key of Object.keys(next) as MacroKey[]) {
    const value = draft.per_100[key];
    if (value != null) next[key] = formatDecimal(value);
  }
  return next;
}

/**
 * Zmniejsza zdjęcie z aparatu (kilka MB) do JPEG-a o boku najwyżej LABEL_MAX_EDGE.
 * Gdy przeglądarka nie potrafi go przetworzyć, wysyłamy oryginał: limit jest na serwerze.
 */
export async function shrinkPhoto(file: Blob): Promise<Blob> {
  const url = URL.createObjectURL(file);
  try {
    const image = new Image();
    image.src = url;
    await image.decode();
    const size = fitWithin(image.naturalWidth, image.naturalHeight, LABEL_MAX_EDGE);
    const canvas = document.createElement("canvas");
    canvas.width = size.width;
    canvas.height = size.height;
    const context = canvas.getContext("2d");
    if (!context) return file;
    context.drawImage(image, 0, 0, size.width, size.height);
    const shrunk = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob(resolve, "image/jpeg", JPEG_QUALITY),
    );
    return shrunk && shrunk.size < file.size ? shrunk : file;
  } catch {
    return file;
  } finally {
    URL.revokeObjectURL(url);
  }
}

/** Wysyła zdjęcie etykiety i zwraca szkic. Wymaga sieci: funkcje AI nie trafiają do kolejki. */
export async function readLabel(file: Blob): Promise<LabelDraft> {
  return api.post<LabelDraft>("/api/foods/label", await shrinkPhoto(file));
}
