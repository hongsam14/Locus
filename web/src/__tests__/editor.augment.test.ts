// V8 names for the augmentation panel and the build report (code plan Step 3.4/3.5, BR-V8-18/30,
// TP-V8-10, § 1.4 R-08(c)): the issue key and the change description become names and labels;
// nothing internal reaches the screen.
import fc from "fast-check";
import { changeLabel, fieldLabel, issueKeyLine, issueKeyName, type NameSource, targetLabel } from "../features/editor/augmentNames";
import { BUILD_STAGES, groupByStage, sessionsNotClosed, stageLabel } from "../features/editor/buildStages";
import { ENUM_VALUES, enumLabel } from "../format";
import { t } from "../i18n";
import type { BuildWarning, ConnectionEdge, Knowledge, QuestionTarget, Region } from "../types";

const reg = (id: string, name: string): Region => ({ id, name, level: "town" });
const src: NameSource = {
  regions: [reg("r1", "Harbor"), reg("r|2", "Iron|crag"), reg("r:3", "Ford")],
  knowledge: [{ id: "k1", title: "Fish", statement: "fish swim" } as Knowledge],
  entities: [{ id: "e1", name: "Tomas" }],
  connections: [{ source_region_id: "r1", target_region_id: "r:3", kind: "route", weight: 0.6 } as ConnectionEdge],
};

describe("issue key names (BLM § 6.4, R-07)", () => {
  it("names a region, knowledge, an entity and a connection", () => {
    expect(issueKeyName("gap:region:r1::", src)).toBe("Harbor");
    expect(issueKeyName("low_confidence:knowledge:k1::", src)).toBe("Fish");
    expect(issueKeyName("orphan:entity:e1::", src)).toBe("Tomas");
    expect(issueKeyName("dangling:connection:r1|r:3|route:wiki_prior_ref:p9", src)).toBe(
      `Harbor – Ford · ${enumLabel("connectionKind", "route")} · ${fieldLabel("wiki_prior_ref")}`,
    );
  });

  it("reads ids that hold ':' or '|' themselves, and adds the broken field's label", () => {
    expect(issueKeyName("gap:region:r:3::", src)).toBe("Ford");
    expect(issueKeyName("gap:region:r|2::", src)).toBe("Iron|crag");
    expect(issueKeyName("dangling:entity:e1:located_in:gone", src)).toBe(`Tomas · ${t("label.field.located_in")}`);
  });

  it("an unknown target or a key it cannot read is an unnamed item", () => {
    expect(issueKeyName("gap:region:nope::", src)).toBe(t("label.unnamed"));
    expect(issueKeyName("garbage", src)).toBe(t("label.unnamed"));
    expect(fieldLabel("weird_field")).toBe(t("label.field.other"));
  });
});

describe("change descriptions (BR-V8-18)", () => {
  it("type:action reads as two labels; anything else as 'change'", () => {
    expect(changeLabel("low_confidence:confirm")).toBe(
      `${enumLabel("augmentationIssue", "low_confidence")} · ${enumLabel("augmentationAction", "confirm")}`,
    );
    expect(changeLabel("low_confidence:dance")).toBe(t("label.change"));
    expect(changeLabel("something")).toBe(t("label.change"));
  });
});

// R-08(c): names and ids drawn from letters, Hangul and spaces only — no "_" or ":" — so a
// raw enum value or the key itself in the output can only come from a leak
const word = fc.stringMatching(/^[A-Za-z가-힣 ]{1,8}$/);
const RAW = [...ENUM_VALUES.augmentationIssue, ...ENUM_VALUES.augmentationAction].filter((v) => v.includes("_"));

describe("nothing internal leaks (property)", () => {
  it("an issue key never comes back as itself or as a raw enum value", () => {
    fc.assert(
      fc.property(
        fc.constantFrom(...ENUM_VALUES.augmentationIssue),
        fc.constantFrom("region", "knowledge", "entity", "connection"),
        word,
        word,
        fc.boolean(),
        (type, kind, id, name, known) => {
          const s: NameSource = {
            regions: known && kind === "region" ? [reg(id, name)] : [],
            knowledge: known && kind === "knowledge" ? [{ id, title: name, statement: name } as Knowledge] : [],
            entities: known && kind === "entity" ? [{ id, name }] : [],
            connections: [],
          };
          const key = `${type}:${kind}:${id}::`;
          const out = issueKeyName(key, s);
          expect(out).not.toContain(key);
          for (const raw of RAW) expect(out).not.toContain(raw);
        },
      ),
    );
  });

  it("a change description never comes back raw", () => {
    fc.assert(
      fc.property(fc.constantFrom(...ENUM_VALUES.augmentationIssue, "x"), fc.constantFrom(...ENUM_VALUES.augmentationAction, "y"), (type, action) => {
        const out = changeLabel(`${type}:${action}`);
        expect(out).not.toContain(":");
        for (const raw of RAW) expect(out).not.toContain(raw);
      }),
    );
  });
});

