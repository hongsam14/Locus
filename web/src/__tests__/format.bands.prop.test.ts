// Measure bands are total, monotone and cut at their boundaries (V2 BR-V2-12, TP-V2-4,
// PBT-03). The seed is the run's (src/test/globalSetup.ts).
import fc from "fast-check";
import { BANDS, bandIndex, bandOf, decayWord, degreeWord, numberWithMeaning, type MeasureKind } from "../format";

const KINDS = Object.keys(BANDS) as MeasureKind[];
const kind = fc.constantFrom(...KINDS);
const unit = fc.double({ min: 0, max: 1, noNaN: true });
// values just around every boundary: where an off-by-one would show
const nearBoundary = kind.chain((k) =>
  fc
    .constantFrom(...BANDS[k].map((b) => b.upTo))
    .chain((b) => fc.constantFrom(b - 1e-9, b, b + 1e-9))
    .map((v) => ({ k, v: Math.min(1, Math.max(0, v)) })),
);

describe("measure bands (properties)", () => {
  it("every value in 0..1 gets exactly one band", () => {
    fc.assert(
      fc.property(kind, unit, (k, v) => {
        const i = bandIndex(k, v);
        return i >= 0 && i < BANDS[k].length;
      }),
    );
  });

  it("a larger value never gets a lower band", () => {
    fc.assert(
      fc.property(kind, unit, unit, (k, a, b) => {
        const [lo, hi] = a <= b ? [a, b] : [b, a];
        return bandIndex(k, lo) <= bandIndex(k, hi);
      }),
    );
  });

  it("a band holds its lower boundary and not its upper one (the last holds 1)", () => {
    fc.assert(
      fc.property(nearBoundary, ({ k, v }) => {
        const i = bandIndex(k, v);
        const bands = BANDS[k];
        const lower = i === 0 ? 0 : bands[i - 1].upTo;
        const upper = bands[i].upTo;
        return v >= lower && (v < upper || (i === bands.length - 1 && v <= 1));
      }),
    );
  });

  it("values outside 0..1 are clamped", () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    fc.assert(
      fc.property(kind, fc.double({ min: 1, max: 1e6, noNaN: true }), (k, over) => {
        return bandIndex(k, 1 + over) === bandIndex(k, 1) && bandIndex(k, -over) === bandIndex(k, 0);
      }),
    );
    warn.mockRestore();
  });
});

describe("measure bands (examples)", () => {
  it("cuts the distortion bands at 0.15 / 0.4 / 0.7", () => {
    expect(bandOf("distortion", 0)).toBe("word.distortion.nearlyTrue");
    expect(bandOf("distortion", 0.149)).toBe("word.distortion.nearlyTrue");
    expect(bandOf("distortion", 0.15)).toBe("word.distortion.stretched");
    expect(bandOf("distortion", 0.4)).toBe("word.distortion.twisted");
    expect(bandOf("distortion", 0.7)).toBe("word.distortion.otherStory");
    expect(bandOf("distortion", 1)).toBe("word.distortion.otherStory");
  });

  it("shows NaN and null as a dash", () => {
    expect(bandOf("support", Number.NaN)).toBe("word.none");
    expect(degreeWord(null, "ko")).toBe("—");
    expect(numberWithMeaning("support", undefined, "ko")).toBe("—");
  });

  it("words for the player, number and meaning for the GM", () => {
    expect(degreeWord(0.2, "ko")).toBe("조금 부풀려짐");
    expect(decayWord(0.7, "en")).toBe("Very faintly");
    expect(numberWithMeaning("distortion", 0.42, "ko")).toBe("0.42 · 많이 비틀림");
    expect(numberWithMeaning("weight", 0.6, "en")).toBe("0.60 · Often used");
  });

  it("the meaning matches the number as shown, at every band edge (review § 2)", () => {
    for (const kind of Object.keys(BANDS) as MeasureKind[]) {
      for (const { upTo } of BANDS[kind].slice(0, -1)) {
        const justBelow = upTo - 0.0001; // shows as the edge itself
        expect(numberWithMeaning(kind, justBelow, "ko")).toBe(numberWithMeaning(kind, upTo, "ko"));
      }
    }
  });

  it("every band has a ko and an en word", async () => {
    const { dicts } = await import("../i18n");
    for (const k of KINDS)
      for (const b of BANDS[k]) {
        expect(dicts.ko[`word.${k}.${b.key}`]).toBeTruthy();
        expect(dicts.en[`word.${k}.${b.key}`]).toBeTruthy();
      }
  });
});
