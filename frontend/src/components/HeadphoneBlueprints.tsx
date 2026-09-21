import React from "react";

type BlueprintProps = { index: number };

function Grid() {
  const minor: number[] = [];
  const major: number[] = [];
  for (let x = 20; x < 560; x += 20) minor.push(x);
  for (let y = 20; y < 380; y += 20) minor.push(y);
  for (let x = 100; x < 560; x += 100) major.push(x);
  for (let y = 100; y < 380; y += 100) major.push(y);

  return (
    <g>
      <g className="bp-grid-minor">
        {minor.map((x, i) => (
          <line key={`v${i}`} x1={x} y1={0} x2={x} y2={380} />
        ))}
        {minor.map((y, i) => (
          <line key={`h${i}`} x1={0} y1={y} x2={560} y2={y} />
        ))}
      </g>
      <g className="bp-grid-major">
        {major.map((x, i) => (
          <line key={`V${i}`} x1={x} y1={0} x2={x} y2={380} />
        ))}
        {major.map((y, i) => (
          <line key={`H${i}`} x1={0} y1={y} x2={560} y2={y} />
        ))}
      </g>
    </g>
  );
}

function Tag({ x, y, n }: { x: number; y: number; n: number }) {
  return (
    <g>
      <circle className="bp-tag" cx={x} cy={y} r="7" />
      <text className="bp-tag-num" x={x} y={y + 2.7} textAnchor="middle">
        {n}
      </text>
    </g>
  );
}

function Note({
  n,
  x,
  y,
  tx,
  ty,
  label,
  anchor = "start",
}: {
  n: number;
  x: number;
  y: number;
  tx: number;
  ty: number;
  label: string;
  anchor?: "start" | "end";
}) {
  return (
    <g>
      <path className="bp-leader" d={`M${x} ${y} L${tx} ${ty}`} />
      <Tag x={tx} y={ty} n={n} />
      <text
        className="bp-label"
        x={anchor === "start" ? tx + 12 : tx - 12}
        y={ty + 3.2}
        textAnchor={anchor}
      >
        {label}
      </text>
    </g>
  );
}

function DimH({ x1, x2, y, label }: { x1: number; x2: number; y: number; label: string }) {
  return (
    <g className="bp-dim">
      <line x1={x1} y1={y} x2={x2} y2={y} />
      <line x1={x1 - 3} y1={y + 3} x2={x1 + 3} y2={y - 3} />
      <line x1={x2 - 3} y1={y + 3} x2={x2 + 3} y2={y - 3} />
      <text className="bp-label" x={(x1 + x2) / 2} y={y - 5} textAnchor="middle">
        {label}
      </text>
    </g>
  );
}

function DimV({ y1, y2, x, label }: { y1: number; y2: number; x: number; label: string }) {
  const cy = (y1 + y2) / 2;
  return (
    <g className="bp-dim">
      <line x1={x} y1={y1} x2={x} y2={y2} />
      <line x1={x - 3} y1={y1 + 3} x2={x + 3} y2={y1 - 3} />
      <line x1={x - 3} y1={y2 + 3} x2={x + 3} y2={y2 - 3} />
      <text className="bp-label" x={x - 5} y={cy} textAnchor="middle" transform={`rotate(-90 ${x - 5} ${cy})`}>
        {label}
      </text>
    </g>
  );
}

function HFlow({ x1, x2, y, label }: { x1: number; x2: number; y: number; label?: string }) {
  const dir = x2 > x1 ? 1 : -1;
  return (
    <g className="bp-flow">
      <line x1={x1} y1={y} x2={x2 - dir * 6} y2={y} />
      <path d={`M${x2} ${y} l${-7 * dir} -3.2 l0 6.4 Z`} />
      {label && (
        <text className="bp-micro" x={(x1 + x2) / 2} y={y - 4} textAnchor="middle">
          {label}
        </text>
      )}
    </g>
  );
}

