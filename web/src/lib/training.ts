/**
 * Formatowanie ekranu treningu (etap 4). Liczby (ciężary, e1RM, statusy) przychodzą
 * z serwera; tu jest tylko zamiana na tekst i zebranie wpisu z pól formularza.
 */

import type { TrainingEntry, TrainingExercise } from "./api";
import { INVALID, parseDecimal } from "./number";

const WEEKDAYS = ["Nd", "Pon", "Wt", "Śr", "Czw", "Pt", "Sob"];
const WEEKDAYS_FULL = ["niedziela", "poniedziałek", "wtorek", "środa", "czwartek", "piątek", "sobota"];

/** Liczba po polsku: najwyżej dwa miejsca po przecinku, brak jako „–". */
export function fmt(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return "–";
  return String(Math.round(value * 100) / 100).replace(".", ",");
}

/** RPE z planu bywa zakresem: „8.5-9" → „8,5–9". */
export function rpeText(rpe: string): string {
  return rpe.replace(/\./g, ",").replace("-", "–");
}

function parseIsoDay(iso: string): Date {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d);
}

/** „Pon 2.11" na przyciskach dni. */
export function shortDay(iso: string): string {
  const d = parseIsoDay(iso);
  return `${WEEKDAYS[d.getDay()]} ${d.getDate()}.${String(d.getMonth() + 1).padStart(2, "0")}`;
}

/** „2.11" */
export function dayMonth(iso: string): string {
  const d = parseIsoDay(iso);
  return `${d.getDate()}.${String(d.getMonth() + 1).padStart(2, "0")}`;
}

/** „poniedziałek 2.11.2026" w nagłówku sesji. */
export function longDay(iso: string): string {
  const d = parseIsoDay(iso);
  return `${WEEKDAYS_FULL[d.getDay()]} ${dayMonth(iso)}.${d.getFullYear()}`;
}

/** Kod dnia na przycisku: D1…D5 bez zmian, dni specjalne słowem. */
export function dayCodeLabel(code: string): string {
  return ({ TEST: "TEST", OPT: "opcja", AMP: "AMP" } as Record<string, string>)[code] ?? code;
}

function hintText(hint: string): string {
  const value = hint.replace(".", ",");
  return value.startsWith("+") ? `obciążenie ${value} kg` : `ok. ${value} kg`;
}

/** Zalecenie z planu, np. „4 × 4 · 78% TM · RPE 7" albo „3 × 10/str. · ok. 20 kg". */
export function prescription(ex: TrainingExercise): string {
  const rpe = ex.rpe ? rpeText(ex.rpe) : null;
  if (ex.kind === "single") return `1 × 1 · single do RPE ${rpe ?? "–"}`;
  if (ex.kind === "sets") {
    return `${ex.sets ?? "–"} × ${ex.reps ?? "–"} · ${fmt(ex.percent_tm)}% TM · RPE ${rpe ?? "–"}`;
  }
  if (ex.kind === "att") return `${ex.attempt ?? "–"}. podejście`;
  const parts = [`${ex.sets ?? "–"} × ${ex.reps ?? "–"}`];
  if (rpe) parts.push(`RPE ${rpe}`);
  if (ex.weight_hint) parts.push(hintText(ex.weight_hint));
  return parts.join(" · ");
}

export function tierLabel(tier: TrainingExercise["tier"]): string | null {
  return tier === "main" ? "bój" : tier === "var" ? "wariant" : null;
}

/** Podpowiedź w polu powtórzeń: liczba z planu (akcesoria: początek tekstu, np. „8-12"). */
export function repsPlaceholder(ex: TrainingExercise): string {
  if (ex.kind === "sets") return ex.reps ?? "";
  if (ex.kind === "acc") return (ex.reps ?? "").match(/^[0-9–-]+/)?.[0] ?? "";
  return "";
}

/** Podpowiedź w polu kg: ciężar z planu albo startowy ciężar akcesorium. */
export function kgPlaceholder(ex: TrainingExercise): string {
  if (ex.load != null) return fmt(ex.load);
  return ex.weight_hint ? ex.weight_hint.replace(".", ",") : "";
}

export interface EntryTexts {
  kg: string;
  reps: string;
  rpe: string;
}

export function entryTexts(entry: TrainingEntry): EntryTexts {
  const text = (v: number | null) => (v == null ? "" : fmt(v));
  return { kg: text(entry.kg), reps: text(entry.reps), rpe: text(entry.rpe) };
}

/**
 * Wpis z pól formularza. Błędna liczba albo wartość spoza zakresu daje `null`
 * (nic nie wysyłamy, pole pokazuje błąd), puste pole to brak wartości.
 */
export function entryFromTexts(texts: EntryTexts, base: TrainingEntry): TrainingEntry | null {
  const kg = parseDecimal(texts.kg);
  const reps = parseDecimal(texts.reps);
  const rpe = parseDecimal(texts.rpe);
  if (kg === INVALID || reps === INVALID || rpe === INVALID) return null;
  if ((kg ?? 0) > 1000 || (reps ?? 0) > 1000 || (rpe ?? 0) > 10) return null;
  return { ...base, kg, reps, rpe };
}

/**
 * Odhaczenie: serie bez wpisanego ciężaru dostają ciężar z planu (jak w starym pliku),
 * żeby zrobiona seria zgodnie z planem nie wymagała pisania.
 */
export function toggledDone(entry: TrainingEntry, ex: TrainingExercise): TrainingEntry {
  if (entry.done) return { ...entry, done: false };
  const kg = entry.kg == null && ex.kind === "sets" && ex.load != null ? ex.load : entry.kg;
  return { ...entry, done: true, kg };
}

/** Ocena podejścia: drugie stuknięcie tej samej oceny ją zdejmuje. */
export function toggledOk(entry: TrainingEntry, value: "y" | "n"): TrainingEntry {
  return { ...entry, ok: entry.ok === value ? null : value };
}

/** Tekst talerzy na stronę: „25+25+2,5 /str.", pusta sztanga albo nic. */
export function platesText(plates: number[] | null): string | null {
  if (plates == null) return null;
  if (plates.length === 0) return "pusta sztanga";
  return `${plates.map(fmt).join("+")} /str.`;
}

/** „dzień" / „dni" */
export function daysWord(n: number): string {
  return n === 1 ? "dzień" : "dni";
}
