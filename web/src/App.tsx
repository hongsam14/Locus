import { useEffect } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { api } from "./api";
import { configureLangs } from "./i18n";
import { DEFAULT_WORLD, EditorPage } from "./routes/EditorPage";
import { GmPage } from "./routes/GmPage";
import { PlayPage } from "./routes/PlayPage";

// Three screens (F1 / AD-R8): world editor, GameMaster, player.
export function App() {
  const home = `/editor/${DEFAULT_WORLD}`;
  // Learn the server's display languages once (review U5 #2). Until they arrive (or
  // if the call fails) no `?lang=` is sent and the server's default applies.
  useEffect(() => {
    Promise.resolve()
      .then(() => api.getLangs())
      .then((r) => {
        if (r && Array.isArray(r.supported)) configureLangs(r.default, r.supported);
      })
      .catch(() => {
        /* keep the server default */
      });
  }, []);
  return (
    <Routes>
      <Route path="/" element={<Navigate to={home} replace />} />
      <Route path="/editor/:worldId" element={<EditorPage />} />
      <Route path="/gm/:sessionId" element={<GmPage />} />
      <Route path="/play/:sessionId?" element={<PlayPage />} />
      <Route path="*" element={<Navigate to={home} replace />} />
    </Routes>
  );
}