function Frame({ children, title, scale }: { children: React.ReactNode; title: string; scale: string }) {
  return (
    <svg viewBox="0 0 560 380" className="blueprint" role="img" aria-label={title}>
      <Grid />
      {children}
      <g className="bp-title-block">
        <rect x="368" y="330" width="180" height="40" />
        <line x1="368" y1="350" x2="548" y2="350" />
        <line x1="470" y1="350" x2="470" y2="370" />
        <text className="bp-label bp-label-hi" x="376" y="344">
          {title}
        </text>
        <text className="bp-label" x="376" y="364">
          {scale}
        </text>
        <text className="bp-label" x="478" y="364">
          KSPR ENG
        </text>
      </g>
    </svg>
  );
}

function DriverBlueprint() {
  let trace = "M176 178";
  for (let i = 0; i < 20; i += 1) {
    trace += ` q6 ${i % 2 === 0 ? -7 : 7} 12 0`;
  }

  return (
    <Frame title="DRIVER PLANAR · SECCIÓN A-A" scale="ESC 4:1">
      <rect className="bp-frame" x="150" y="96" width="300" height="176" rx="10" />
      <rect className="bp-line" x="168" y="114" width="264" height="140" rx="4" />
      <rect className="bp-fill" x="150" y="96" width="18" height="176" />
      <rect className="bp-fill" x="432" y="96" width="18" height="176" />

      {Array.from({ length: 7 }, (_, i) => {
        const x = 176 + i * 36;
        return (
          <g key={i}>
            <rect className={i % 2 ? "bp-mag-b" : "bp-mag-a"} x={x} y="122" width="30" height="16" />
            <text className="bp-micro" x={x + 15} y="133" textAnchor="middle">
              {i % 2 ? "S" : "N"}
            </text>
            <rect className={i % 2 ? "bp-mag-a" : "bp-mag-b"} x={x} y="230" width="30" height="16" />
            <text className="bp-micro" x={x + 15} y="241" textAnchor="middle">
              {i % 2 ? "N" : "S"}
            </text>
          </g>
        );
      })}

      <path className="bp-accent" d="M168 184 Q300 174 432 184" fill="none" />
      <path className="bp-trace" d={trace} fill="none" />
      <line className="bp-dash" x1="300" y1="104" x2="300" y2="264" />

      <DimH x1={150} x2={450} y={300} label="106.0 mm" />
      <DimV y1={96} y2={272} x={116} label="Ø 68.0 mm" />

      <Note n={1} x={210} y={130} tx={128} ty={62} label="IMÁN N52" anchor="end" />
      <Note n={2} x={392} y={180} tx={520} ty={62} label="DIAFRAGMA 1.5 µm" anchor="end" />
      <Note n={3} x={232} y={190} tx={128} ty={318} label="PISTA SERPENTINA Al" anchor="end" />
      <Note n={4} x={441} y={252} tx={452} ty={318} label="MARCO Ti" />
    </Frame>
  );
}

