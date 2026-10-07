// The screens' list of server values matches the backend's (V2 BR-V2-11, review § 2): a
// value added or renamed on the server fails here, not as a raw identifier on a screen.
// Reads the Python sources as text, from web/ (src/test/paths).
import { readFileSync } from "node:fs";
import { ENUM_VALUES, type EnumKind } from "../format";
import { webPath } from "../test/paths";

const py = (path: string) => readFileSync(webPath(`../${path}`), "utf8");

/** The string values of `class <name>(…Enum)`: its `NAME = "value"` lines. */
function enumClass(source: string, name: string): string[] {
  const start = source.search(new RegExp(`^class ${name}\\(`, "m"));
  if (start < 0) throw new Error(`class ${name} not found`);
  const body = source.slice(start).split("\n").slice(1);
  const end = body.findIndex((l) => /^\S/.test(l));
  return (end < 0 ? body : body.slice(0, end)).flatMap((l) => {
    const m = /^\s+[A-Z_]+\s*=\s*"([^"]+)"/.exec(l);
    return m ? [m[1]] : [];
  });
}

/** The values of a `Literal["a", "b"]` on the line that starts with `lead`. */
function literal(source: string, lead: RegExp): string[] {
  const line = source.split("\n").find((l) => lead.test(l));
  if (!line) throw new Error(`${lead} not found`);
  const inside = /Literal\[([^\]]+)\]/.exec(line)?.[1] ?? "";
  return [...inside.matchAll(/"([^"]+)"/g)].map((m) => m[1]);
}

const shared = py("locus/shared/models/enums.py");
const play = py("locus/play/models.py");
const aug = py("locus/world/augmentation/types.py");

const BACKEND: Record<EnumKind, string[]> = {
  regionLevel: enumClass(shared, "RegionLevel"),
  connectionKind: enumClass(shared, "ConnectionKind"),
  travelBy: enumClass(shared, "ConnectionKind"), // a move goes along a connection
  scopeType: enumClass(shared, "ScopeType"),
  eventStatus: enumClass(play, "EventStatus"),
  eventCategory: enumClass(shared, "EventCategory"),
  eventLifecycle: enumClass(shared, "EventLifecycle"),
  sessionStatus: enumClass(play, "SessionStatus"),
  turnRunStatus: enumClass(play, "TurnRunStatus"),
  augmentationStatus: enumClass(aug, "RunStatus"),
  augmentationTarget: literal(aug, /^TargetKind\s*=/),
  augmentationAction: enumClass(aug, "AnswerAction"),
  deedKind: enumClass(play, "DeedKind"),
  rumorOrigin: literal(play, /^\s+origin_kind:\s*Literal/),
  wikiDomain: enumClass(shared, "WikiDomain"),
};

describe("server values against the backend", () => {
  for (const kind of Object.keys(ENUM_VALUES) as EnumKind[]) {
    it(`${kind} lists what the backend has`, () => {
      expect(BACKEND[kind].length, kind).toBeGreaterThan(1);
      expect([...ENUM_VALUES[kind]].sort()).toEqual([...BACKEND[kind]].sort());
    });
  }
});
