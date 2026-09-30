// API client split by backend boundary (U1 §11.2): world / knowledge / play / gm.
// `api` merges the four so existing components keep importing `./api`.
import { gmApi } from "./gm";
import { knowledgeApi } from "./knowledge";
import { metaApi } from "./meta";
import { playApi } from "./play";
import { worldApi } from "./world";

export { gmApi, knowledgeApi, metaApi, playApi, worldApi };

export const api = {
  ...worldApi,
  ...knowledgeApi,
  ...playApi,
  ...gmApi,
  ...metaApi,
};
