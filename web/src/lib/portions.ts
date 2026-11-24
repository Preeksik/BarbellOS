/**
 * Liczba porcji przy dodawaniu produktu (24.11.2026): „6 kromek po 23 g" zamiast liczenia
 * gramów w głowie. Do dziennika i tak trafia ilość w gramach, więc to tylko przeliczenie
 * pola formularza, nie logika żywieniowa.
 */

/** Ile porcji to dana ilość, np. 138 g przy porcji 23 g = 6. Do dwóch miejsc po przecinku. */
export function portionsOf(amount: number, serving: number): number {
  return Math.round((amount / serving) * 100) / 100;
}

/** Ilość dla liczby porcji, np. 6 × 23 g = 138 g. Do jednego miejsca po przecinku. */
export function amountOf(portions: number, serving: number): number {
  return Math.round(portions * serving * 10) / 10;
}

/**
 * Przycisk − albo + przy liczbie porcji. Z ułamka przechodzi do najbliższej całej porcji
 * w tę stronę (2,4 → 3 albo 2), a nie schodzi poniżej jednej.
 */
export function stepPortions(current: number | null, delta: 1 | -1): number {
  if (current == null || current <= 0) return 1;
  const whole = Math.abs(current - Math.round(current)) < 0.01;
  const next = whole
    ? Math.round(current) + delta
    : delta > 0
      ? Math.ceil(current)
      : Math.floor(current);
  return Math.max(1, next);
}
