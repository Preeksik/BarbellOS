/**
 * Mikroskładniki na ekranie (etap 6): źródła wartości i opis pokrycia normy.
 * Liczby (średnie, procent normy, udziały źródeł) liczy serwer (`core/week.py`).
 */

import type { MicroWeek } from "./api";

export const SOURCE_LABELS: Record<string, string> = {
  label: "etykieta",
  user: "Twoje",
  reference: "tabela USDA",
  estimated: "szacunek",
};

/** Liczba w polskim zapisie z sensowną dokładnością (µg potrafi być ułamkiem). */
export function formatAmount(value: number): string {
  const digits = value >= 100 ? 0 : value >= 10 ? 1 : 2;
  return value.toLocaleString("pl-PL", { maximumFractionDigits: digits });
}

export function percent(share: number): string {
  return `${Math.round(share * 100)}%`;
}

/**
 * Czy pokryciu można ufać. Gdy większość kalorii tygodnia nie ma danych o składniku,
 * procent normy jest zaniżony i nie mówi nic o niedoborze.
 */
export function coverageState(m: MicroWeek): "low-data" | "low" | "ok" {
  if (m.share_missing > 0.5) return "low-data";
  if (m.percent_rda != null && m.percent_rda < 50 && m.nutrient_id !== "sodium") return "low";
  return "ok";
}

/** Opis pochodzenia danych, np. „z tabel 70% · szacunek 15% · brak 15%". */
export function trustText(m: MicroWeek): string {
  const parts = [`z tabel/etykiet ${percent(m.share_trusted)}`];
  if (m.share_estimated > 0.005) parts.push(`szacunek ${percent(m.share_estimated)}`);
  if (m.share_missing > 0.005) parts.push(`brak ${percent(m.share_missing)}`);
  return parts.join(" · ");
}