describe("build stages (BR-V8-15/30)", () => {
  const w = (stage: string, severity: "warning" | "error" = "warning"): BuildWarning => ({ stage, severity, message: `m ${stage}` });

  it("labels known stages and reads an unknown one as 'other'", () => {
    expect(stageLabel("carry-over")).toBe(t("label.stage.carry-over"));
    expect(stageLabel("a-new-stage")).toBe(t("label.stage.other"));
  });

  it("groups by stage, errors first, keeping the server's lines", () => {
    const groups = groupByStage([w("carry-over"), w("backup", "error"), w("carry-over"), w("zzz")]);
    expect(groups.map((g) => [g.stage, g.severity, g.warnings.length])).toEqual([
      ["backup", "error", 1],
      ["carry-over", "warning", 2],
      ["other", "warning", 1],
    ]);
    expect(groups[1].warnings[0].message).toBe("m carry-over");
  });

  it("counts the sessions a replace could not close", () => {
    expect(sessionsNotClosed([w("sessions"), w("sessions"), w("backup")])).toBe(2);
  });
});


// V8 code review 01 #16, #21, #23, #3: keys and names the friendly fixtures above did not try
describe("issue keys and target names, as the server really sends them", () => {
  it("a broken id that holds ':' does not hide the field (#21)", () => {
    expect(issueKeyName("dangling:knowledge:k1:about_entity_ids:e:gone", src)).toBe(`Fish · ${fieldLabel("about_entity_ids")}`);
  });

  it("a connection stored the other way round is still named (#16)", () => {
    const reversed: NameSource = { ...src, connections: [{ source_region_id: "r:3", target_region_id: "r1", kind: "route", weight: 0.6 } as ConnectionEdge] };
    const key = `orphan:connection:${["r1", "r:3"].sort().join("|")}|route::`;
    expect(issueKeyName(key, reversed)).toBe(`Harbor – Ford · ${enumLabel("connectionKind", "route")}`);
  });

  it("a key over several targets is named by the first the world holds (#16)", () => {
    expect(issueKeyName("low_confidence:knowledge:k0|k1::", src)).toBe("Fish");
  });

  it("a target the world does not hold is an unnamed item, never its id (#16)", () => {
    fc.assert(
      fc.property(fc.stringMatching(/^[A-Za-z가-힣 ]{1,12}$/), (id) => {
        fc.pre(!["r1", "k1", "e1"].includes(id));
        for (const kind of ["region", "knowledge", "entity"]) {
          expect(issueKeyName(`gap:${kind}:${id}::`, src)).toBe(t("label.unnamed"));
        }
      }),
    );
  });

  it("an ignored or kept line says which issue (#23)", () => {
    expect(issueKeyLine("gap:region:r1::", src)).toBe(`${enumLabel("augmentationIssue", "gap")} · Harbor`);
    expect(issueKeyLine("low_confidence:knowledge:k1::", src)).toBe(`${enumLabel("augmentationIssue", "low_confidence")} · Fish`);
    expect(issueKeyLine("strange:region:r1::", src)).toBe("Harbor");
  });

  it("a question's target is named from the world: a connection by its regions and kind in words (#3)", () => {
    const conn: QuestionTarget = { kind: "connection", id: "r1|r:3|route", name: "Harbor – Ford (route)",
      connection: { world_id: "w", a_region_id: "r1", b_region_id: "r:3", kind: "route" } };
    expect(targetLabel(conn, src)).toBe(`Harbor – Ford · ${enumLabel("connectionKind", "route")}`);
    expect(targetLabel({ ...conn, connection: null }, src)).toBe(`Harbor – Ford · ${enumLabel("connectionKind", "route")}`);
    expect(targetLabel({ ...conn, id: "x|y|route", connection: null }, src)).toBe(t("label.unnamed"));
    expect(targetLabel({ kind: "knowledge", id: "k1", name: "Fische" }, src)).toBe("Fish");
    expect(targetLabel({ kind: "knowledge", id: "k-gone", name: "Old mill" }, src)).toBe("Old mill");
  });

  it("the build stages are the 15 of BR-V8-15 (T12: the list does not check itself)", () => {
    expect([...BUILD_STAGES].sort()).toEqual([
      "backup", "carry-over", "commit", "duplicate-ids", "embed", "import", "ingestion", "load", "ontology",
      "persist-graph", "persist-meta", "persist-search", "sessions", "topology", "wiki",
    ]);
  });
});
