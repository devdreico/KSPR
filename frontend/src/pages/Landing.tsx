import React, { useState } from "react";
import { Terminal, Copy, Check, Sparkles, Shield, GitBranch, FolderArchive, ArrowRight, Code2, Cpu, ExternalLink, Monitor, CreditCard, Lock, Zap, Layers, Activity, Database, Search } from "lucide-react";

export function Landing() {
  const [copiedCmd, setCopiedCmd] = useState<string | null>(null);
  const [terminalTab, setTerminalTab] = useState<"install" | "analyze" | "git" | "dev">("install");
  const [labTab, setLabTab] = useState<number>(0);
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
    setTimeout(() => setSimStep(2), 800);
    setTimeout(() => setSimStep(3), 1600);
    setTimeout(() => {
      setSimStep(4);
      setRunningSim(false);
    }, 2400);
  };

  const labProcesses = [
    {
      title: "1. Topología UI & AST",
      desc: "Análisis sintáctico abstracto (AST) de componentes React, Vue, Svelte y plantillas HTML para extraer inventario de botones, formularios, rutas y contratos de entrada sin renderizar código.",
      code: "kspr ./repo --output ./context --extract-ui",
      output: "✓ 67 archivos analizados\n✓ 1,305 elementos UI indexados\n✓ Jerarquía de componentes consolidada en UI_INVENTORY.md"
    },
    {
      title: "2. Endpoints & Rutas HTTP",
      desc: "Desensamblado estático de enrutadores Express, FastAPI, Flask, Spring y Laravel para mapear métodos HTTP, parámetros de consulta, cuerpos de solicitud y guards de seguridad.",
      code: "kspr ./backend --scan-routes --json",
      output: "✓ 84 rutas HTTP detectadas\n✓ Métodos: GET (45), POST (28), PUT/DELETE (11)\n✓ Contratos OpenAPI/Swagger generados automáticamente"
    },
    {
      title: "3. Linaje de Datos & SQL",
      desc: "Aislamiento de consultas SQL puras, ORMs (Prisma, SQLAlchemy, Hibernate) y migraciones para reconstruir esquemas relacionales, dependencias de tablas y flujos de mutación.",
      code: "kspr ./data --sql-audit --export-schema",
      output: "✓ 32 consultas SQL y sentencias ORM extraídas\n✓ Relaciones FK mapeadas\n✓ Reporte de linaje de datos listo para KSPR I"
    },
    {
      title: "4. Taint & Vulnerabilidad Estática",
      desc: "Trazado heurístico de entradas de usuario sin validar desde controladores hasta sumideros de riesgo (SQLi, XSS, SSRF, RCE) con garantía absoluta de ejecución cero (0% de riesgo en runtime).",
      code: "kspr ./src --security-audit --strict",
      output: "✓ 0 ejecución de código en runtime (100% estático)\n✓ 3 advertencias de sanitización detectadas\n✓ Paquete de riesgos generado con mitigaciones"
    },
    {
      title: "5. Deriva Arquitectónica",
      desc: "Reconciliación matemática entre especificaciones de diseño y código implementado en producción para detectar código fantasma, rutas huérfanas y desvíos de contratos.",
      code: "kspr ./app --drift-check --compare",
      output: "✓ Deriva detectada: 4.2%\n✓ Rutas huérfanas identificadas: 5\n✓ Informe de deuda técnica exportado"
    }
  ];

  return (
    <div className="app-shell animate-fade-in">
      {/* Telemetry Ticker Bar */}
      <div className="telemetry-ticker">
        <div className="ticker-track">
          <div className="ticker-item"><span className="dot" /> SOVERATH HOLDING RESEARCH · BOGOTÁ D.C., COLOMBIA</div>
          <div className="ticker-item"><span className="dot" /> 100% NON-EXECUTION STATIC REVERSE ENGINEERING</div>
          <div className="ticker-item"><span className="dot" /> 9 LLM PROVIDERS SUPPORTED (GEMINI, CLAUDE, GPT-4O, DEEPSEEK)</div>
          <div className="ticker-item"><span className="dot" /> MCP & CAPABILITY LAYER INTEGRATED</div>
          <div className="ticker-item"><span className="dot" /> SOVERATH HOLDING RESEARCH · BOGOTÁ D.C., COLOMBIA</div>
          <div className="ticker-item"><span className="dot" /> 100% NON-EXECUTION STATIC REVERSE ENGINEERING</div>
        </div>
      </div>

      {/* Topbar */}
      <header className="topbar">
        <div className="brand">
          <img src="/casper-ai-logo.png" alt="KSPR AI" className="brand-logo" />
          <div>
            <strong>KSPR CLI</strong>
            <span>Reverse Engineering Engine v0.1.0</span>
          </div>
        </div>
        
        <div className="topbar-right">
          <div className="institute-badge">
            <span>Soverath Holding</span>
            <strong>Bogotá D.C. - CO</strong>
          </div>
          <a
            href="https://kspr.desktop.presentto.online"
            target="_blank"
            rel="noreferrer"
            className="desktop-link-btn"
          >
            <Monitor size={14} color="#ffffff" />
            KSPR AI DESKTOP
            <ExternalLink size={12} style={{ opacity: 0.7 }} />
          </a>
        </div>
      </header>

      {/* Main Content */}
      <main>
        {/* Hero Section */}
        <section className="hero">
          <div className="section-tag">
            <Sparkles size={13} /> KSPR ENGINE · AGENTE DE INGENIERÍA INVERSA ESTÁTICA
          </div>
          
          <h1>
            Transforma sistemas legados en <em style={{ color: "#d4d4d8" }}>mapas cinéticos</em> desde la terminal.
          </h1>
          
          <p>
            Agente autónomo de ingeniería inversa estática desarrollado por <strong>Soverath Holding (Bogotá D.C. - Colombia)</strong>. Analiza repositorios y archivos sin ejecutar código, extrayendo componentes UI, rutas HTTP, esquemas SQL y dependencias para generar paquetes Markdown auditables listos para humanos y agentes de IA (KSPR I).
          </p>

          {/* Action Strip: Curl + Membership Side-by-Side */}
          <div className="action-strip">
            <div className="install-box">
              <div style={{ display: "flex", alignItems: "center", gap: 10, overflow: "hidden" }}>
                <Terminal size={18} color="#ffffff" style={{ flexShrink: 0 }} />
                <code style={{ whiteSpace: "nowrap", overflowX: "auto" }}>{curlCommand}</code>
              </div>
              <button
                onClick={() => copyToClipboard(curlCommand, "curl-install")}
                className="copy-btn"
                title="Copiar comando de instalación"
              >
                {copiedCmd === "curl-install" ? <Check size={14} color="#ffffff" /> : <Copy size={14} />}
                <span>{copiedCmd === "curl-install" ? "Copiado" : "Copiar cURL"}</span>
              </button>
            </div>

            <a
              href="https://kspr.membership.vercel.app"
              target="_blank"
              rel="noreferrer"
              className="membership-card-btn"
            >
              <CreditCard size={20} color="#ffffff" />
              <div className="membership-info">
                <strong>KSPR MEMBERSHIP</strong>
                <span>One-Time Purchase ↗</span>
              </div>
            </a>
          </div>
        </section>

        {/* KSPR Desktop Highlight Banner */}
        <div style={{
          background: "linear-gradient(135deg, #101014, #1c1c24)",
          border: "1px solid #27272a",
          borderRadius: "16px",
          padding: "28px 36px",
          margin: "30px 0 50px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 20,
          boxShadow: "0 15px 40px rgba(0,0,0,0.7)"
        }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, color: "#d4d4d8", font: "11px 'DM Mono', monospace", marginBottom: 6 }}>
              <Zap size={14} /> CLIENTE NATIVO DE ESCRITORIO DISPONIBLE
            </div>
            <h3 style={{ margin: 0, fontSize: "20px", fontWeight: 700, fontFamily: "'Montserrat', sans-serif", color: "#fff" }}>
              KSPR AI Desktop — Entorno Gráfico Avanzado
            </h3>
            <p style={{ margin: "6px 0 0", color: "var(--muted)", fontSize: "14px", maxWidth: "700px" }}>
              ¿Prefieres una interfaz visual nativa con control de grafos y MCP servers en tiempo real? Accede al cliente de escritorio oficial alojado en la red de Soverath Holding.
            </p>
          </div>
          <a
            href="https://kspr.desktop.presentto.online"
            target="_blank"
            rel="noreferrer"
            style={{
              background: "#ffffff",
              color: "#000000",
              padding: "12px 24px",
              borderRadius: "10px",
              fontWeight: 700,
              fontSize: "13px",
              textDecoration: "none",
              display: "flex",
              alignItems: "center",
              gap: 8,
              boxShadow: "0 4px 20px rgba(255, 255, 255, 0.2)",
              transition: "transform 0.2s"
            }}
          >
            Abrir kspr.desktop.presentto.online <ExternalLink size={14} />
          </a>
        </div>

        {/* Deep Dive: Architecture & Engineering */}
        <section style={{ margin: "50px 0" }}>
          <div style={{ marginBottom: 24 }}>
            <span style={{ color: "#d4d4d8", font: "11px 'DM Mono', monospace", letterSpacing: ".1em" }}>ARQUITECTURA DE INGENIERÍA</span>
            <h2 style={{ fontSize: "28px", margin: "6px 0 0", fontWeight: 700, fontFamily: "'Montserrat', sans-serif" }}>
              ¿Cómo opera el motor estático de KSPR?
            </h2>
          </div>

          <div className="grid-cards">
            <div className="card">
              <Shield size={24} color="#ffffff" />
              <h3>Seguridad Estática Pura</h3>
              <p>
                KSPR examina únicamente la sintaxis y los árboles de análisis abstracto (AST). <strong>Jamás ejecuta el código analizado</strong>, garantizando 0% de vulnerabilidades de ejecución en repositorios legados o desconocidos.
              </p>
            </div>

            <div className="card">
              <Layers size={24} color="#d4d4d8" />
              <h3>Capability Layer & MCP</h3>
              <p>
                Una capa de abstracción unificada que descubre automáticamente herramientas CLI (incluyendo adaptadores CLI-Anything), servidores MCP y plugins externos bajo estrictos controles de permisos.
              </p>
            </div>

            <div className="card">
              <Cpu size={24} color="#a1a1aa" />
              <h3>KSPR I & Tool Calling Loop</h3>
              <p>
                El núcleo agéntico procesa la evidencia en bucles iterativos de hasta 10 turnos, invocando herramientas, verificando resultados y autocorrigiendo hipótesis antes de consolidar la documentación.
              </p>
            </div>
          </div>
        </section>

        {/* Interactive Reverse Engineering Lab */}
        <section className="lab-container">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20, flexWrap: "wrap", gap: 12 }}>
            <div>
              <span style={{ color: "#d4d4d8", font: "11px 'DM Mono', monospace", letterSpacing: ".1em" }}>LABORATORIO TÉCNICO</span>
              <h2 style={{ fontSize: "24px", margin: "4px 0 0", fontWeight: 700 }}>Procesos de Ingeniería Inversa</h2>
            </div>
            <span style={{ color: "var(--muted)", font: "11px 'DM Mono', monospace" }}>Soverath Holding · Bogotá D.C.</span>
          </div>

          <div className="lab-tabs">
            {labProcesses.map((proc, idx) => (
              <button
                key={idx}
                onClick={() => setLabTab(idx)}
                className={`lab-tab ${labTab === idx ? "active" : ""}`}
              >
                {proc.title}
              </button>
            ))}
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "30px", alignItems: "stretch" }} className="lab-content-grid">
            <div style={{ background: "#08080a", padding: "24px", borderRadius: "12px", border: "1px solid var(--line)" }}>
              <h4 style={{ margin: "0 0 12px", color: "#fff", fontSize: "16px" }}>{labProcesses[labTab].title}</h4>
              <p style={{ margin: 0, color: "var(--muted)", fontSize: "14px", lineHeight: "1.7" }}>
                {labProcesses[labTab].desc}
              </p>
              <div style={{ marginTop: "20px", padding: "12px", background: "#141418", borderRadius: "8px", font: "12px 'DM Mono', monospace", color: "#ffffff" }}>
                $ {labProcesses[labTab].code}
              </div>
            </div>

            <div style={{ background: "#020203", padding: "24px", borderRadius: "12px", border: "1px solid var(--line)", fontFamily: "'DM Mono', monospace", fontSize: "13px", display: "flex", flexDirection: "column", justifyContent: "center" }}>
              <div style={{ color: "var(--muted)", marginBottom: "8px" }}># Salida estructurada de evidencia:</div>
              <pre style={{ margin: 0, color: "#d4d4d8", whiteSpace: "pre-wrap", lineHeight: 1.6 }}>
                {labProcesses[labTab].output}
              </pre>
            </div>
          </div>
        </section>

        {/* Terminal Simulation Section */}
        <section style={{ margin: "50px 0" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16, flexWrap: "wrap", gap: 12 }}>
            <div>
              <span style={{ color: "#d4d4d8", font: "11px 'DM Mono', monospace", letterSpacing: ".1em" }}>TERMINAL CLI</span>
              <h2 style={{ fontSize: "22px", margin: "4px 0 0", fontWeight: 700 }}>Simulador de Ejecución y Comandos</h2>
            </div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <button
                onClick={() => setTerminalTab("install")}
                className={`lab-tab ${terminalTab === "install" ? "active" : ""}`}
              >
                1. cURL Install
              </button>
              <button
                onClick={() => setTerminalTab("analyze")}
                className={`lab-tab ${terminalTab === "analyze" ? "active" : ""}`}
              >
                2. Análisis Local
              </button>
              <button
                onClick={() => setTerminalTab("git")}
                className={`lab-tab ${terminalTab === "git" ? "active" : ""}`}
              >
                3. Repositorio Git
              </button>
              <button
                onClick={() => setTerminalTab("dev")}
                className={`lab-tab ${terminalTab === "dev" ? "active" : ""}`}
              >
                4. Shell Interactivo
              </button>
            </div>
          </div>

          <div className="terminal-window">
            <div className="terminal-header">
              <div className="terminal-dots">
                <span className="dot-r" />
                <span className="dot-y" />
                <span className="dot-g" />
                <span style={{ marginLeft: 8, fontSize: "12px", fontFamily: "'DM Mono', monospace", color: "#a1a1aa" }}>kspr@soverath-bogota:~</span>
              </div>
              <button
                onClick={runSimulation}
                disabled={runningSim}
                style={{
                  background: runningSim ? "#27272a" : "#3f3f46",
                  color: "#fff",
                  border: "none",
                  padding: "6px 14px",
                  borderRadius: "6px",
                  fontSize: "11px",
                  fontFamily: "'Montserrat', sans-serif",
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
                  <div style={{ color: "#ffffff", margin: "8px 0" }}>$ curl -sSL https://raw.githubusercontent.com/devdreiortiz/KSPR/main/bin/install.sh | bash</div>
                  <div style={{ color: "#a1a1aa", marginTop: "12px" }}>
                    ✓ Clonación segura en ~/.kspr<br />
                    ✓ Entorno virtual Python aislado (.venv)<br />
                    ✓ Enlace ejecutable creado en ~/.local/bin/kspr
                  </div>
                </div>
              )}

              {terminalTab === "analyze" && (
                <div>
                  <div style={{ color: "#71717a" }}># Analizar directorio local con 3 iteraciones de razonamiento agéntico</div>
                  <div style={{ color: "#ffffff", margin: "8px 0" }}>$ kspr ./mi-proyecto --output ./kspr-context --iterations 3</div>
                  {simStep >= 1 && <div style={{ color: "#d4d4d8", marginTop: "6px" }}>[1/3] Ingesta estática completada: 67 archivos leídos sin ejecución.</div>}
                  {simStep >= 2 && <div style={{ color: "#a1a1aa", marginTop: "4px" }}>[2/3] Extracción AST de UI, rutas HTTP, SQL y dependencias...</div>}
                  {simStep >= 3 && <div style={{ color: "#71717a", marginTop: "4px" }}>[3/3] Consolidando mapa cinético con KSPR I (3/3)...</div>}
                  {simStep >= 4 && (
                    <div style={{ color: "#ffffff", marginTop: "8px", borderTop: "1px dashed #27272a", paddingTop: "8px" }}>
                      ✓ Análisis finalizado con éxito (Duración: 1.4s)<br />
                      Paquete generado en: ./kspr-context<br />
                      Soverath Holding Secure Vault · Bogotá D.C.
                    </div>
                  )}
                </div>
              )}

              {terminalTab === "git" && (
                <div>
                  <div style={{ color: "#71717a" }}># Clonar y auditar repositorio Git remoto de forma superficial (--depth 1)</div>
                  <div style={{ color: "#ffffff", margin: "8px 0" }}>$ kspr . --git-url https://github.com/org/repo.git --output ./repo-context</div>
                  <div style={{ color: "#a1a1aa", marginTop: "8px" }}>Clonación segura completada en sandbox temporal. Listo para exportación de conocimiento.</div>
                </div>
              )}

              {terminalTab === "dev" && (
                <div>
                  <div style={{ color: "#71717a" }}># Iniciar el shell interactivo de KSPR con logotipo ASCII y comandos slash</div>
                  <div style={{ color: "#ffffff", margin: "8px 0" }}>$ kspr --interactive</div>
                  <div style={{ color: "#e2e8f0", marginTop: "6px" }}>
                    <span style={{ color: "#d4d4d8" }}>  KSPR CLI — OpenCode Interactive Terminal Agent (v0.1.0)</span><br/>
                    <span style={{ color: "#a1a1aa" }}>  Escribe una consulta, referencia archivos con @ o usa /capabilities, /prompts, /skills.</span><br/>
                    <span style={{ color: "#ffffff" }}>kspr (architect)&gt; /capabilities</span>
                  </div>
                </div>
              )}
            </div>
          </div>
        </section>

        {/* Feature Grid */}
        <div className="grid-cards">
          <div className="card">
            <Activity size={24} color="#ffffff" />
            <h3>Integración de 9 Proveedores LLM</h3>
            <p>Soporte nativo para Google Gemini, OpenAI GPT-4o, Anthropic Claude 3.5, DeepSeek Reasoner/V3, Groq, OpenRouter, OpenCode Zen, Local LLMs y endpoints OpenAI-compatibles.</p>
          </div>

          <div className="card">
            <FolderArchive size={24} color="#d4d4d8" />
            <h3>Paquetes Markdown Modulares</h3>
            <p>Exporta carpetas estructuradas conteniendo inventario UI, mapa de flujos, contratos de API, riesgos de seguridad y contradicciones listos para entregar a humanos o agentes.</p>
          </div>

          <div className="card">
            <Search size={24} color="#a1a1aa" />
            <h3>gsap-skills & Prompts Personalizados</h3>
            <p>Sistema de habilidades empaquetadas (gsap-skills) y gestión de prompts guardados mediante el comando <code style={{ color: "#fff" }}>/prompts</code> para flujos de trabajo repetibles.</p>
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
          <a href="https://kspr.desktop.presentto.online" target="_blank" rel="noreferrer" style={{ color: "#ffffff", textDecoration: "none" }}>Desktop Client ↗</a>
          {" · "}
          <a href="https://github.com/devdreiortiz/KSPR" target="_blank" rel="noreferrer" style={{ color: "var(--muted)", textDecoration: "none" }}>GitHub</a>
        </div>
      </footer>
    </div>
  );
}
