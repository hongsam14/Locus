// `/api/gm` — GameMaster controls: timeline, rumors, distortion, turns, events.
import type {
  EventCategory,
  EventLifecycle,
  RegionDistortion,
  SessionEvent,
  SessionRumor,
  TimelineEntry,
  TurnResult,
} from "../types";
import { enc, http } from "./http";

const s = (sid: string) => `/api/gm/sessions/${enc(sid)}`;

export const gmApi = {
  getTimeline: (sid: string) => http<TimelineEntry[]>(`${s(sid)}/timeline`),
  listRumors: (sid: string, regionId: string) =>
    http<SessionRumor[]>(`${s(sid)}/regions/${enc(regionId)}/rumors`),
  generateRumors: (sid: string, regionId: string) =>
    http<SessionRumor[]>(`${s(sid)}/regions/${enc(regionId)}/rumors`, { method: "POST" }),
  regenRumors: (sid: string, regionId: string) =>
    http<SessionRumor[]>(`${s(sid)}/regions/${enc(regionId)}/rumors/regen`, { method: "POST" }),
  setSupport: (sid: string, rumorId: string, support: number) =>
    http<SessionRumor>(`${s(sid)}/rumors/${enc(rumorId)}/support`, {
      method: "PUT",
      body: JSON.stringify({ support }),
    }),
  setDistortion: (sid: string, regionId: string, degree: number) =>
    http<RegionDistortion>(`${s(sid)}/regions/${enc(regionId)}/distortion`, {
      method: "PUT",
      body: JSON.stringify({ degree }),
    }),
  listDistortions: (sid: string) => http<RegionDistortion[]>(`${s(sid)}/distortions`),
  advanceTurn: (sid: string) => http<TurnResult>(`${s(sid)}/advance`, { method: "POST" }),

  // events
  listEvents: (sid: string, status?: string) =>
    http<SessionEvent[]>(`${s(sid)}/events${status ? `?status=${enc(status)}` : ""}`),
  createEvent: (
    sid: string,
    body: {
      region_id: string;
      category: EventCategory;
      description: string;
      magnitude: number;
      lifecycle?: EventLifecycle | null;
    },
  ) => http<SessionEvent>(`${s(sid)}/events`, { method: "POST", body: JSON.stringify(body) }),
  suggestEvents: (sid: string, n = 1) =>
    http<SessionEvent[]>(`${s(sid)}/events/suggest?n=${n}`, { method: "POST" }),
  approveEvent: (sid: string, eid: string) =>
    http<SessionEvent>(`${s(sid)}/events/${enc(eid)}/approve`, { method: "POST" }),
  resolveEvent: (sid: string, eid: string) =>
    http<SessionEvent>(`${s(sid)}/events/${enc(eid)}/resolve`, { method: "POST" }),
  discardEvent: (sid: string, eid: string) =>
    http<void>(`${s(sid)}/events/${enc(eid)}`, { method: "DELETE" }),
};
