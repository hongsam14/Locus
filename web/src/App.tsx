import { Navigate, Route, Routes } from "react-router-dom";
import { DEFAULT_WORLD, EditorPage } from "./routes/EditorPage";
import { GmPage } from "./routes/GmPage";
import { PlayPage } from "./routes/PlayPage";

// Three screens (F1 / AD-R8): world editor, GameMaster, player.
export function App() {
  const home = `/editor/${DEFAULT_WORLD}`;
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
