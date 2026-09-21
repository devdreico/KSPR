import React from "react";

type BotanicalProps = {
  className?: string;
  style?: React.CSSProperties;
};

/* Hojas: origen en el punto de inserción (0,0), punta en (0,-100). */
const BROAD_LEAF =
  "M0 0 C -20 -12 -31 -32 -30 -54 C -29 -76 -16 -93 0 -100 C 17 -93 31 -76 32 -54 C 33 -32 20 -12 0 0 Z";

const NARROW_LEAF =
  "M0 0 C -10 -16 -14 -50 -11 -76 C -9 -92 -5 -100 0 -100 C 5 -100 9 -92 11 -76 C 14 -50 10 -16 0 0 Z";

const MONSTERA_LEAF =
  "M100 14 C 124 18 146 32 158 52 C 172 72 181 88 181 102 " +
  "C 168 102 158 104 148 106 C 164 116 176 128 180 142 " +
  "C 182 156 179 166 178 172 C 166 170 158 172 152 174 " +
  "C 166 184 174 194 176 204 C 177 214 172 219 168 223 " +
  "C 156 220 142 224 132 228 C 126 244 116 254 100 258 " +
  "C 84 254 76 246 70 238 C 60 242 50 246 40 244 " +
  "C 30 232 26 216 28 206 C 35 202 42 199 48 196 " +
  "C 34 188 25 178 23 166 C 21 152 20 140 20 130 " +
  "C 30 132 42 133 52 134 C 40 124 28 112 23 98 " +
  "C 20 82 24 68 34 54 C 48 34 74 20 100 14 Z " +
  "M120 128 a7 11 0 1 0 14 0 a7 11 0 1 0 -14 0 Z " +
  "M72 200 a6 10 0 1 0 12 0 a6 10 0 1 0 -12 0 Z";

type LeafTransform = { x: number; y: number; r: number; s: number };

export function LeafBranch({ className, style }: BotanicalProps) {
  const leaves: LeafTransform[] = [
    { x: 99, y: 306, r: -66, s: 0.5 },
    { x: 104, y: 272, r: 60, s: 0.47 },
    { x: 97, y: 238, r: -63, s: 0.44 },
    { x: 94, y: 202, r: 58, s: 0.41 },
    { x: 99, y: 166, r: -62, s: 0.38 },
    { x: 102, y: 130, r: 56, s: 0.34 },
    { x: 99, y: 96, r: -60, s: 0.3 },
    { x: 101, y: 62, r: 52, s: 0.25 },
    { x: 100, y: 30, r: -4, s: 0.19 },
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
        className="botanical-stem"
        pathLength={1}
        d="M100 338 C 94 286 106 236 99 186 C 93 140 104 92 100 20"
        fill="none"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
      />
      {leaves.map((leaf, i) => (
        <g key={i} transform={`translate(${leaf.x} ${leaf.y}) rotate(${leaf.r}) scale(${leaf.s})`}>
          <path
            className="botanical-leaf"
            style={{ animationDelay: `${0.35 + i * 0.22}s` }}
            d={BROAD_LEAF}
          />
        </g>
      ))}
    </svg>
  );
}

export function Fern({ className, style }: BotanicalProps) {
  const levels = Array.from({ length: 14 }, (_, i) => {
    const t = i / 13;
    return {
      y: 300 - t * 258,
      x: 100 + Math.sin(t * 3.1) * 4,
      scale: 0.42 - t * 0.31,
      rot: 70 + t * 10,
    };
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
        className="botanical-stem"
        pathLength={1}
        d="M100 336 C 96 258 104 160 100 18"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
      />
      {levels.map((p, i) => (
        <g key={i}>
          <g transform={`translate(${p.x} ${p.y}) rotate(${-p.rot}) scale(${p.scale})`}>
            <path
              className="botanical-leaf"
              style={{ animationDelay: `${0.4 + i * 0.12}s` }}
              d={NARROW_LEAF}
            />
          </g>
          <g transform={`translate(${p.x} ${p.y - 4}) rotate(${p.rot - 4}) scale(${p.scale * 0.92})`}>
            <path
              className="botanical-leaf"
              style={{ animationDelay: `${0.46 + i * 0.12}s` }}
              d={NARROW_LEAF}
            />
          </g>
        </g>
      ))}
      <g transform="translate(100 40) rotate(-3) scale(0.16)">
        <path className="botanical-leaf" style={{ animationDelay: "0.3s" }} d={NARROW_LEAF} />
      </g>
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
      <path
        className="botanical-stem"
        pathLength={1}
        d="M100 338 C 100 306 99 284 100 256"
        fill="none"
        stroke="currentColor"
        strokeWidth="5"
        strokeLinecap="round"
      />
      <path
        className="botanical-leaf"
        style={{ animationDelay: "0.35s" }}
        d={MONSTERA_LEAF}
        fillRule="evenodd"
      />
    </svg>
  );
}

export function Sprig({ className, style }: BotanicalProps) {
  const leaves: LeafTransform[] = [
    { x: 22, y: 46, r: -34, s: 0.3 },
    { x: 60, y: 38, r: 28, s: 0.3 },
    { x: 100, y: 31, r: -32, s: 0.28 },
    { x: 142, y: 24, r: 26, s: 0.24 },
    { x: 184, y: 18, r: -30, s: 0.2 },
  ];

  return (
    <svg
      viewBox="0 0 240 60"
      className={className}
      style={style}
      fill="currentColor"
      aria-hidden="true"
      focusable="false"
    >
      <path
        className="botanical-stem"
        pathLength={1}
        d="M2 50 C 60 42 130 30 238 8"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
      {leaves.map((leaf, i) => (
        <g key={i} transform={`translate(${leaf.x} ${leaf.y}) rotate(${leaf.r}) scale(${leaf.s})`}>
          <path
            className="botanical-leaf"
            style={{ animationDelay: `${0.3 + i * 0.18}s` }}
            d={BROAD_LEAF}
          />
        </g>
      ))}
    </svg>
  );
}
