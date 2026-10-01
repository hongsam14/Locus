// `/api/langs` — what the server accepts as a display language (review U5 #2).
import type { Capabilities } from "../types";
import { http } from "./http";

export interface LangsOut {
  default: string;
  supported: string[];
}

export const metaApi = {
  getLangs: () => http<LangsOut>("/api/langs"),
  // U8 (BR-U8-23): which providers the server has; the screens warn ahead without an LLM
  capabilities: () => http<Capabilities>("/api/capabilities"),
};