function CircuitBlueprint() {
  return (
    <Frame title="CADENA DSP / DAC · BLOQUES" scale="DIAGRAMA 1:1">
      <rect className="bp-frame" x="62" y="92" width="436" height="196" rx="12" />
      {[
        [80, 110],
        [480, 110],
        [80, 270],
        [480, 270],
      ].map(([cx, cy], i) => (
        <g key={i}>
          <circle className="bp-line" cx={cx} cy={cy} r="5" />
          <circle className="bp-dash" cx={cx} cy={cy} r="8" />
        </g>
      ))}

      <rect className="bp-fill" x="78" y="166" width="46" height="42" rx="4" />
      <text className="bp-micro" x="101" y="190" textAnchor="middle">
        USB-C
      </text>

      <rect className="bp-fill" x="152" y="160" width="64" height="50" rx="4" />
      <text className="bp-label bp-label-hi" x="184" y="189" textAnchor="middle">
        XU208
      </text>

      <rect className="bp-fill" x="248" y="146" width="76" height="78" rx="4" />
      <text className="bp-label bp-label-hi" x="286" y="182" textAnchor="middle">
        SoC
      </text>

      <rect className="bp-fill" x="356" y="130" width="66" height="46" rx="4" />
      <text className="bp-label" x="389" y="157" textAnchor="middle">
        DAC L
      </text>

      <rect className="bp-fill" x="356" y="206" width="66" height="46" rx="4" />
      <text className="bp-label" x="389" y="233" textAnchor="middle">
        DAC R
      </text>

      <rect className="bp-fill" x="452" y="150" width="64" height="82" rx="4" />
      <text className="bp-label" x="484" y="186" textAnchor="middle">
        I/V
      </text>
      <text className="bp-label" x="484" y="200" textAnchor="middle">
        BAL
      </text>

      <HFlow x1={124} x2={152} y={187} label="UAC2" />
      <HFlow x1={216} x2={248} y={187} label="I²S" />
      <HFlow x1={324} x2={356} y={153} label="I²S" />
      <HFlow x1={324} x2={356} y={229} label="I²S" />
      <HFlow x1={422} x2={452} y={173} label="ΔΣ" />
      <HFlow x1={516} x2={544} y={191} label="OUT" />

      <circle className="bp-line" cx="290" cy="252" r="15" />
      <text className="bp-micro" x="290" y="255" textAnchor="middle">
        MCLK
      </text>
      <path className="bp-lead-line" d="M290 237 L290 224" stroke="#6a6a6a" strokeWidth="1" fill="none" />
      <line className="bp-dash" x1="290" y1="267" x2="290" y2="286" />

      {[80, 108, 136].map((x, i) => (
        <rect key={i} className="bp-fill-dark" x={x} y="272" width="16" height="9" rx="2" />
      ))}

      <DimH x1={62} x2={498} y={312} label="PCB 42 × 28 mm" />

      <Note n={1} x={184} y={160} tx={128} ty={64} label="XMOS / UAC2 384 kHz" anchor="end" />
      <Note n={2} x={389} y={176} tx={540} ty={64} label="DAC DIFERENCIAL 32-bit" anchor="end" />
      <Note n={3} x={484} y={232} tx={540} ty={318} label="SNR 128 dB" anchor="end" />
      <Note n={4} x={290} y={267} tx={150} ty={318} label="RELOJ MAESTRO" anchor="end" />
    </Frame>
  );
}

function AcousticBlueprint() {
  return (
    <Frame title="CÁMARA ACÚSTICA · CORTE B-B" scale="ESC 3:2">
      <rect className="bp-frame" x="70" y="70" width="400" height="240" rx="36" />
      <rect className="bp-fill" x="86" y="92" width="28" height="88" rx="14" />
      <rect className="bp-fill" x="86" y="200" width="28" height="88" rx="14" />
      <path className="bp-dash" d="M70 150 a30 30 0 0 0 0 80" fill="none" />

      <rect className="bp-fill" x="344" y="110" width="18" height="160" rx="3" />
      {Array.from({ length: 7 }, (_, i) => (
        <line key={i} className="bp-line" x1="344" y1={122 + i * 23} x2="362" y2={122 + i * 23} />
      ))}

      {Array.from({ length: 6 }, (_, i) => {
        const y = 118 + i * 26;
        return <path key={i} className="bp-fill-dark" d={`M344 ${y} L272 ${y + 13} L344 ${y + 26} Z`} />;
      })}

      <line className="bp-dash" x1="378" y1="96" x2="378" y2="284" />

      <path className="bp-wave" d="M336 150 q-42 -26 -62 6" />
      <path className="bp-wave" d="M336 186 q-52 -30 -66 8" />
      <path className="bp-wave" d="M336 222 q-42 -26 -62 6" />

      <DimV y1={110} y2={270} x={496} label="Ø 62 mm" />
      <DimH x1={272} x2={344} y={312} label="FAZOR 12.5 mm" />

      <Note n={1} x={100} y={130} tx={132} ty={56} label="PAD VISCOELÁSTICO" anchor="end" />
      <Note n={2} x={330} y={118} tx={420} ty={56} label="FAZOR Ti" />
      <Note n={3} x={353} y={250} tx={545} ty={318} label="DRIVER PLANAR" anchor="end" />
      <Note n={4} x={378} y={110} tx={150} ty={318} label="REJILLA Ti" anchor="end" />
    </Frame>
  );
}

