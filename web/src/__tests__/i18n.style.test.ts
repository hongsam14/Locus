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
const lines = (group: string[]) => ko.filter(([k]) => group.includes(prefix(k)));

const CONTROL_END = /[.。]$|요$|다$/;
const HAEYO = /요[.?]?$/;
const HAERA = /다\.$/;

describe("register by key", () => {
  it("control names have no sentence ending and no period", () => {
    expect(lines(CONTROL).length).toBeGreaterThan(0); // the check checks something (review § 2)
    for (const [k, v] of lines(CONTROL)) expect(v, k).not.toMatch(CONTROL_END);
  });

  it("notices are 해요체", () => {
    expect(lines(NOTICE).length).toBeGreaterThan(0);
    for (const [k, v] of lines(NOTICE)) expect(v.trim(), k).toMatch(HAEYO);
  });

  // no story.* line yet: log.* and timeline.* move over with V4/V6, and this then checks them
  it.skipIf(lines(STORY).length === 0)("story lines are 해라체", () => {
    for (const [k, v] of lines(STORY)) expect(v.trim(), k).toMatch(HAERA);
  });

  it("value names have no period", () => {
    expect(lines(VALUE).length).toBeGreaterThan(0);
    for (const [k, v] of lines(VALUE)) expect(v, k).not.toMatch(/\.$/);
  });

  it("the register checks tell the registers apart", () => {
    expect("소문이 퍼졌다.").toMatch(HAERA);
    expect("소문이 퍼졌어요.").not.toMatch(HAERA);
    expect("서버에 닿지 못했어요.").toMatch(HAEYO);
    expect("서버에 닿지 못했다.").not.toMatch(HAEYO);
    expect("저장했어요").toMatch(CONTROL_END);
    expect("저장").not.toMatch(CONTROL_END);
  });

  it("the LLM-off notice gives no developer instruction (BR-V2-20)", () => {
    for (const lang of ["ko", "en"] as const) {
      const text = dicts[lang]["notice.llmOff"];
      expect(text).toBeTruthy();
      expect(text).not.toMatch(/\.env|OPENAI|API_KEY/);
    }
  });
});
