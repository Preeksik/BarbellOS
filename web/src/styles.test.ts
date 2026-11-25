import { describe, expect, it } from "vitest";
import css from "./styles.css?raw";

// Regresja z 26.11.2026: style treningu definiowały globalne `.plates` (rząd talerzy),
// a Dieta ma `goals plates` (paski B/W/T). Ekran Diety się rozjechał. Style nowego ekranu
// nie mogą nadpisywać klas, których używa inny ekran.

const TRAINING_MARKER = "/* ---------- etap 4: trening";

// Klasy wspólne celowo (karty, pola, stany przycisków), w treningu zawsze z inną klasą.
const SHARED = new Set([
  "card",
  "muted",
  "error",
  "link",
  "chips",
  "daynav",
  "status",
  "ok",
  "on",
  "sel",
  "done",
  "active",
  "full",
  "now",
]);

const sources = import.meta.glob("./**/*.tsx", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

/** Nazwy klas z atrybutów `className` (dosłowne teksty, także w warunkach i szablonach). */
function classNamesIn(source: string): Set<string> {
  const names = new Set<string>();
  for (const match of source.matchAll(/className=(?:"([^"]*)"|\{([^}]*)\})/g)) {
    const raw = match[1] ?? match[2] ?? "";
    const literals = match[1] != null ? [raw] : [...raw.matchAll(/["'`]([^"'`]*)["'`]/g)].map((m) => m[1]);
    for (const literal of literals) {
      for (const token of literal.replace(/\$\{[^}]*\}?/g, " ").split(/\s+/)) {
        if (/^[a-z][\w-]*$/i.test(token)) names.add(token);
      }
    }
  }
  return names;
}

describe("style ekranu treningu", () => {
  it("nie nadpisują klas używanych na innych ekranach", () => {
    const start = css.indexOf(TRAINING_MARKER);
    expect(start).toBeGreaterThan(0);
    // Tylko selektory (przed „{"), bez wartości właściwości.
    const selectors = css
      .slice(start)
      .replace(/\/\*[\s\S]*?\*\//g, "")
      .split("}")
      .map((block) => block.split("{")[0]);
    const trainingClasses = new Set(
      selectors.flatMap((s) => [...s.matchAll(/\.([a-z][\w-]*)/gi)].map((m) => m[1])),
    );
    const elsewhere = new Set<string>();
    for (const [path, source] of Object.entries(sources)) {
      if (path.includes("/features/training/")) continue;
      for (const name of classNamesIn(source)) elsewhere.add(name);
    }
    const clashes = [...trainingClasses].filter((c) => elsewhere.has(c) && !SHARED.has(c));
    expect(clashes).toEqual([]);
  });
});
