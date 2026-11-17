import { describe, expect, it } from "vitest";
import { GOAL_ROWS, progress, progressText } from "./targets";

describe("progress", () => {
  it("cel (kalorie): poniżej, osiągnięty, przekroczony", () => {
    expect(progress(2150, 2800, "target")).toEqual({ fill: 2150 / 2800, state: "under", left: 650 });
    expect(progress(2800, 2800, "target").state).toBe("done");
    const over = progress(2920, 2800, "target");
    expect(over).toEqual({ fill: 1, state: "over", left: -120 });
  });

  it("co najmniej (białko): przekroczenie nie jest problemem", () => {
    expect(progress(120, 180, "min").state).toBe("under");
    expect(progress(180, 180, "min").state).toBe("done");
    expect(progress(230, 180, "min").state).toBe("done");
  });

  it("najwyżej (sól): poniżej limitu jest dobrze, ponad źle", () => {
    expect(progress(3, 5, "max").state).toBe("under");
    expect(progress(5, 5, "max").state).toBe("under");
    expect(progress(6.2, 5, "max").state).toBe("over");
  });

  it("pasek mieści się w 0–1", () => {
    expect(progress(0, 100, "target").fill).toBe(0);
    expect(progress(500, 100, "target").fill).toBe(1);
  });
});

describe("progressText", () => {
  it("opisuje stan po polsku", () => {
    expect(progressText(progress(2150, 2800, "target"), "target", "kcal")).toBe("zostało 650 kcal");
    expect(progressText(progress(2920, 2800, "target"), "target", "kcal")).toBe(
      "+120 kcal ponad cel",
    );
    expect(progressText(progress(200, 180, "min"), "min", "g")).toBe("cel osiągnięty");
    expect(progressText(progress(120.5, 180, "min"), "min", "g")).toBe("zostało 59,5 g");
    expect(progressText(progress(3.2, 5, "max"), "max", "g")).toBe("zostało 1,8 g do limitu");
    expect(progressText(progress(6.2, 5, "max"), "max", "g")).toBe("+1,2 g ponad limit");
  });
});

describe("GOAL_ROWS", () => {
  it("obejmuje osiem wartości z etykiety, każdą raz", () => {
    expect(new Set(GOAL_ROWS.map((row) => row.key)).size).toBe(8);
  });
});
