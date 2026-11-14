/** Cyfra kontrolna GS1 dla EAN-8, UPC-A, EAN-13 i GTIN-14. Ta sama reguła co w backendzie. */
export function isValidEan(code: string): boolean {
  if (!/^\d+$/.test(code) || ![8, 12, 13, 14].includes(code.length)) return false;
  const digits = [...code].map(Number);
  const check = digits.pop()!;
  const total = digits.reverse().reduce((sum, d, i) => sum + d * (i % 2 === 0 ? 3 : 1), 0);
  return (10 - (total % 10)) % 10 === check;
}
