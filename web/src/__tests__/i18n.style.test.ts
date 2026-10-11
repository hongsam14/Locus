// The register of a dictionary line follows its key's first segment (V2 Q2=A, BLM § 4,
// BR-V2-10, TP-V2-6). Older lines that V4/V6 move over are listed as legacy.
import { readFileSync } from "node:fs";
import { BANDS, type MeasureKind } from "../format/bands";
import { ENUM_VALUES } from "../format/enums";
import { dicts } from "../i18n";
import { sourceFiles, webPath } from "../test/paths";

const CONTROL = ["action", "nav", "tab"];
const NOTICE = ["notice", "error", "confirm", "empty", "hint"];
const STORY = ["story", "log"]; // log.* moved over with the play screen (V4); timeline.* with GM (V6)
const VALUE = ["enum", "word", "label", "unit"];

// lines written before V2, moved to the rule by the unit that rewrites their screen
const LEGACY = new Set<string>([
  // V6 rewrote the two regenerate confirmations under the rule (confirm.regenRegion /
  // confirm.regenAllRumors); none is left
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


// V8 code review 01 #38: a placeholder dropped or renamed in one language shows "{n}" raw
describe("placeholders", () => {
  it("every key has the same {placeholders} in ko and en", () => {
    const names = (text: string) => [...text.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort().join(",");
    const off = Object.entries(dicts.ko)
      .filter(([k, v]) => names(v) !== names((dicts.en as Record<string, string>)[k] ?? ""))
      .map(([k]) => k);
    expect(off).toEqual([]);
  });
});


// V9 W-1: the editor and the map speak 해요체 like every other notice (V8 code-summary § 6).
// 합니다체 is a ㅂ batchim before 니다/니까 (or 십시오), wherever it stands in the line — before
// "…", "(" or a quote too — while "없으니까" or "다니다" is not (code review 01 #1, #13). Every
// sentence that ends in a mark ends in 해요체, and a line never ends in a bare 다/까 (#14);
// a name such as "{name} 지역 삭제" ends in neither.
const nfd = (text: string) => text.normalize("NFD");
const HAPNIDA = new RegExp(
  `${nfd("ᆸ")}(?:${nfd("니다")}|${nfd("니까")})|${nfd("십시오")}|${nfd("시오")}(?=[\\s.!?…)"']|$)`,
);
const hapnida = (text: string) => HAPNIDA.test(nfd(text));
function registerOff(text: string): string | null {
  const line = text.trim();
  if (hapnida(line)) return "합니다체";
  for (const sentence of line.split(/(?<=[.?!])\s+/)) {
    // an aside in brackets before the mark belongs to the sentence: "있어요(서버 재시작)."
    const core = sentence.replace(/\s*\([^()]*\)(?=[.?!]$)/, "");
    if (/[.?!]$/.test(core) && !/요[.?!]$/.test(core)) return `not 해요체: ${sentence}`;
  }
  return /[다까]$/.test(line) ? "ends in 다/까" : null;
}

describe("the editor's and the map's lines", () => {
  const EDITOR = ["editor.", "map.hint.", "delete.", "augment.", "wiki.", "build."];
  const shown = Object.entries(dicts.ko).filter(([k]) => EDITOR.some((p) => k.startsWith(p)));

  it("are 해요체: no 합니다체 anywhere, every sentence and the line's end in 해요체", () => {
    expect(shown.map(([k]) => k)).toEqual(
      expect.arrayContaining(["map.hint.select", "editor.npc.none", "delete.knowledge",
        "augment.budget", "wiki.none", "build.working"]),
    );
    expect(shown.filter(([, v]) => registerOff(v)).map(([k, v]) => `${k}: ${registerOff(v)}`)).toEqual([]);
  });

  it("the 합니다체 check finds ㅂ니다 and ㅂ니까 wherever they stand", () => {
    for (const text of ["지웁니까", "지웁니까 하고", "연결이 없습니다", "만드는 중입니다…", "지웁니다(x)"]) {
      expect(hapnida(text), text).toBe(true);
    }
    for (const text of ["없으니까", "돌아다니다", "지워요"]) expect(hapnida(text), text).toBe(false);
  });

  it("the register check tells the forms apart", () => {
    for (const off of ["연결이 없습니다", "연결 {n}개를 지웁니다: {names}", "만드는 중입니다…",
      "씨앗 {n}개를 지웁니다(되돌릴 수 없음)", "\"지웁니다\"", "지웁니까?", "누르십시오", "누르시오",
      "저장합니다만 되돌릴 수 없어요.", "이곳에 사는 NPC가 없다", "지운다. 기록은 남아요.",
      "기록이 사라졌다(서버 재시작)."]) {
      expect(registerOff(off), off).not.toBeNull();
    }
    for (const fine of ["연결 {n}개를 지워요: {names}", "키가 없으니까 쉬어요", "섬을 돌아다니며 들어요",
      "{name} 지역 삭제", "같은 id의 월드가 있어요. 교체할까요?", "만드는 중… 수십 초 걸려요",
      "보강 기록이 사라졌어요(서버 재시작)."]) {
      expect(registerOff(fine), fine).toBeNull();
    }
  });
});

// V9 W-2: a key no screen reads is a line nobody sees and nobody keeps in step. A key counts
// as used when the source names it outside a comment, or builds it from a family. `word.` and
// `enum.` are families whose keys the data fixes (BANDS, ENUM_VALUES), so only those keys
// count (code review 01 #15); `error.`, `timeline.`, `log.` and `tab.` are built from what the
// server or the screen passes, so their prefix counts.
const stripComments = (text: string) =>
  text.replace(/\/\*[\s\S]*?\*\//g, "").replace(/(^|[^:\\])\/\/.*$/gm, "$1");
const familiesIn = (text: string) =>
  [
    ...text.matchAll(/`([\w.-]+\.)\$\{/g),
    ...text.matchAll(/["']([A-Za-z]\w*(?:\.\w+)*\.)["']\s*\+/g),
  ].map((m) => m[1]);

describe("every dictionary key is used", () => {
  const app = sourceFiles("src")
    .filter((path) => !/src\/i18n\/(ko|en)\.ts$/.test(path))
    .map((path) => stripComments(readFileSync(webPath(path), "utf8")))
    .join("\n");
  const families = familiesIn(app);
  const DATA: Record<string, Set<string>> = {
    "word.": new Set(
      (Object.keys(BANDS) as MeasureKind[]).flatMap((kind) =>
        BANDS[kind].map((band) => `word.${kind}.${band.key}`)),
    ),
    "enum.": new Set(
      Object.entries(ENUM_VALUES).flatMap(([kind, values]) =>
        (values as readonly string[]).map((value) => `enum.${kind}.${value}`)),
    ),
  };
  const named = (key: string) =>
    new RegExp(`["'\`]${key.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}["'\`]`).test(app);
  const used = (key: string) => {
    if (named(key)) return true;
    const data = Object.keys(DATA).find((prefix) => key.startsWith(prefix));
    return data ? DATA[data].has(key) : families.some((family) => key.startsWith(family));
  };

  it("by a literal or a family in the app's source, comments left out", () => {
    expect(app).not.toMatch(/(^|\s)\/\/ /m); // the sources' comments are gone
    expect(Object.keys(dicts.ko).filter((key) => !used(key))).toEqual([]);
  });

  it("the check tells a used key from an unused one", () => {
    expect(families).toContain("map.hint.");
    expect(used("map.hint.select")).toBe(true); // a family
    expect(used("map.unused")).toBe(false); // a family is its whole prefix, not "map."
    expect(used("nav.play")).toBe(true); // a literal
    expect(used("session.none")).toBe(false); // gone with V9; no screen showed it
    expect(used("word.distortion.twisted")).toBe(true); // a band
    expect(used("word.rumor.promoted")).toBe(false); // no band "rumor" (code review 01 #15)
    expect(used("enum.eventCategory.war")).toBe(true);
    expect(used("enum.eventCategory.madeUp")).toBe(false);
  });

  it("reads both family forms and skips comments", () => {
    expect(familiesIn('t("aa.bb." + k); t(`cc.dd.${k}`)')).toEqual(["cc.dd.", "aa.bb."]);
    expect(stripComments('// was "editor.ghost"\nconst u = "http://x"; /* "a.b" */')).toBe(
      '\nconst u = "http://x"; ',
    );
  });
});
