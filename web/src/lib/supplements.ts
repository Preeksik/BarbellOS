/**
 * Suplementacja po stronie telefonu (23.11.2026): tylko podgląd zmian czekających w kolejce
 * offline. Stan po zapisie (seria dni, tydzień) liczy serwer (`backend/app/core/supplements.py`).
 */

import type { SupplementDay } from "./api";

/** Lista wziętych po stuknięciu w suplement: dodaje albo usuwa, w kolejności listy. */
export function toggled(day: SupplementDay, id: string): string[] {
  const taken = new Set(day.taken_ids);
  if (taken.has(id)) taken.delete(id);
  else taken.add(id);
  return day.supplements.map((s) => s.id).filter((sid) => taken.has(sid));
}

/** Podgląd „To co wczoraj": dzisiejsze plus wczorajsze, niczego nie odznacza. */
export function likeYesterday(day: SupplementDay): string[] {
  const chosen = new Set([...day.taken_ids, ...day.yesterday_ids]);
  return day.supplements.map((s) => s.id).filter((sid) => chosen.has(sid));
}

/** Ile suplementów doda „To co wczoraj". */
export function yesterdayGain(day: SupplementDay): number {
  const taken = new Set(day.taken_ids);
  return day.yesterday_ids.filter((id) => !taken.has(id)).length;
}

/** Dzień z nowym stanem odhaczeń (do podglądu, zanim odpowie serwer). */
export function withTaken(day: SupplementDay, takenIds: string[]): SupplementDay {
  const taken = new Set(takenIds);
  return {
    ...day,
    taken_ids: day.supplements.map((s) => s.id).filter((id) => taken.has(id)),
    supplements: day.supplements.map((s) => ({ ...s, taken: taken.has(s.id) })),
  };
}
