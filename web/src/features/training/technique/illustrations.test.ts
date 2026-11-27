import { describe, expect, it } from "vitest";
import { cycleLength, frameAt, illustrationFor, videoCountdown } from "./illustrations";

describe("ilustracje z klatek", () => {
  it("przysiad przełącza górę i dół z krótkim przejściem", () => {
    const ill = illustrationFor("Przysiad");
    if (!ill) throw new Error("brak ilustracji");
    expect(ill.frames).toEqual(["/technique/przysiad-1.webp", "/technique/przysiad-2.webp"]);
    expect(cycleLength(ill)).toBe(300 + 1100 + 300 + 900);
    // W połowie przejścia do góry klatka dolna jeszcze prześwituje.
    expect(frameAt(ill, 150)).toMatchObject({ frame: 0, previous: 1, opacity: 0.5, label: "góra" });
    expect(frameAt(ill, 1000)).toMatchObject({ frame: 0, opacity: 1, countdown: null });
    expect(frameAt(ill, 1400 + 300 + 100)).toMatchObject({ frame: 1, opacity: 1, label: "dół" });
    // Pętla wraca na początek.
    expect(frameAt(ill, cycleLength(ill) + 150).opacity).toBe(0.5);
  });

  it("pauza 2 s odlicza na dolnej klatce", () => {
    const ill = illustrationFor("Przysiad z pauzą 2 s");
    if (!ill) throw new Error("brak ilustracji");
    const bottom = 300 + 1100 + 300;
    expect(frameAt(ill, bottom + 100)).toMatchObject({ frame: 1, label: "pauza", countdown: 2 });
    expect(frameAt(ill, bottom + 1500)).toMatchObject({ frame: 1, countdown: 1 });
  });

  it("tempo 3-1-0: wolne zejście z odliczaniem i sekunda pauzy", () => {
    const ill = illustrationFor("Przysiad tempo 3-1-0");
    if (!ill) throw new Error("brak ilustracji");
    const down = 300 + 900;
    expect(frameAt(ill, down + 500)).toMatchObject({
      frame: 1,
      label: "3 s w dół",
      countdown: 3,
      moving: true,
    });
    expect(frameAt(ill, down + 3000 + 200)).toMatchObject({ label: "pauza", countdown: 1, moving: false });
  });

  it("ćwiczenia bez klatek zostają przy ludziku", () => {
    expect(illustrationFor("Face pull")).toBeNull();
  });
});

describe("film ruchu", () => {
  it("warianty przysiadu korzystają z jednego filmu z innym przebiegiem", () => {
    const plain = illustrationFor("Przysiad")?.video;
    const pause = illustrationFor("Przysiad z pauzą 2 s")?.video;
    const tempo = illustrationFor("Przysiad tempo 3-1-0")?.video;
    expect(plain?.src).toBe("/technique/przysiad.mp4");
    expect(pause?.src).toBe(plain?.src);
    expect(pause?.steps[1]).toEqual({ kind: "hold", ms: 2000, label: "pauza", countdown: true });
    // Tempo: zejście w normalnej prędkości trwa dokładnie 3 s, wstanie szybko.
    expect(tempo?.steps[0]).toMatchObject({ kind: "play", to: 3, rate: 1 });
    expect(tempo?.steps[2]).toMatchObject({ kind: "play", to: 6, rate: 3 });
  });

  it("odlicza pozostałe sekundy zejścia i pauzy", () => {
    const down = { kind: "play" as const, to: 3, rate: 1, label: "3 s w dół", countdown: true };
    expect(videoCountdown(down, 0.2, 0)).toBe(3);
    expect(videoCountdown(down, 2.5, 0)).toBe(1);
    const hold = { kind: "hold" as const, ms: 2000, label: "pauza", countdown: true };
    expect(videoCountdown(hold, 3, 100)).toBe(2);
    expect(videoCountdown(hold, 3, 1500)).toBe(1);
    expect(videoCountdown({ kind: "hold", ms: 300, label: "dół" }, 3, 0)).toBeNull();
  });
});
