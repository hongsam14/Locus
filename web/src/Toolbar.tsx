import { useState } from "react";

interface Props {
  worldId: string;
  onWorldIdChange: (v: string) => void;
  onLoad: () => void;
  onBuildDemo: () => void;
  onBuildWiki: () => void;
  onPickMap: (url: string) => void;
  busy?: boolean;
}

export function Toolbar({
  worldId,
  onWorldIdChange,
  onLoad,
  onBuildDemo,
  onBuildWiki,
  onPickMap,
  busy,
}: Props) {
  const [pending, setPending] = useState(worldId);
  return (
    <div style={{ display: "flex", gap: 8, alignItems: "center", padding: 8, borderBottom: "1px solid #ddd" }}>
      <strong>Locus</strong>
      <input
        data-testid="world-input"
        value={pending}
        placeholder="world id"
        onChange={(e) => setPending(e.target.value)}
        onBlur={() => onWorldIdChange(pending)}
      />
      <button data-testid="load-btn" onClick={onLoad} disabled={busy}>
        Load
      </button>
      <button data-testid="build-world-btn" onClick={onBuildDemo} disabled={busy}>
        Build World (demo)
      </button>
      <button data-testid="build-wiki-btn" onClick={onBuildWiki} disabled={busy}>
        Build Wiki
      </button>
      <label style={{ fontSize: 12 }}>
        Map:
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
