import { formatDuration } from "@/lib/format";

describe("formatDuration", () => {
  it("shows plain seconds under a minute", () => {
    expect(formatDuration(0)).toBe("0s");
    expect(formatDuration(45)).toBe("45s");
  });

  it("shows minutes and seconds under an hour", () => {
    expect(formatDuration(2190)).toBe("36m 30s");
    expect(formatDuration(120)).toBe("2m");
  });

  it("shows hours and minutes at or above an hour", () => {
    expect(formatDuration(3661)).toBe("1h 1m");
    expect(formatDuration(7200)).toBe("2h");
  });

  it("rounds and clamps negative input to zero", () => {
    expect(formatDuration(59.6)).toBe("1m");
    expect(formatDuration(-5)).toBe("0s");
  });
});
