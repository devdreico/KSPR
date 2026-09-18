import React, { useState } from "react";
import { Terminal, Copy, Check, Sparkles, Shield, GitBranch, FolderArchive, ArrowRight, Code2, Cpu, ExternalLink, Monitor, CreditCard, Lock, Zap, Layers, Activity, Database, Search } from "lucide-react";

export function Landing() {
  const [copiedCmd, setCopiedCmd] = useState<string | null>(null);
  const [terminalTab, setTerminalTab] = useState<"install" | "analyze" | "git" | "dev">("install");
  const [decompTab, setDecompTab] = useState<number>(0);
  const [runningSim, setRunningSim] = useState(false);
  const [simStep, setSimStep] = useState(0);

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
      {/* Topbar */}
      <header className="topbar">
        <div className="brand">
          <img src="/casper-ai-logo.png" alt="KSPR AI" className="brand-logo" />
          <div>
            <strong style={{ fontWeight: 700 }}>KSPR CLI</strong>
            <span style={{ fontWeight: 500 }}>Reverse Engineering Engine v0.1.0</span>
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
          <div className="section-tag">
            <Sparkles size={14} /> KSPR ENGINE · AGENTE DE INGENIERÍA INVERSA ESTÁTICA
          </div>
          
          <h1 style={{ fontWeight: 700 }}>
            Transforma sistemas legados y hardware en <em style={{ fontWeight: 400 }}>mapas de contexto</em> desde la terminal.
          </h1>
          
          <p style={{ fontWeight: 400 }}>
            Motor autónomo de ingeniería inversa estática desarrollado por <strong style={{ fontWeight: 700 }}>Soverath Holding (Bogotá D.C. - Colombia)</strong>. Analiza repositorios de código, esquemáticos, PDFs técnicos, imágenes y enlaces web mediante análisis estricto sin ejecución, generando árboles de conocimiento auditables para arquitectos e ingenieros de élite.
          </p>

          {/* Action Strip: Curl + Membership Side-by-Side */}
          <div className="action-strip">
            <div className="install-box">
              <div style={{ display: "flex", alignItems: "center", gap: 12, overflow: "hidden" }}>
                <Terminal size={19} color="#ffffff" style={{ flexShrink: 0 }} />
                <code style={{ whiteSpace: "nowrap", overflowX: "auto", fontFamily: "'Montserrat', sans-serif", fontSize: "13px" }}>{curlCommand}</code>
              </div>
              <button
                onClick={() => copyToClipboard(curlCommand, "curl-install")}
                className="copy-btn"
                title="Copiar comando de instalación"
              >
                {copiedCmd === "curl-install" ? <Check size={14} color="#ffffff" /> : <Copy size={14} />}
                <span style={{ fontWeight: 700 }}>{copiedCmd === "curl-install" ? "Copiado" : "Copiar cURL"}</span>
              </button>
            </div>

            <a
              href="https://kspr.membership.vercel.app"
              target="_blank"
              rel="noreferrer"
              className="membership-card-btn"
            >
              <CreditCard size={22} color="#ffffff" />
              <div className="membership-info">
                <strong style={{ fontWeight: 700 }}>KSPR MEMBERSHIP</strong>
                <span style={{ fontWeight: 500 }}>One-Time Purchase ↗</span>
              </div>
            </a>
          </div>
        </section>

        {/* KSPR Desktop Highlight Banner */}
        <div style={{
          background: "linear-gradient(135deg, #0a0a0e, #14141c)",
          border: "1px solid #27272a",
          borderRadius: "18px",
          padding: "32px 40px",
          margin: "40px 0 60px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 24,
          boxShadow: "0 20px 50px rgba(0,0,0,0.8)"
        }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, color: "#d4d4d8", fontSize: "12px", fontWeight: 600, marginBottom: 8, letterSpacing: ".1em" }}>
              <Zap size={15} /> CLIENTE NATIVO DE ESCRITORIO DISPONIBLE
            </div>
            <h3 style={{ margin: 0, fontSize: "22px", fontWeight: 700, color: "#fff" }}>
              KSPR AI Desktop — Entorno Gráfico Avanzado
            </h3>
            <p style={{ margin: "8px 0 0", color: "var(--muted)", fontSize: "15px", maxWidth: "720px", fontWeight: 400 }}>
              ¿Prefieres una interfaz visual nativa con control de grafos y MCP servers en tiempo real? Accede al cliente de escritorio oficial en la infraestructura de Soverath Holding.
            </p>
          </div>
          <a
            href="https://kspr.desktop.presentto.online"
            target="_blank"
            rel="noreferrer"
            style={{
              background: "#ffffff",
              color: "#000000",
              padding: "14px 28px",
              borderRadius: "12px",
              fontWeight: 700,
              fontSize: "14px",
              textDecoration: "none",
              display: "flex",
              alignItems: "center",
              gap: 10,
              boxShadow: "0 6px 25px rgba(255, 255, 255, 0.2)",
              transition: "transform 0.2s"
            }}
          >
            <span>Abrir kspr.desktop.presentto.online</span>
            <ExternalLink size={15} />
          </a>
        </div>

        {/* Real Workflows & Exploration Areas */}
        <section style={{ margin: "60px 0" }}>
          <div style={{ marginBottom: 28 }}>
            <span style={{ color: "#d4d4d8", fontSize: "12px", fontWeight: 600, letterSpacing: ".12em" }}>CAMPOS DE APLICACIÓN INDUSTRIAL</span>
            <h2 style={{ fontSize: "32px", margin: "8px 0 0", fontWeight: 700 }}>
              Flujos de trabajo reales donde KSPR destaca
            </h2>
          </div>

          <div className="grid-cards">
            <div className="card">
              <Shield size={28} color="#ffffff" />
              <h3 style={{ fontWeight: 700 }}>1. Auditoría y Taint Analysis sin Ejecución</h3>
              <p>
                Analiza software crítico de cadena de suministro y repositorios legados con 0% de riesgo de runtime. KSPR rastrea entradas de usuario desde controladores hasta sumideros de riesgo (SQLi, XSS, RCE) puramente mediante AST y análisis sintáctico.
              </p>
            </div>

            <div className="card">
              <Layers size={28} color="#d4d4d8" />
              <h3 style={{ fontWeight: 700 }}>2. Decompilación Multi-Modal con /decompilate</h3>
              <p>
                Ingesta simultánea de PDFs, esquemáticos en imagen (.jpg, .png, .heif), notas de texto y enlaces web. KSPR agrupa la evidencia y genera árboles de contexto estructurados en carpetas con sub-archivos Markdown granulares.
              </p>
            </div>

            <div className="card">
              <Cpu size={28} color="#a1a1aa" />
              <h3 style={{ fontWeight: 700 }}>3. Orquestación Multi-LLM y Tool-Calling</h3>
              <p>
                Bucle agéntico autónomo de hasta 10 iteraciones (KSPR I) respaldado por 9 proveedores (Gemini, Claude 3.5, GPT-4o, DeepSeek, Groq, OpenRouter, OpenCode Zen, Local). Invoca herramientas y corrige hipótesis dinámicamente.
              </p>
            </div>
          </div>
        </section>

        {/* Cinematic Hardware Decomposition Example (Planar Headphones) */}
        <section className="decomp-container">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24, flexWrap: "wrap", gap: 16 }}>
            <div>
              <span style={{ color: "#d4d4d8", fontSize: "12px", fontWeight: 600, letterSpacing: ".12em" }}>DEMOSTRACIÓN DE CAPACIDAD TÉCNICA</span>
              <h2 style={{ fontSize: "26px", margin: "6px 0 0", fontWeight: 700 }}>Decompilación Estática de Hardware: Audífonos Planar Hi-Fi</h2>
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

          <div style={{ display: "grid", gridTemplateColumns: "1.1fr 0.9fr", gap: "32px", alignItems: "stretch" }} className="decomp-grid">
            <div style={{ background: "#050508", padding: "30px", borderRadius: "16px", border: "1px solid var(--line)" }}>
              <h4 style={{ margin: "0 0 6px", color: "#fff", fontSize: "18px", fontWeight: 700 }}>{headphoneDecompParts[decompTab].title}</h4>
              <div style={{ color: "#a1a1aa", fontSize: "13px", fontWeight: 500, marginBottom: "16px" }}>{headphoneDecompParts[decompTab].subtitle}</div>
              <p style={{ margin: 0, color: "var(--muted)", fontSize: "15px", lineHeight: "1.7", fontWeight: 400 }}>
                {headphoneDecompParts[decompTab].desc}
              </p>
              <div style={{ marginTop: "24px", padding: "14px 18px", background: "#101015", borderRadius: "10px", fontSize: "13px", fontWeight: 600, color: "#ffffff", border: "1px solid #27272a" }}>
                $ {headphoneDecompParts[decompTab].command}
              </div>
            </div>

            <div style={{ background: "#010103", padding: "30px", borderRadius: "16px", border: "1px solid var(--line)", fontSize: "13px", display: "flex", flexDirection: "column", justifyContent: "center" }}>
              <div style={{ color: "var(--muted)", marginBottom: "10px", fontWeight: 500 }}># Resultado del Árbol de Contexto Generado:</div>
              <pre style={{ margin: 0, color: "#d4d4d8", whiteSpace: "pre-wrap", lineHeight: 1.7, fontWeight: 500 }}>
                {headphoneDecompParts[decompTab].output}
              </pre>
            </div>
          </div>
        </section>

        {/* Terminal Simulation Section */}
        <section style={{ margin: "60px 0" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20, flexWrap: "wrap", gap: 16 }}>
            <div>
              <span style={{ color: "#d4d4d8", fontSize: "12px", fontWeight: 600, letterSpacing: ".12em" }}>TERMINAL CLI</span>
              <h2 style={{ fontSize: "24px", margin: "6px 0 0", fontWeight: 700 }}>Simulador de Comandos y Flujo Interactivo</h2>
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
                4. Shell KSPR I
              </button>
            </div>
          </div>

          <div className="terminal-window">
            <div className="terminal-header">
              <div className="terminal-dots">
                <span className="dot-r" />
                <span className="dot-y" />
                <span className="dot-g" />
                <span style={{ marginLeft: 10, fontSize: "13px", fontWeight: 500, color: "#a1a1aa" }}>kspr@soverath-bogota:~</span>
              </div>
              <button
                onClick={runSimulation}
                disabled={runningSim}
                style={{
                  background: runningSim ? "#27272a" : "#3f3f46",
                  color: "#fff",
                  border: "none",
                  padding: "8px 16px",
                  borderRadius: "8px",
                  fontSize: "12px",
                  fontWeight: 700,
                  cursor: runningSim ? "wait" : "pointer"
                }}
              >
                {runningSim ? "Ejecutando proceso..." : "▶ Simular Ejecución"}
              </button>
            </div>

            <div className="terminal-body">
              {terminalTab === "install" && (
                <div>
                  <div style={{ color: "#71717a" }}># Instalación desatendida mediante script Bash oficial</div>
                  <div style={{ color: "#ffffff", margin: "10px 0", fontWeight: 600 }}>$ curl -sSL https://raw.githubusercontent.com/devdreiortiz/KSPR/main/bin/install.sh | bash</div>
                  <div style={{ color: "#a1a1aa", marginTop: "14px" }}>
                    ✓ Clonación segura en ~/.kspr<br />
                    ✓ Entorno virtual Python aislado (.venv)<br />
                    ✓ Enlace ejecutable creado en ~/.local/bin/kspr
                  </div>
                </div>
              )}

              {terminalTab === "analyze" && (
                <div>
                  <div style={{ color: "#71717a" }}># Ingesta multi-fuente y compilación de Context Trees</div>
                  <div style={{ color: "#ffffff", margin: "10px 0", fontWeight: 600 }}>$ kspr /decompilate ./specs.pdf ./diagram.png https://docs.api.com</div>
                  {simStep >= 1 && <div style={{ color: "#d4d4d8", marginTop: "8px" }}>[1/3] Fuentes indexadas y subidas a staging workspace.</div>}
                  {simStep >= 2 && <div style={{ color: "#a1a1aa", marginTop: "6px" }}>[2/3] Análisis agéntico con KSPR I y extracción heurística...</div>}
                  {simStep >= 3 && <div style={{ color: "#71717a", marginTop: "6px" }}>[3/3] Generación de Contexto inicial.md y archivos modulares...</div>}
                  {simStep >= 4 && (
                    <div style={{ color: "#ffffff", marginTop: "12px", borderTop: "1px dashed #27272a", paddingTop: "10px", fontWeight: 600 }}>
                      ✓ Context Tree creado en: ./Context Trees/Hardware - Audifonos Planar HiFi/<br />
                      Soverath Holding Secure Vault · Bogotá D.C.
                    </div>
                  )}
                </div>
              )}

              {terminalTab === "git" && (
                <div>
                  <div style={{ color: "#71717a" }}># Listar rutas de los Context Trees generados</div>
                  <div style={{ color: "#ffffff", margin: "10px 0", fontWeight: 600 }}>$ kspr /trees</div>
                  <div style={{ color: "#a1a1aa", marginTop: "14px" }}>
                    - Concepto: Hardware - Audifonos Planar HiFi | Ruta: ./Context Trees/Hardware - Audifonos Planar HiFi<br />
                    - Concepto: Legacy Banking Core | Ruta: ./Context Trees/Legacy Banking Core
                  </div>
                </div>
              )}

              {terminalTab === "dev" && (
                <div>
                  <div style={{ color: "#71717a" }}># Iniciar shell interactivo de KSPR I</div>
                  <div style={{ color: "#ffffff", margin: "10px 0", fontWeight: 600 }}>$ kspr --interactive</div>
                  <div style={{ color: "#e2e8f0", marginTop: "8px" }}>
                    <span style={{ color: "#d4d4d8", fontWeight: 600 }}>  KSPR CLI — OpenCode Interactive Terminal Agent (v0.1.0)</span><br/>
                    <span style={{ color: "#a1a1aa" }}>  Usa @ para adjuntar archivos, o comandos /decompilate, /trees, /capabilities.</span><br/>
                    <span style={{ color: "#ffffff", fontWeight: 700 }}>kspr (architect)&gt; /trees</span>
                  </div>
                </div>
              )}
            </div>
          </div>
        </section>

        {/* Feature Grid */}
        <div className="grid-cards">
          <div className="card">
            <Activity size={26} color="#ffffff" />
            <h3 style={{ fontWeight: 700 }}>9 Proveedores LLM Sincronizados</h3>
            <p>Conectividad directa con Google Gemini, OpenAI GPT-4o, Anthropic Claude 3.5, DeepSeek Reasoner/V3, Groq, OpenRouter, OpenCode Zen, Local LLMs y gateways compatibles.</p>
          </div>

          <div className="card">
            <FolderArchive size={26} color="#d4d4d8" />
            <h3 style={{ fontWeight: 700 }}>Paquetes Markdown Modulares</h3>
            <p>Exportación estructurada de inventarios UI, grafos de rutas HTTP, contratos de API y reportes de seguridad listos para entrega empresarial.</p>
          </div>

          <div className="card">
            <Search size={26} color="#a1a1aa" />
            <h3 style={{ fontWeight: 700 }}>gsap-skills & Prompts Guardados</h3>
            <p>Sistema de habilidades empaquetadas (gsap-skills) y gestión de prompts personalizados mediante el comando <code style={{ color: "#fff", fontWeight: 700 }}>/prompts</code>.</p>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer>
        <div>
          <span className="footer-brand">KSPR AI</span> · Terminal-First Reverse Engineering Agent
        </div>
        <div className="footer-provenance">
          Engineered & Maintained by Soverath Holding · Bogotá D.C. - Colombia
        </div>
        <div>
          <a href="https://kspr.desktop.presentto.online" target="_blank" rel="noreferrer" style={{ color: "#ffffff", textDecoration: "none", fontWeight: 700 }}>Desktop Client ↗</a>
          {" · "}
          <a href="https://github.com/devdreiortiz/KSPR" target="_blank" rel="noreferrer" style={{ color: "var(--muted)", textDecoration: "none", fontWeight: 500 }}>GitHub</a>
        </div>
      </footer>
    </div>
  );
}
