// Every server enum value has a Korean and an English label (V2 BR-V2-11, TP-V2-3).
import { dicts } from "../i18n";
import { ENUM_VALUES, enumLabel, type EnumKind } from "../format";

describe("enum labels", () => {
  for (const [kind, values] of Object.entries(ENUM_VALUES) as [EnumKind, readonly string[]][]) {
    for (const value of values) {
      it(`${kind}.${value} has ko and en`, () => {
        const ko = enumLabel(kind, value, "ko");
        const en = enumLabel(kind, value, "en");
        expect(ko).not.toBe("");
        expect(en).not.toBe("");
        expect(ko).not.toBe(value); // a Korean label, not the raw identifier
      });
    }
  }

  it("every enum.* dictionary key belongs to a listed value", () => {
    const listed = new Set(
      Object.entries(ENUM_VALUES).flatMap(([k, vs]) => vs.map((v) => `enum.${k}.${v}`)),
    );
    for (const key of Object.keys(dicts.ko).filter((k) => k.startsWith("enum."))) {
      expect(listed.has(key), key).toBe(true);
    }
  });

  it("an unknown value shows as it is and warns in dev", () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    expect(enumLabel("regionLevel", "moon", "ko")).toBe("moon");
    expect(warn).toHaveBeenCalled();
    warn.mockRestore();
  });

  it("slant is not an enum (free text from the LLM)", () => {
    expect(Object.keys(ENUM_VALUES)).not.toContain("slant");
  });
});
