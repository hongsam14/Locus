// Every server value the screens show, in one place (V2 BR-V2-11, domain-entities § 4).
// A value added on the server shows here as a missing label in the exhaustive test.
// Sources: locus/shared/models/enums.py, locus/play/models.py, web/src/types.ts,
// locus/world/augmentation/types.py.

export const ENUM_VALUES = {
  regionLevel: ["continent", "province", "town", "district", "terrain"],
  connectionKind: ["adjacent", "route", "river", "blocked"],
  travelBy: ["adjacent", "route", "river", "blocked"],
  scopeType: ["direct", "inherited", "propagated", "global", "hearsay"],
  eventStatus: ["suggested", "active", "resolved"],
  eventCategory: ["war", "plague", "politics", "disaster", "festival", "discovery"],
  eventLifecycle: ["one_shot", "persistent"],
  sessionStatus: ["open", "closed"],
  turnRunStatus: ["running", "done", "failed"],
  augmentationStatus: ["open", "converged", "stopped"],
  augmentationTarget: ["knowledge", "entity", "region", "connection"],
  augmentationAction: ["confirm", "edit", "remove", "add", "ignore"],
  deedKind: ["arrival", "statement", "declared_action"],
  rumorOrigin: ["canonical", "deed"],
  wikiDomain: [
    "geography",
    "geology",
    "climate",
    "ecology",
    "economy",
    "logistics",
    "culture",
    "history",
    "politics",
    "religion",
    "military",
    "technology",
    "other",
  ],
} as const;

export type EnumKind = keyof typeof ENUM_VALUES;
