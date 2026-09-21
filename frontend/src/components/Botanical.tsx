import React from "react";

type BotanicalProps = {
  className?: string;
  style?: React.CSSProperties;
};

export function LeafBranch({ className, style }: BotanicalProps) {
  const leaves = [
    { cx: 104, cy: 58, rx: 30, ry: 12, rot: -58 },
    { cx: 96, cy: 92, rx: 34, ry: 13, rot: 56 },
    { cx: 106, cy: 132, rx: 33, ry: 13, rot: -60 },
    { cx: 96, cy: 172, rx: 36, ry: 14, rot: 58 },
    { cx: 106, cy: 214, rx: 34, ry: 13, rot: -62 },
    { cx: 98, cy: 254, rx: 31, ry: 12, rot: 60 },
    { cx: 105, cy: 292, rx: 26, ry: 11, rot: -64 },
  ];

  return (
    <svg
      viewBox="0 0 200 340"
      className={className}
      style={style}
      fill="currentColor"
      aria-hidden="true"
      focusable="false"
    >
      <path
        d="M100 340 C 106 258 96 168 104 22"
        fill="none"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
      />
      {leaves.map((leaf, i) => (
        <ellipse
          key={i}
          cx={leaf.cx}
          cy={leaf.cy}
          rx={leaf.rx}
          ry={leaf.ry}
          transform={`rotate(${leaf.rot} ${leaf.cx} ${leaf.cy})`}
        />
      ))}
    </svg>
  );
}

export function Fern({ className, style }: BotanicalProps) {
  const pinnae = Array.from({ length: 16 }, (_, i) => {
    const t = i / 15;
    const y = 24 + t * 290;
    const spread = 62 * Math.sin(Math.PI * (0.18 + t * 0.82));
    const len = 30 * Math.sin(Math.PI * (0.2 + t * 0.8)) + 8;
    return { y, spread, len, rot: -34 - t * 12 };
  });

  return (
    <svg
      viewBox="0 0 200 340"
      className={className}
      style={style}
      fill="currentColor"
      aria-hidden="true"
      focusable="false"
    >
      <path
        d="M100 338 C 102 250 98 140 100 18"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
      />
      {pinnae.map((p, i) => (
        <g key={i}>
          <ellipse
            cx={100 - p.spread}
            cy={p.y}
            rx={p.len}
            ry="6"
            transform={`rotate(${-p.rot} ${100 - p.spread} ${p.y})`}
          />
          <ellipse
            cx={100 + p.spread}
            cy={p.y}
            rx={p.len}
            ry="6"
            transform={`rotate(${p.rot} ${100 + p.spread} ${p.y})`}
          />
        </g>
      ))}
    </svg>
  );
}

export function MonsteraLeaf({ className, style }: BotanicalProps) {
  return (
    <svg
      viewBox="0 0 200 340"
      className={className}
      style={style}
      fill="currentColor"
      aria-hidden="true"
      focusable="false"
    >
      <path d="M100 336 L100 150" stroke="currentColor" strokeWidth="4" fill="none" strokeLinecap="round" />
      <path
        d="M100 12
           C 142 34, 176 76, 178 122
           C 162 120, 148 126, 140 138
           C 168 150, 184 178, 180 208
           C 162 202, 146 206, 138 218
           C 160 236, 166 268, 152 300
           C 130 286, 114 288, 100 306
           C 86 288, 70 286, 48 300
           C 34 268, 40 236, 62 218
           C 54 206, 38 202, 20 208
           C 16 178, 32 150, 60 138
           C 52 126, 38 120, 22 122
           C 24 76, 58 34, 100 12 Z"
      />
      <path
        d="M100 22 L100 300"
        stroke="currentColor"
        strokeWidth="3"
        fill="none"
        strokeLinecap="round"
        opacity="0.35"
      />
    </svg>
  );
}

export function VineDivider({ className, style }: BotanicalProps) {
  const leaves = [90, 220, 360, 500, 640, 780, 920, 1060, 1140];
  return (
    <svg
      viewBox="0 0 1200 60"
      className={className}
      style={style}
      fill="currentColor"
      preserveAspectRatio="none"
      aria-hidden="true"
      focusable="false"
    >
      <path
        d="M0 30 C 200 6, 400 54, 600 30 C 800 6, 1000 54, 1200 30"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        opacity="0.6"
      />
      {leaves.map((x, i) => (
        <ellipse
          key={i}
          cx={x}
          cy={30}
          rx="20"
          ry="6"
          transform={`rotate(${i % 2 === 0 ? -28 : 28} ${x} 30)`}
          opacity="0.6"
        />
      ))}
    </svg>
  );
}