function MechanicalBlueprint() {
  return (
    <Frame title="ENSAMBLE EXPLOSIONADO" scale="TOL ±0.05 mm">
      <line className="bp-dash" x1="280" y1="24" x2="280" y2="356" />

      <path className="bp-thick" d="M190 76 Q280 8 370 76" fill="none" />
      <rect className="bp-fill" x="180" y="68" width="20" height="16" rx="5" />
      <rect className="bp-fill" x="360" y="68" width="20" height="16" rx="5" />

      <path className="bp-line" d="M240 104 v26 q0 8 8 8 h64 q8 0 8 -8 v-26" fill="none" strokeWidth="2" />
      <circle className="bp-line" cx="280" cy="182" r="26" />
      <circle className="bp-dash" cx="280" cy="182" r="19" />

      <ellipse className="bp-fill" cx="280" cy="236" rx="54" ry="27" />
      <ellipse className="bp-dash" cx="280" cy="236" rx="42" ry="19" />

      <circle className="bp-fill" cx="280" cy="288" r="16" />
      <circle className="bp-line" cx="280" cy="288" r="8" />
      {[0, 90, 180, 270].map((a, i) => (
        <circle
          key={i}
          className="bp-mag-a"
          cx={280 + 20 * Math.cos((a * Math.PI) / 180)}
          cy={288 + 20 * Math.sin((a * Math.PI) / 180)}
          r="4"
        />
      ))}

      <ellipse className="bp-fill" cx="280" cy="332" rx="50" ry="15" />
      <ellipse className="bp-dash" cx="280" cy="332" rx="34" ry="8" />

      <DimV y1={76} y2={332} x={132} label="Ø 210 mm" />

      <g className="bp-detail">
        <circle className="bp-line" cx="466" cy="238" r="34" />
        <circle className="bp-line" cx="466" cy="238" r="12" />
        <line className="bp-line" x1="454" y1="238" x2="478" y2="238" />
        <line className="bp-line" x1="466" y1="226" x2="466" y2="250" />
        <path className="bp-dash" d="M432 238 h-16" fill="none" />
        <text className="bp-label" x="466" y="290" textAnchor="middle">
          DETALLE B
        </text>
        <text className="bp-micro" x="466" y="302" textAnchor="middle">
          M2 · Ti Grado 5
        </text>
      </g>

      <Note n={1} x={200} y={66} tx={150} ty={44} label="ARCO Ti" anchor="end" />
      <Note n={2} x={252} y={116} tx={150} ty={112} label="YOKE Al" anchor="end" />
      <Note n={3} x={306} y={182} tx={360} ty={112} label="GIMBAL 6061" />
      <Note n={4} x={226} y={236} tx={150} ty={236} label="CARCASA Al" anchor="end" />
      <Note n={5} x={296} y={288} tx={360} ty={236} label="DRIVER 106 mm" />
      <Note n={6} x={230} y={332} tx={150} ty={330} label="PAD" anchor="end" />
    </Frame>
  );
}

const BLUEPRINTS = [DriverBlueprint, CircuitBlueprint, AcousticBlueprint, MechanicalBlueprint];

export function HeadphoneBlueprint({ index }: BlueprintProps) {
  const Drawing = BLUEPRINTS[index] ?? BLUEPRINTS[0];
  return <Drawing />;
}
