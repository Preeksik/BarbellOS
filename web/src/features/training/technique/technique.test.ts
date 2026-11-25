import { describe, expect, it } from "vitest";
import { cycleMs, moveFor, progressAt } from "./moves";
import { BODY, MIDFOOT_X, PLATE_RADIUS, benchPose, dist, hingePose, squatPose, twoBone, vec } from "./skeleton";

const STEPS = [0, 0.1, 0.25, 0.4, 0.5, 0.6, 0.75, 0.9, 1];

describe("mechanika ludzika", () => {
  it("staw pośredni trzyma długości kości, a za daleki cel prostuje ramię", () => {
    const a = vec(0, 0);
    const target = vec(30, 40);
    const mid = twoBone(a, target, 30, 33, 1);
    expect(dist(a, mid)).toBeCloseTo(30);
    expect(dist(mid, target)).toBeCloseTo(33);
    const straight = twoBone(a, vec(200, 0), 30, 33, 1);
    expect(straight.x).toBeCloseTo(30);
    expect(straight.y).toBeCloseTo(0, 1);
  });

  it("przysiad: stałe kości, sztanga nad środkiem stopy, biodro poniżej kolana na dole", () => {
    for (const p of STEPS) {
      const pose = squatPose(p);
      expect(dist(pose.ankle, pose.knee)).toBeCloseTo(BODY.shin);
      expect(dist(pose.knee, pose.hip)).toBeCloseTo(BODY.thigh);
      expect(dist(pose.hip, pose.shoulder)).toBeCloseTo(BODY.torso);
      expect(pose.bar?.x).toBeCloseTo(MIDFOOT_X, 0);
    }
    const bottom = squatPose(1);
    expect(bottom.hip.y).toBeLessThan(bottom.knee.y);
    expect(bottom.knee.x).toBeGreaterThan(bottom.ankle.x); // kolana do przodu
  });

  it("martwy ciąg: sztanga pionowo nad stopą, od podłogi do wyprostu", () => {
    const move = moveFor("Martwy ciąg");
    expect(move).not.toBeNull();
    const xs = STEPS.map((p) => move?.pose(p).bar?.x ?? 0);
    expect(new Set(xs.map((x) => x.toFixed(3))).size).toBe(1);
    expect(move?.pose(0).bar?.y).toBeCloseTo(PLATE_RADIUS); // talerze na podłodze
    const top = move?.pose(1);
    expect(top && Math.abs(top.hip.x - top.knee.x)).toBeLessThan(6); // wyprost bioder
    for (const p of STEPS) {
      const pose = move?.pose(p) ?? hingePose(30, 10);
      expect(dist(pose.knee, pose.hip)).toBeCloseTo(BODY.thigh);
      expect(dist(pose.hip, pose.shoulder)).toBeCloseTo(BODY.torso);
      expect(pose.hip.x).toBeLessThan(pose.knee.x + 6); // biodro z tyłu, nie przed kolanami
    }
  });

  it("ława: sztanga na klatce w dole, spoto zatrzymuje ją wyżej, łokieć pod sztangą", () => {
    const touch = benchPose(1);
    const spoto = benchPose(1, { stopAbove: 3 });
    expect(spoto.bar?.y ?? 0).toBeGreaterThan(touch.bar?.y ?? 0);
    expect(dist(touch.shoulder, touch.elbow)).toBeCloseTo(BODY.upperArm);
    expect(touch.elbow.y).toBeLessThan(touch.hand.y);
    const legs = benchPose(0);
    expect(legs.knee.y).toBeGreaterThan(legs.ankle.y + 30); // kolano w górze, stopy na podłodze
    const larsen = benchPose(0, { legsUp: true });
    expect(larsen.ankle.y).toBeGreaterThan(30); // nogi w powietrzu
  });
});

describe("przebieg ruchu", () => {
  it("pauza trzyma pozycję, a pętla wraca do startu", () => {
    const move = moveFor("Przysiad z pauzą 2 s");
    if (!move) throw new Error("brak ruchu");
    // 700 ms stania, 1600 ms w dół, potem 2 s pauzy.
    expect(progressAt(move, 300)).toEqual({ progress: 0, label: null });
    expect(progressAt(move, 1500).progress).toBeCloseTo(0.5);
    expect(progressAt(move, 1500).label).toBe("w dół");
    expect(progressAt(move, 3300)).toEqual({ progress: 1, label: "pauza 2 s" });
    expect(cycleMs(move)).toBe(5500);
    expect(progressAt(move, 5500 + 300).progress).toBe(0);
  });

  it("każdy bój ze sztangą z planu ma animację, akcesoria jeszcze nie", () => {
    for (const name of [
      "Przysiad",
      "Przysiad z pauzą 2 s",
      "Przysiad tempo 3-1-0",
      "Przysiad z pinów",
      "Wyciskanie leżąc (pauza)",
      "Wyciskanie leżąc T&G",
      "Wyciskanie z pauzą 3 s",
      "Larsen press",
      "Spoto press",
      "Wyciskanie wąskim chwytem",
      "Martwy ciąg",
      "Martwy ciąg z pauzą pod kolanem",
      "Rumuński martwy ciąg (RDL)",
    ]) {
      expect(moveFor(name), name).not.toBeNull();
    }
    expect(moveFor("Face pull")).toBeNull();
  });
});
