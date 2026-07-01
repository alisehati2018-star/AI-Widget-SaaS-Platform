"use client";

// Small single-series area trend (dataviz-skill compliant): 2px line in the
// validated brand hue on the dark surface, zero-based scale, crosshair +
// tooltip hover layer (readers aim at a date, never at the 2px line), values
// rendered in text tokens — never in the series color. The plot is forced LTR
// so time flows left→right even inside the RTL admin shell.

import { useCallback, useRef, useState } from "react";

export interface TrendPoint {
  date: string; // ISO YYYY-MM-DD
  value: number;
}

const W = 600; // viewBox units; strokes use non-scaling so they stay 2px on screen
const H = 140;
const TOP_PAD = 0.12; // headroom so the peak never clips

export function TrendChart({
  data,
  label,
  formatValue,
  formatDate,
  height = 96,
}: {
  data: TrendPoint[];
  label: string;
  formatValue: (v: number) => string;
  formatDate: (iso: string) => string;
  height?: number;
}) {
  const wrap = useRef<HTMLDivElement>(null);
  const [hover, setHover] = useState<number | null>(null);

  const n = data.length;
  const max = Math.max(1, ...data.map((p) => p.value));
  const xAt = (i: number) => (n > 1 ? (i / (n - 1)) * W : W / 2);
  const yAt = (v: number) => H - (v / max) * H * (1 - TOP_PAD);

  const linePath = data
    .map((p, i) => `${i === 0 ? "M" : "L"}${xAt(i).toFixed(2)},${yAt(p.value).toFixed(2)}`)
    .join(" ");
  const areaPath = n > 1 ? `${linePath} L${W},${H} L0,${H} Z` : "";

  const pick = useCallback(
    (clientX: number) => {
      const el = wrap.current;
      if (!el || n === 0) return;
      const rect = el.getBoundingClientRect();
      const ratio = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width));
      setHover(Math.round(ratio * (n - 1)));
    },
    [n],
  );

  const point = hover != null ? data[hover] : null;
  const hoverLeftPct = hover != null && n > 1 ? (hover / (n - 1)) * 100 : 50;
  const hoverTopPct = point != null ? (yAt(point.value) / H) * 100 : 0;
  // Keep the tooltip inside the card near either edge.
  const tipAlign = hoverLeftPct < 20 ? "left" : hoverLeftPct > 80 ? "right" : "center";

  return (
    <div>
      <div
        ref={wrap}
        dir="ltr"
        role="img"
        aria-label={label}
        style={{ position: "relative", height, touchAction: "pan-y" }}
        onPointerMove={(e) => pick(e.clientX)}
        onPointerDown={(e) => pick(e.clientX)}
        onPointerLeave={() => setHover(null)}
      >
        <svg
          viewBox={`0 0 ${W} ${H}`}
          preserveAspectRatio="none"
          style={{ position: "absolute", inset: 0, width: "100%", height: "100%", display: "block" }}
          aria-hidden
        >
          {areaPath ? <path d={areaPath} fill="var(--brand)" opacity={0.14} /> : null}
          <path
            d={linePath}
            fill="none"
            stroke="var(--brand)"
            strokeWidth={2}
            strokeLinejoin="round"
            strokeLinecap="round"
            vectorEffect="non-scaling-stroke"
          />
          <line
            x1={0}
            y1={H - 0.5}
            x2={W}
            y2={H - 0.5}
            stroke="var(--border)"
            strokeWidth={1}
            vectorEffect="non-scaling-stroke"
          />
        </svg>

        {point != null ? (
          <>
            {/* crosshair snapped to the nearest data X */}
            <div
              style={{
                position: "absolute",
                top: 0,
                bottom: 0,
                left: `${hoverLeftPct}%`,
                width: 1,
                background: "var(--faint)",
                opacity: 0.6,
                pointerEvents: "none",
              }}
            />
            {/* marker with a 2px surface ring so it separates from the fill */}
            <div
              style={{
                position: "absolute",
                left: `${hoverLeftPct}%`,
                top: `${hoverTopPct}%`,
                width: 9,
                height: 9,
                borderRadius: "50%",
                background: "var(--brand)",
                border: "2px solid var(--panel)",
                transform: "translate(-50%, -50%)",
                pointerEvents: "none",
              }}
            />
            <div
              role="status"
              style={{
                position: "absolute",
                bottom: "100%",
                left: tipAlign === "center" ? `${hoverLeftPct}%` : undefined,
                transform: tipAlign === "center" ? "translateX(-50%)" : undefined,
                ...(tipAlign === "left" ? { left: 0 } : {}),
                ...(tipAlign === "right" ? { right: 0 } : {}),
                marginBottom: 6,
                background: "var(--panel-2)",
                border: "1px solid var(--border)",
                borderRadius: 8,
                padding: "0.3rem 0.6rem",
                whiteSpace: "nowrap",
                pointerEvents: "none",
                zIndex: 5,
              }}
            >
              {/* values lead, labels follow — value strong, date secondary */}
              <strong style={{ fontSize: "0.9rem" }}>{formatValue(point.value)}</strong>{" "}
              <span className="hint">{formatDate(point.date)}</span>
            </div>
          </>
        ) : null}
      </div>

      {n > 1 ? (
        <div
          dir="ltr"
          className="hint"
          style={{ display: "flex", justifyContent: "space-between", marginTop: 4 }}
        >
          <span>{formatDate(data[0].date)}</span>
          <span>{formatDate(data[n - 1].date)}</span>
        </div>
      ) : null}
    </div>
  );
}
