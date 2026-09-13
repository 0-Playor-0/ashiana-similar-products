// A static summary of §2's pipeline — offline embedding/fusion producing a
// versioned artifact bundle, served read-only by the API at request time.
// No numbers here are computed; this is a fixed illustration, not a chart.
const BOX_STYLE = {
  fill: "var(--color-surface)",
  stroke: "var(--color-accent-gold)",
  strokeWidth: 1,
};
const TEXT_STYLE = { fill: "var(--color-ground)", fontSize: 12, fontFamily: "var(--font-ui)" };
const LABEL_STYLE = { fill: "var(--color-accent-ice)", fontSize: 11, fontFamily: "var(--font-ui)" };

function Box({ x, y, w, h, lines }: { x: number; y: number; w: number; h: number; lines: string[] }) {
  return (
    <g>
      <rect x={x} y={y} width={w} height={h} rx={4} style={BOX_STYLE} />
      {lines.map((line, i) => (
        <text
          key={line}
          x={x + w / 2}
          y={y + h / 2 - ((lines.length - 1) * 7) + i * 14}
          textAnchor="middle"
          style={TEXT_STYLE}
        >
          {line}
        </text>
      ))}
    </g>
  );
}

function Arrow({ x1, y1, x2, y2 }: { x1: number; y1: number; x2: number; y2: number }) {
  return (
    <line
      x1={x1}
      y1={y1}
      x2={x2}
      y2={y2}
      stroke="var(--color-accent-silver)"
      strokeWidth={1.5}
      markerEnd="url(#arrowhead)"
    />
  );
}

export function ArchitectureDiagram() {
  return (
    <svg viewBox="0 0 820 300" role="img" aria-label="Architecture: an offline pipeline builds a versioned artifact bundle from the catalog; the online API loads it once and serves ranking requests to the React UI.">
      <defs>
        <marker id="arrowhead" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
          <path d="M0,0 L8,4 L0,8 Z" fill="var(--color-accent-silver)" />
        </marker>
      </defs>

      <text x={16} y={20} style={LABEL_STYLE}>
        OFFLINE (rerun when the catalog changes)
      </text>
      <Box x={16} y={30} w={110} h={44} lines={["catalog.jsonl"]} />
      <Arrow x1={126} y1={52} x2={166} y2={52} />
      <Box x={166} y={30} w={110} h={44} lines={["DINOv2-small", "bge-small-en"]} />
      <Arrow x1={276} y1={52} x2={316} y2={52} />
      <Box x={316} y={30} w={120} h={44} lines={["S_image / S_text", "S_meta"]} />
      <Arrow x1={436} y1={52} x2={476} y2={52} />
      <Box x={476} y={30} w={130} h={44} lines={["core.fusion", "offdiag_zscore"]} />
      <Arrow x1={606} y1={52} x2={646} y2={52} />
      <Box x={646} y={20} w={150} h={64} lines={["artifacts/", "matrices + manifest", "(committed to git)"]} />

      <Arrow x1={721} y1={84} x2={721} y2={130} />

      <text x={16} y={160} style={LABEL_STYLE}>
        ONLINE
      </text>
      <Box x={476} y={170} w={150} h={44} lines={["FastAPI (numpy only)", "loads bundle at startup"]} />
      <Arrow x1={646} y1={192} x2={686} y2={192} />
      <Box x={686} y={160} w={110} h={64} lines={["React UI", "catalog · product", "under-the-hood"]} />
      <Arrow x1={476} y1={192} x2={356} y2={192} />
      <Box x={236} y={170} w={120} h={44} lines={["core.filters", "core.reasons"]} />
    </svg>
  );
}
