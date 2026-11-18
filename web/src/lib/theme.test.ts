import { describe, expect, it } from "vitest";
import { parseTheme } from "./theme";

describe("parseTheme", () => {
  it("przyjmuje tylko znane wybory", () => {
    expect(parseTheme("dark")).toBe("dark");
    expect(parseTheme("light")).toBe("light");
  });

  it("brak albo śmieci w pamięci to wybór automatyczny", () => {
    expect(parseTheme(null)).toBe("auto");
    expect(parseTheme(undefined)).toBe("auto");
    expect(parseTheme("auto")).toBe("auto");
    expect(parseTheme("niebieski")).toBe("auto");
  });
});
