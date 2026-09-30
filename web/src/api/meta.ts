// `/api/langs` — what the server accepts as a display language (review U5 #2).
import { http } from "./http";

export interface LangsOut {
  default: string;
  supported: string[];
}

export const metaApi = {
  getLangs: () => http<LangsOut>("/api/langs"),
};
