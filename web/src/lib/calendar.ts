/**
 * Mini-kalendarz do kopiowania posiłku z innego dnia (22.11.2026). Tylko układ siatki
 * i podpisy; które dni mają wpisy, mówi serwer (`GET /api/diary/month/{RRRR-MM}`).
 */

/** Miesiąc dnia „RRRR-MM-DD" w postaci „RRRR-MM". */
export function monthOf(isoDay: string): string {
  return isoDay.slice(0, 7);
}

/** Miesiąc przesunięty o `delta` (np. -1: poprzedni). */
export function shiftMonth(month: string, delta: number): string {
  const [year, number] = month.split("-").map(Number);
  const index = year * 12 + (number - 1) + delta;
  return `${Math.floor(index / 12)}-${String((index % 12) + 1).padStart(2, "0")}`;
}

/**
 * Tygodnie miesiąca od poniedziałku. Każdy tydzień ma 7 pól: dzień „RRRR-MM-DD" albo null
 * (pole przed pierwszym albo po ostatnim dniu miesiąca).
 */
export function monthGrid(month: string): (string | null)[][] {
  const [year, number] = month.split("-").map(Number);
  const daysInMonth = new Date(Date.UTC(year, number, 0)).getUTCDate();
  const firstWeekday = (new Date(Date.UTC(year, number - 1, 1)).getUTCDay() + 6) % 7; // pon = 0
  const cells: (string | null)[] = Array(firstWeekday).fill(null);
  for (let day = 1; day <= daysInMonth; day++) {
    cells.push(`${month}-${String(day).padStart(2, "0")}`);
  }
  while (cells.length % 7 !== 0) cells.push(null);
  const weeks: (string | null)[][] = [];
  for (let i = 0; i < cells.length; i += 7) weeks.push(cells.slice(i, i + 7));
  return weeks;
}

/** „listopad 2026". */
export function monthLabel(month: string): string {
  const [year, number] = month.split("-").map(Number);
  return new Date(Date.UTC(year, number - 1, 1)).toLocaleDateString("pl-PL", {
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });
}

export const WEEKDAYS = ["pon", "wt", "śr", "czw", "pt", "sob", "nd"];
