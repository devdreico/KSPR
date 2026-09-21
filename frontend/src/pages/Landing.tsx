import React, { useState } from "react";
import { Terminal, Copy, Check, Sparkles, Shield, FolderArchive, Cpu, ExternalLink, Monitor, CreditCard, Zap, Layers, Activity, Search } from "lucide-react";
import { LeafBranch, Fern, MonsteraLeaf, VineDivider } from "../components/Botanical";
import { Typewriter } from "../components/Typewriter";
import { useAtmosphere, useReveal, useTilt } from "../hooks/useInteractions";

const marqueeItems = [
  "PARSING ESTÁTICO",
  "CONTEXT TREES",
  "MULTI-LLM",
  "MCP SERVERS",
  "AST / TREE-SITTER",
  "EVIDENCE-FIRST",
  "REVERSE ENGINEERING",
  "MARKDOWN MODULAR",
  "gsap-skills",
  "AUDITABLE",
];

export function Landing() {
  const [copiedCmd, setCopiedCmd] = useState<string | null>(null);
  const [terminalTab, setTerminalTab] = useState<"install" | "analyze" | "git" | "dev">("install");
  const [decompTab, setDecompTab] = useState<number>(0);
  const [runningSim, setRunningSim] = useState(false);
  const [simStep, setSimStep] = useState(0);

  useReveal();
  useAtmosphere();
  useTilt();

  const curlCommand = "curl -fsSL https://raw.githubusercontent.com/devdreiortiz/KSPR/main/bin/install.sh | bash";

  const copyToClipboard = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedCmd(key);
    setTimeout(() => setCopiedCmd(null), 2000);
  };

  const runSimulation = () => {
    if (runningSim) return;
    setRunningSim(true);
    setSimStep(1);
    setTimeout(() => setSimStep(2), 900);
    setTimeout(() => setSimStep(3), 1800);
    setTimeout(() => {
      setSimStep(4);
      setRunningSim(false);
    }, 2700);
  };

  const delay = (i: number) => ({ "--d": `${(i * 0.09).toFixed(2)}s` } as React.CSSProperties);

  const headphoneDecompParts = [
    {
      title: "1. Transductores Planar-Magnéticos",
      subtitle: "Arquitectura de Inducción y Diafragma Sub-Micrónico",
      desc: "Desensamblaje estático de esquemáticos y notas de ingeniería acústica. KSPR decompila las especificaciones del diafragma de polimida de 1.5 micras, el patrón de grabado serpentino de aluminio y la simetría del arreglo magnético push-pull de neodimio N52 (1.5 Tesla).",
      command: "kspr /decompilate ./audifonos/esquematicos.pdf ./audifonos/drivers.cad --target hi-fi",
      output: "[Context Tree Generado]\n└── Context Trees/Hardware - Audifonos Planar HiFi/\n    ├── Contexto inicial.md (Topología y respuesta 5Hz-50kHz)\n    └── transductores_y_magnetismo.md (Flujo magnético y THD < 0.05%)"
    },
    {
      title: "2. Circuitería DSP y DAC",
      subtitle: "Decodificación Digital, Filtros FIR y Ganancia Dinámica",
      desc: "Análisis estático de firmware y diagramas de bloques del procesador de señal digital. KSPR extrae la topología de conversión D/A diferencial, la gestión de muestreo UAC2 (32-bit/384kHz) y las tablas de calibración de fase.",
      command: "kspr /decompilate ./firmware/dsp_registers.json ./specs/dac_topology.md",
      output: "[Context Tree Generado]\n└── Context Trees/Hardware - Audifonos Planar HiFi/\n    └── circuiteria_dsp_dac.md (Registros I2S, filtros de fase y SNR 128dB)"
    },
    {
      title: "3. Cámaras Acústicas y Difusores Fazor",
      subtitle: "Control de Ondas Estacionarias y Guías de Onda",
      desc: "Ingeniería inversa de volúmenes de resonancia circumaural y rejillas aerodinámicas de titanio. El motor agéntico calcula coeficientes de difracción y mapea la atenuación de reflexiones internas.",
      command: "kspr /decompilate https://docs.audio-engineering.org/fazor-waveguides --extract-geometry",
      output: "[Context Tree Generado]\n└── Context Trees/Hardware - Audifonos Planar HiFi/\n    └── acustica_y_camaras_resonancia.md (Guías Fazor y atenuación modal)"
    },
    {
      title: "4. Ensamble Mecánico y Materiales",
      subtitle: "Tolerancias Térmicas, Aleaciones de Titanio y Ergonomía",
      desc: "Procesamiento de planos mecánicos y diagramas de despiece CATIA/STEP. KSPR clasifica los puntos de esfuerzo estructural, la densidad de las almohadillas de polímero viscoelástico y la distribución de masa.",
      command: "kspr /decompilate ./cad/chassis_assembly.step ./specs/materials.txt",
      output: "[Context Tree Generado]\n└── Context Trees/Hardware - Audifonos Planar HiFi/\n    └── ensamble_mecanico_materiales.md (Chasis de titanio, torque y fatiga)"
    }
  ];

  return (
    <div className="app-shell animate-fade-in" style={{ fontFamily: "'Montserrat', sans-serif" }}>
      <div className="scroll-progress" aria-hidden="true" />
      <div className="cursor-glow" aria-hidden="true" />
      <div className="grain" aria-hidden="true" />
      <span className="side-note" aria-hidden="true">SOVERATH HOLDING · BOGOTÁ D.C. · EST. KSPR</span>

      {/* Topbar */}
      <header className="topbar">
        <div className="brand">
          <img src="/casper-ai-logo.png" alt="KSPR AI CLI TOOL" className="brand-logo" />
          <div>
            <strong style={{ fontWeight: 700 }}>KSPR CLI</strong>
            <span style={{ fontWeight: 500 }}>Knowledge Source Parsing &amp; Reconstruction · v0.1.0</span>
          </div>
        </div>

        <div className="topbar-right">
          <div className="institute-badge">
            <span style={{ fontWeight: 500 }}>Soverath Holding</span>
            <strong style={{ fontWeight: 700 }}>Bogotá D.C. - CO</strong>
          </div>
          <a
            href="https://kspr.desktop.presentto.online"
            target="_blank"
            rel="noreferrer"
            className="desktop-link-btn"
          >
            <Monitor size={15} color="#ffffff" />
            <span>KSPR AI DESKTOP</span>
            <ExternalLink size={13} style={{ opacity: 0.8 }} />
          </a>
        </div>
      </header>

      {/* Main Content */}
      <main>
        {/* Hero Section */}
        <section className="hero">
          <div className="glow-orb" aria-hidden="true" />
          <div className="hero-beam" aria-hidden="true" />
          <Fern className="botanical botanical-fern-left" />
          <LeafBranch className="botanical botanical-branch-right" />

          <div className="motes" aria-hidden="true">
            {Array.from({ length: 14 }, (_, i) => (
              <span
                key={i}
                className="mote"
                style={{
                  left: `${(i * 7 + 2) % 96}%`,
                  animationDelay: `${(i * 0.9).toFixed(1)}s`,
                  animationDuration: `${(12 + (i % 5) * 2).toFixed(0)}s`,
                }}
              />
            ))}
          </div>

          <div className="hero-content">
            <div className="section-tag">
              <Sparkles size={14} /> KSPR AI CLI TOOL · PARSING Y RECONSTRUCCIÓN DE CONOCIMIENTO
            </div>

            <h1 style={{ fontWeight: 700 }}>
              Descompón sistemas complejos y reconstruye su conocimiento técnico <em style={{ fontWeight: 400 }}>desde la terminal</em>.
            </h1>

            <p style={{ fontWeight: 400 }}>
              Herramienta de línea de comandos para analizar repositorios, esquemáticos, PDFs técnicos, imágenes y enlaces web sin ejecutar el artefacto. KSPR AI CLI TOOL conserva la evidencia, separa hechos de inferencias y genera árboles de conocimiento auditables para comprender, documentar y reconstruir procesos.
            </p>

            {/* Action Strip: Curl + Membership Side-by-Side */}
            <div className="action-strip">
              <div className="install-box" data-tilt>
                <div style={{ display: "flex", alignItems: "center", gap: 12, overflow: "hidden" }}>
                  <Terminal size={19} color="#ffffff" style={{ flexShrink: 0 }} />
                  <code style={{ whiteSpace: "nowrap", overflowX: "auto", fontFamily: "'Montserrat', sans-serif", fontSize: "13px" }}>{curlCommand}</code>
                </div>
                <button
                  onClick={() => copyToClipboard(curlCommand, "curl-install")}
                  className="copy-btn"
                  aria-label="Copiar comando de instalación"
                  title="Copiar comando de instalación"
                >
                  {copiedCmd === "curl-install" ? <Check size={14} color="#000000" /> : <Copy size={14} />}
                  <span style={{ fontWeight: 700 }}>{copiedCmd === "curl-install" ? "Copiado" : "Copiar cURL"}</span>
                </button>
              </div>

              <a
                href="https://kspr.comunity.vercel.app"
                target="_blank"
                rel="noreferrer"
                className="membership-card-btn"
                data-tilt
              >
                <CreditCard size={22} color="#ffffff" />
                <div className="membership-info">
                  <strong style={{ fontWeight: 700 }}>KSPR MEMBERSHIP</strong>
                  <span style={{ fontWeight: 500 }}>One-Time Purchase ↗</span>
                </div>
              </a>
            </div>

            <div className="hero-cue" aria-hidden="true">
              <span />
            </div>
          </div>
        </section>

        {/* KSPR Desktop Highlight Banner */}
        <div className="desktop-banner" data-reveal>
          <MonsteraLeaf className="botanical botanical-monstera" />
          <div className="banner-content">
            <div className="desktop-banner-eyebrow">
              <Zap size={15} /> CLIENTE NATIVO DE ESCRITORIO DISPONIBLE
            </div>
            <h3>KSPR AI Desktop — Entorno visual para explorar el conocimiento</h3>
            <p>
              ¿Prefieres explorar sesiones, grafos y servidores MCP desde una interfaz visual? Accede al cliente de escritorio de KSPR AI CLI TOOL.
            </p>
          </div>
          <a
            href="https://kspr.desktop.presentto.online"
            target="_blank"
            rel="noreferrer"
            className="desktop-banner-cta"
          >
            <span>Abrir kspr.desktop.presentto.online</span>
            <ExternalLink size={15} />
          </a>
        </div>

        {/* Kinetic marquee */}
        <div className="marquee" aria-hidden="true">
          <div className="marquee-track">
            {[...marqueeItems, ...marqueeItems].map((item, i) => (
              <span key={i} className="marquee-item">
                {item}
                <i />
              </span>
            ))}
          </div>
        </div>

        {/* Real Workflows & Exploration Areas */}
        <section style={{ margin: "60px 0" }} data-reveal>
          <div className="section-head">
            <span className="section-index" aria-hidden="true">01</span>
            <div>
              <span className="eyebrow">CAMPOS DE APLICACIÓN INDUSTRIAL</span>
              <h2 className="section-title">Flujos de trabajo reales donde KSPR destaca</h2>
            </div>
          </div>

          <div className="grid-cards">
            <div className="card reveal-fade" data-tilt data-reveal style={delay(0)}>
              <Shield size={28} color="#ffffff" />
              <h3 style={{ fontWeight: 700 }}>1. Evidencia estática y trazabilidad</h3>
              <p>
                Inspecciona software crítico y repositorios legados sin ejecutar el código. KSPR rastrea entradas, handlers y puntos sensibles mediante AST y análisis sintáctico, conservando las referencias que sostienen cada hallazgo.
              </p>
            </div>

            <div className="card reveal-fade" data-tilt data-reveal style={delay(1)}>
              <Layers size={28} color="#a3a3a3" />
              <h3 style={{ fontWeight: 700 }}>2. Parsing multi-fuente con /decompilate</h3>
              <p>
                Reúne PDFs, imágenes, notas y enlaces en un mismo análisis. KSPR agrupa la evidencia y genera árboles de contexto estructurados en carpetas Markdown que pueden revisarse y ampliarse.
              </p>
            </div>

            <div className="card reveal-fade" data-tilt data-reveal style={delay(2)}>
              <Cpu size={28} color="#6f6f6f" />
              <h3 style={{ fontWeight: 700 }}>3. Orquestación de modelos y capacidades</h3>
              <p>
                Coordina proveedores de IA, MCP, plugins y capabilities con permisos explícitos. Las iteraciones contrastan hipótesis, riesgos y contradicciones sin confundir una inferencia con una prueba.
              </p>
            </div>
          </div>
        </section>

        <div className="divider-wrap" aria-hidden="true">
          <VineDivider className="vine" />
        </div>

        {/* Cinematic Hardware Decomposition Example (Planar Headphones) */}
        <section className="decomp-container" data-reveal>
          <div className="glow-orb" aria-hidden="true" />
          <div className="section-head">
            <span className="section-index" aria-hidden="true">02</span>
            <div>
              <span className="eyebrow">DEMOSTRACIÓN DE CAPACIDAD TÉCNICA</span>
              <h2 style={{ fontSize: "26px", margin: "6px 0 0", fontWeight: 700 }}>Demostración: reconstrucción técnica de unos audífonos planar Hi-Fi</h2>
            </div>
            <span style={{ color: "var(--muted)", fontSize: "12px", fontWeight: 500 }}>Soverath Holding · Bogotá D.C.</span>
          </div>

          <div className="decomp-tabs">
            {headphoneDecompParts.map((part, idx) => (
              <button
                key={idx}
                onClick={() => setDecompTab(idx)}
                className={`decomp-tab ${decompTab === idx ? "active" : ""}`}
              >
                {part.title}
              </button>
            ))}
          </div>

          <div className="decomp-grid">
            <div className="decomp-panel">
              <h4>{headphoneDecompParts[decompTab].title}</h4>
              <div className="decomp-subtitle">{headphoneDecompParts[decompTab].subtitle}</div>
              <p>{headphoneDecompParts[decompTab].desc}</p>
              <div className="decomp-command">$ {headphoneDecompParts[decompTab].command}</div>
            </div>

            <div className="decomp-panel-alt">
              <div className="decomp-output-label"># Evidencia estructurada generada:</div>
              <div className="decomp-output" key={decompTab}>
                {headphoneDecompParts[decompTab].output.split("\n").map((line, i) => (
                  <div key={i} className="decomp-line" style={{ animationDelay: `${i * 0.12}s` }}>
                    {line || "\u00A0"}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* Terminal Simulation Section */}
        <section style={{ margin: "60px 0" }} data-reveal>
          <div className="section-head">
            <span className="section-index" aria-hidden="true">03</span>
            <div>
              <span className="eyebrow">TERMINAL CLI</span>
              <h2 className="section-title">Recorrido interactivo del flujo de análisis</h2>
            </div>
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              <button
                onClick={() => setTerminalTab("install")}
                className={`decomp-tab ${terminalTab === "install" ? "active" : ""}`}
              >
                1. cURL Install
              </button>
              <button
                onClick={() => setTerminalTab("analyze")}
                className={`decomp-tab ${terminalTab === "analyze" ? "active" : ""}`}
              >
                2. /decompilate
              </button>
              <button
                onClick={() => setTerminalTab("git")}
                className={`decomp-tab ${terminalTab === "git" ? "active" : ""}`}
              >
                3. /trees
              </button>
              <button
                onClick={() => setTerminalTab("dev")}
                className={`decomp-tab ${terminalTab === "dev" ? "active" : ""}`}
              >
                4. Shell KSPR AI CLI TOOL
              </button>
            </div>
          </div>

          <div className="terminal-window">
            <div className="terminal-header">
              <div className="terminal-dots">
                <span className="dot-r" />
                <span className="dot-y" />
                <span className="dot-g" />
                <span style={{ marginLeft: 10, fontSize: "13px", fontWeight: 500, color: "#a3a3a3" }}>kspr@soverath-bogota:~</span>
              </div>
              <button
                onClick={runSimulation}
                disabled={runningSim}
                className="terminal-run-btn"
              >
                {runningSim ? "Ejecutando proceso..." : "▶ Simular Ejecución"}
              </button>
            </div>

            <div className="terminal-body" key={terminalTab}>
              {terminalTab === "install" && (
                <div className="term-block">
                  <div className="term-comment"># Instalación desatendida mediante script Bash oficial</div>
                  <div className="term-cmd">$ <Typewriter text={curlCommand} speed={12} /></div>
                  <div className="term-ok" style={{ marginTop: "14px" }}>
                    ✓ Clonación segura en ~/.kspr<br />
                    ✓ Entorno virtual Python aislado (.venv)<br />
                    ✓ Enlace ejecutable creado en ~/.local/bin/kspr
                  </div>
                </div>
              )}

              {terminalTab === "analyze" && (
                <div className="term-block">
                  <div className="term-comment"># Ingesta multi-fuente y compilación de Context Trees</div>
                  <div className="term-cmd">$ <Typewriter text="kspr /decompilate ./specs.pdf ./diagram.png https://docs.api.com" speed={16} /></div>
                  {simStep >= 1 && <div className="term-step">[1/3] Fuentes indexadas y subidas a staging workspace.</div>}
                  {simStep >= 2 && <div className="term-step">[2/3] Análisis agéntico con KSPR AI CLI TOOL y extracción heurística...</div>}
                  {simStep >= 3 && <div className="term-comment" style={{ marginTop: "6px" }}>[3/3] Generación de Contexto inicial.md y archivos modulares...</div>}
                  {simStep >= 4 && (
                    <div className="term-ok" style={{ marginTop: "12px", borderTop: "1px dashed #242424", paddingTop: "10px", fontWeight: 600 }}>
                      ✓ Context Tree creado en: ./Context Trees/Hardware - Audifonos Planar HiFi/<br />
                      Soverath Holding Secure Vault · Bogotá D.C.
                    </div>
                  )}
                </div>
              )}

              {terminalTab === "git" && (
                <div className="term-block">
                  <div className="term-comment"># Listar rutas de los Context Trees generados</div>
                  <div className="term-cmd">$ <Typewriter text="kspr /trees" speed={26} /></div>
                  <div className="term-ok" style={{ marginTop: "14px" }}>
                    - Concepto: Hardware - Audifonos Planar HiFi | Ruta: ./Context Trees/Hardware - Audifonos Planar HiFi<br />
                    - Concepto: Legacy Banking Core | Ruta: ./Context Trees/Legacy Banking Core
                  </div>
                </div>
              )}

              {terminalTab === "dev" && (
                <div className="term-block">
                  <div className="term-comment"># Iniciar shell interactivo de KSPR AI CLI TOOL</div>
                  <div className="term-cmd">$ <Typewriter text="kspr --interactive" speed={24} /></div>
                  <div style={{ marginTop: "8px" }}>
                    <span className="term-ok" style={{ fontWeight: 600 }}>  KSPR AI CLI TOOL — Interactive Knowledge Reconstruction (v0.1.0)</span><br />
                    <span className="term-step">  Usa @ para adjuntar archivos, o /decompilate, /trees y /capabilities.</span><br />
                    <span style={{ color: "#ffffff", fontWeight: 700 }}>kspr (architect)&gt; /trees</span>
                  </div>
                </div>
              )}
            </div>
          </div>
        </section>

        <div className="divider-wrap" aria-hidden="true">
          <VineDivider className="vine" />
        </div>

        {/* Feature Grid */}
        <section data-reveal>
          <div className="section-head">
            <span className="section-index" aria-hidden="true">04</span>
            <div>
              <span className="eyebrow">CAPACIDADES DEL MOTOR</span>
              <h2 className="section-title">Construido para análisis profundo y entrega</h2>
            </div>
          </div>
          <div className="grid-cards">
            <div className="card reveal-fade" data-tilt data-reveal style={delay(0)}>
              <Activity size={26} color="#ffffff" />
              <h3 style={{ fontWeight: 700 }}>9 Proveedores LLM Sincronizados</h3>
              <p>Conectividad directa con Google Gemini, OpenAI GPT-4o, Anthropic Claude 3.5, DeepSeek Reasoner/V3, Groq, OpenRouter, OpenCode Zen, Local LLMs y gateways compatibles.</p>
            </div>

            <div className="card reveal-fade" data-tilt data-reveal style={delay(1)}>
              <FolderArchive size={26} color="#a3a3a3" />
              <h3 style={{ fontWeight: 700 }}>Paquetes Markdown Modulares</h3>
              <p>Exportación estructurada de inventarios UI, grafos de rutas HTTP, contratos de API y reportes de seguridad listos para entrega empresarial.</p>
            </div>

            <div className="card reveal-fade" data-tilt data-reveal style={delay(2)}>
              <Search size={26} color="#6f6f6f" />
              <h3 style={{ fontWeight: 700 }}>gsap-skills &amp; Prompts Guardados</h3>
              <p>Sistema de habilidades empaquetadas (gsap-skills) y gestión de prompts personalizados mediante el comando <code style={{ color: "#ffffff", fontWeight: 700 }}>/prompts</code>.</p>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer>
        <div>
          <span className="footer-brand">KSPR AI CLI TOOL</span> · Knowledge Source Parsing &amp; Reconstruction
        </div>
        <div className="footer-provenance">
          Engineered &amp; Maintained by Soverath Holding · Bogotá D.C. - Colombia
        </div>
        <div>
          <a href="https://kspr.desktop.presentto.online" target="_blank" rel="noreferrer" className="link-white">Desktop Client ↗</a>
          {" · "}
          <a href="https://github.com/devdreiortiz/KSPR" target="_blank" rel="noreferrer" className="link-muted">GitHub</a>
        </div>
      </footer>
    </div>
  );
}
