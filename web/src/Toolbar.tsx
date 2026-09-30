import { t } from "./i18n";
import { Button, Field } from "./ui";

interface Props {
  worldId: string;
  onWorldIdChange: (v: string) => void;
  onLoad: () => void;
  onBuildDemo: () => void;
  onPickMap: (url: string) => void;
  busy?: boolean;
}

export function Toolbar({
  worldId,
  onWorldIdChange,
  onLoad,
  onBuildDemo,
  onPickMap,
  busy,
}: Props) {
  return (
    <div className="flex flex-wrap items-center gap-2 border-b border-ink px-3 py-2 bg-paper-card">
      <Field
        data-testid="world-input"
        value={worldId}
        placeholder={t("toolbar.worldId")}
        // keep parent state in sync on every keystroke (avoids stale worldId on Load)
        onChange={(e) => onWorldIdChange(e.target.value)}
      />
      <Button data-testid="load-btn" onClick={onLoad} disabled={busy}>
        {t("toolbar.load")}
      </Button>
      <Button variant="primary" data-testid="build-world-btn" onClick={onBuildDemo} disabled={busy}>
        {t("toolbar.loadDemo")}
      </Button>
      <label className="text-xs text-ink-soft inline-flex items-center gap-1">
        {t("toolbar.pickMap")}
        <input
          data-testid="map-file-input"
          type="file"
          accept="image/*"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) onPickMap(URL.createObjectURL(f));
          }}
        />
      </label>
    </div>
  );
}
