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
    <div style={{ display: "flex", gap: 8, alignItems: "center", padding: 8, borderBottom: "1px solid #ddd" }}>
      <strong>Locus</strong>
      <input
        data-testid="world-input"
        value={worldId}
        placeholder="world id"
        // keep parent state in sync on every keystroke (avoids stale worldId on Load)
        onChange={(e) => onWorldIdChange(e.target.value)}
      />
      <button data-testid="load-btn" onClick={onLoad} disabled={busy}>
        Load
      </button>
      <button data-testid="build-world-btn" onClick={onBuildDemo} disabled={busy}>
        Build World (demo)
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
