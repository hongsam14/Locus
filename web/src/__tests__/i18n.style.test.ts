// The register of a dictionary line follows its key's first segment (V2 Q2=A, BLM § 4,
// BR-V2-10, TP-V2-6). Older lines that V4/V6 move over are listed as legacy.
import { dicts } from "../i18n";

const CONTROL = ["action", "nav", "tab"];
const NOTICE = ["notice", "error", "confirm", "empty", "hint"];
const STORY = ["story"]; // log.* and timeline.* move over with the play and GM screens
const VALUE = ["enum", "word", "label", "unit"];

// lines written before V2, moved to the rule by the unit that rewrites their screen
const LEGACY = new Set([
  "nav.gmLocked", // V4: becomes hint.gmLocked
  "confirm.regen", // V6
  "confirm.regenAll", // V6
]);

const prefix = (key: string) => key.split(".")[0];
const ko = Object.entries(dicts.ko).filter(([k]) => !LEGACY.has(k));

describe("register by key", () => {
  it("control names have no sentence ending and no period", () => {
    for (const [k, v] of ko.filter(([k]) => CONTROL.includes(prefix(k)))) {
      expect(v, k).not.toMatch(/[.。]$|요$|다$/);
    }
  });

  it("notices are 해요체", () => {
    for (const [k, v] of ko.filter(([k]) => NOTICE.includes(prefix(k)))) {
      expect(v.trim(), k).toMatch(/요[.?]?$/);
    }
  });

  it("story lines are 해라체", () => {
    for (const [k, v] of ko.filter(([k]) => STORY.includes(prefix(k)))) {
      expect(v.trim(), k).toMatch(/다\.$/);
    }
  });

  it("value names have no period", () => {
    for (const [k, v] of ko.filter(([k]) => VALUE.includes(prefix(k)))) {
      expect(v, k).not.toMatch(/\.$/);
    }
  });

  it("the LLM-off notice gives no developer instruction (BR-V2-20)", () => {
    for (const lang of ["ko", "en"] as const) {
      const text = dicts[lang]["notice.llmOff"];
      expect(text).toBeTruthy();
      expect(text).not.toMatch(/\.env|OPENAI|API_KEY/);
    }
  });
});
