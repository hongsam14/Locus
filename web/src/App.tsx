import { Component, lazy, Suspense, useEffect, type ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { api } from "./api";
import { configureLangs, t } from "./i18n";
import { HomePage } from "./routes/HomePage";
import { PlayPage } from "./routes/PlayPage";
import { Button } from "./ui";

// The editor and GM screens load when first opened (V2 NFR-4 § 2 "if over": the home and
// play screens a player opens first stay inside the JS budget).
const EditorPage = lazy(() => import("./routes/EditorPage").then((m) => ({ default: m.EditorPage })));
const GmPage = lazy(() => import("./routes/GmPage").then((m) => ({ default: m.GmPage })));

/** A later screen whose code did not arrive (a redeploy removed the old chunk, or the network
 * dropped) says so with [reload] instead of blanking the app (V4 code review 01 #4). */
class LoadFailed extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <div role="alert" data-testid="screen-load-failed" className="flex max-w-xl flex-col items-start gap-2 p-6">
        <strong className="text-danger">{t("error.screenLoad.title")}</strong>
        <span className="text-muted">{t("error.screenLoad.action")}</span>
        <Button onClick={() => window.location.reload()}>{t("action.reloadPage")}</Button>
      </div>
    );
  }
}

function Later({ children }: { children: ReactNode }) {
  return (
    <LoadFailed>
      <Suspense fallback={<p role="status" className="p-6 text-muted">{t("label.loading")}</p>}>{children}</Suspense>
    </LoadFailed>
  );
}

// The world list and three screens (F1 / AD-R8; U3 BR-U3-34: `/` lists the worlds).
export function App() {
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
      <Route path="/" element={<HomePage />} />
      <Route path="/editor/:worldId" element={<Later><EditorPage /></Later>} />
      <Route path="/gm/:sessionId" element={<Later><GmPage /></Later>} />
      <Route path="/play/:sessionId?" element={<PlayPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
