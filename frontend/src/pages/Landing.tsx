import React, { useState } from "react";
import { Terminal, Copy, Check, Sparkles, Shield, GitBranch, FolderArchive, ArrowRight, BookOpen, Code2, Cpu } from "lucide-react";

export function Landing() {
  const [copiedCmd, setCopiedCmd] = useState<string | null>(null);
  const [terminalTab, setTerminalTab] = useState<"install" | "analyze" | "git" | "dev">("install");
  const [runningSim, setRunningSim] = useState(false);
  const [simStep, setSimStep] = useState(0);

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

  return (
    <div className="app-shell" style={{ fontFamily: "'Montserrat', sans-serif" }}>
      {/* Topbar */}
      <header className="topbar">
        <div className="brand">
          <img src="/casper-ai-logo.png" alt="KSPR AI" className="brand-logo" />
          <div>
            <strong style={{ fontFamily: "'Montserrat', sans-serif", fontWeight: 700 }}>KSPR CLI</strong>
            <span>Reverse Engineering AI Agent</span>
          </div>
        </div>
        <div className="topbar-meta">
          <span className="live-dot" />
          <span>v0.1.0 · Terminal-First</span>
          <div className="divider" />
          <a
            href="https://github.com/devdreiortiz/KSPR"
            target="_blank"
            rel="noreferrer"
            style={{ color: "var(--ink)", textDecoration: "none", fontWeight: 700, display: "flex", alignItems: "center", gap: 6, fontFamily: "'Montserrat', sans-serif" }}
          >
            GitHub <ArrowRight size={13} />
          </a>
        </div>
      </header>

      {/* Main Content */}
      <main>
        {/* Hero Section */}
        <section className="hero" style={{ flexDirection: "column", alignItems: "flex-start", gap: 32, paddingBottom: 40 }}>
          <div className="section-kicker" style={{ fontWeight: 700, fontFamily: "'Montserrat', sans-serif" }}>
            <Sparkles size={13} style={{ display: "inline", marginRight: 6 }} /> KSPR ENGINE · CLI INTERFACE
          </div>
          <h1 style={{ maxWidth: "100%", margin: 0, fontFamily: "'Montserrat', sans-serif", fontWeight: 700 }}>
            Transforma sistemas legados en <em style={{ fontWeight: 700 }}>mapas técnicos</em> desde la terminal.
          </h1>
          <p style={{ maxWidth: "700px", fontSize: "17px", fontFamily: "'Montserrat', sans-serif" }}>
            KSPR CLI es un agente de ingeniería inversa estática que escanea repositorios, extrae componentes UI, rutas HTTP, eventos y consultas SQL de forma 100% segura, generando paquetes Markdown auditables listos para humanos y agentes.
          </p>

          {/* Quick Install Bar & Download Methods */}
          <div style={{ display: "flex", flexWrap: "wrap", gap: 14, marginTop: 10, width: "100%", maxWidth: "860px" }}>
            <div style={{
              flex: 1,
              minWidth: "280px",
              background: "#151515",
              color: "#fff",
              padding: "14px 20px",
              borderRadius: "10px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              fontFamily: "'DM Mono', monospace",
              fontSize: "13px",
              boxShadow: "0 10px 30px rgba(0,0,0,0.15)"
            }}>
              <span>npm install -g kspr-ai</span>
              <button
                onClick={() => copyToClipboard("npm install -g kspr-ai", "install-cmd")}
                style={{ background: "transparent", border: "none", color: "#aaa", cursor: "pointer", display: "flex", alignItems: "center", gap: 4 }}
                title="Copiar comando"
              >
                {copiedCmd === "install-cmd" ? <Check size={14} color="#4ade80" /> : <Copy size={14} />}
                <span style={{ fontSize: "11px", fontFamily: "'Montserrat', sans-serif", fontWeight: 700 }}>{copiedCmd === "install-cmd" ? "Copiado" : "Copiar"}</span>
              </button>
            </div>
            <div style={{
              background: "#151515",
              color: "#fff",
              padding: "14px 20px",
              borderRadius: "10px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              fontFamily: "'DM Mono', monospace",
              fontSize: "13px",
              boxShadow: "0 10px 30px rgba(0,0,0,0.15)"
            }}>
              <span>npx kspr-ai</span>
              <button
                onClick={() => copyToClipboard("npx kspr-ai", "npx-cmd")}
                style={{ background: "transparent", border: "none", color: "#aaa", cursor: "pointer", display: "flex", alignItems: "center", gap: 4 }}
                title="Copiar comando"
              >
                {copiedCmd === "npx-cmd" ? <Check size={14} color="#4ade80" /> : <Copy size={14} />}
                <span style={{ fontSize: "11px", fontFamily: "'Montserrat', sans-serif", fontWeight: 700 }}>{copiedCmd === "npx-cmd" ? "Copiado" : "Copiar"}</span>
              </button>
            </div>
          </div>
        </section>

        {/* Engineering & Agentic Flow Section */}
        <section id="engineering-flow" style={{ marginTop: 20, marginBottom: 50, padding: "36px", background: "var(--white)", border: "1px solid var(--line)", borderRadius: "16px" }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "40px" }}>
            <div>
              <h2 style={{ margin: "0 0 16px", fontSize: "20px", fontWeight: 700, fontFamily: "'Montserrat', sans-serif" }}>Ingeniería Inversa Estática y Segura</h2>
              <p style={{ margin: "0 0 16px", color: "var(--muted)", fontSize: "14px", lineHeight: "1.7", fontFamily: "'Montserrat', sans-serif" }}>
                KSPR opera mediante análisis estático puro. <strong>Nunca ejecuta el código analizado</strong>. Examina la estructura sintáctica para recuperar metadatos esenciales sin comprometer la seguridad de sistemas legados.
              </p>
              <ul style={{ margin: 0, paddingLeft: "20px", color: "var(--muted)", fontSize: "14px", lineHeight: "1.7", fontFamily: "'Montserrat', sans-serif" }}>
                <li><strong>Inventario UI:</strong> Botones, formularios, enlaces y elementos de interfaz.</li>
                <li><strong>Rutas HTTP y Endpoints:</strong> Mapeo completo de URLs y métodos de backend.</li>
                <li><strong>Operaciones SQL y Datos:</strong> Consultas SELECT, UPDATE, INSERT y procedimientos almacenados.</li>
                <li><strong>Dependencias:</strong> Paquetes, imports y relaciones de librerías.</li>
              </ul>
            </div>
            <div>
              <h2 style={{ margin: "0 0 16px", fontSize: "20px", fontWeight: 700, fontFamily: "'Montserrat', sans-serif" }}>Flujo Agéntico (KSPR I)</h2>
              <p style={{ margin: "0 0 16px", color: "var(--muted)", fontSize: "14px", lineHeight: "1.7", fontFamily: "'Montserrat', sans-serif" }}>
                El núcleo agéntico <strong>KSPR I</strong> procesa la evidencia estática recolectada en múltiples iteraciones inteligentes para contrastar hallazgos, detectar contradicciones y generar documentación estructurada de calidad empresarial.
              </p>
              <ol style={{ margin: 0, paddingLeft: "20px", color: "var(--muted)", fontSize: "14px", lineHeight: "1.7", fontFamily: "'Montserrat', sans-serif" }}>
                <li><strong>Ingesta y Normalización:</strong> Lectura segura de archivos locales, ZIPs o repositorios Git.</li>
                <li><strong>Razonamiento Iterativo:</strong> Análisis profundo por la IA con validación cruzada de evidencia.</li>
                <li><strong>Consolidación Markdown:</strong> Exportación de paquetes modulares (Inventario UI, Flujos, Riesgos, Iteraciones).</li>
              </ol>
            </div>
          </div>
        </section>

        {/* Interactive Terminal Demo */}
        <section id="terminal-docs" style={{ marginTop: 20, marginBottom: 60 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16, flexWrap: "wrap", gap: 12 }}>
            <h2 style={{ fontSize: "22px", margin: 0, fontWeight: 700, fontFamily: "'Montserrat', sans-serif" }}>Terminal y Metodologías CLI</h2>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <button
                onClick={() => setTerminalTab("install")}
                style={{
                  padding: "6px 14px",
                  borderRadius: "6px",
                  border: "1px solid var(--line)",
                  background: terminalTab === "install" ? "#151515" : "transparent",
                  color: terminalTab === "install" ? "#fff" : "var(--ink)",
                  cursor: "pointer",
                  fontSize: "12px",
                  fontWeight: 700,
                  fontFamily: "'Montserrat', sans-serif"
                }}
              >
                1. npm / npx
              </button>
              <button
                onClick={() => setTerminalTab("analyze")}
                style={{
                  padding: "6px 14px",
                  borderRadius: "6px",
                  border: "1px solid var(--line)",
                  background: terminalTab === "analyze" ? "#151515" : "transparent",
                  color: terminalTab === "analyze" ? "#fff" : "var(--ink)",
                  cursor: "pointer",
                  fontSize: "12px",
                  fontWeight: 700,
                  fontFamily: "'Montserrat', sans-serif"
                }}
              >
                2. Análisis Local
              </button>
              <button
                onClick={() => setTerminalTab("git")}
                style={{
                  padding: "6px 14px",
                  borderRadius: "6px",
                  border: "1px solid var(--line)",
                  background: terminalTab === "git" ? "#151515" : "transparent",
                  color: terminalTab === "git" ? "#fff" : "var(--ink)",
                  cursor: "pointer",
                  fontSize: "12px",
                  fontWeight: 700,
                  fontFamily: "'Montserrat', sans-serif"
                }}
              >
                3. Repositorio Git
              </button>
              <button
                onClick={() => setTerminalTab("dev")}
                style={{
                  padding: "6px 14px",
                  borderRadius: "6px",
                  border: "1px solid var(--line)",
                  background: terminalTab === "dev" ? "#151515" : "transparent",
                  color: terminalTab === "dev" ? "#fff" : "var(--ink)",
                  cursor: "pointer",
                  fontSize: "12px",
                  fontWeight: 700,
                  fontFamily: "'Montserrat', sans-serif"
                }}
              >
                4. Shell Interactivo
              </button>
            </div>
          </div>

          <div style={{
            background: "#0d0d0e",
            color: "#e2e8f0",
            borderRadius: "12px",
            border: "1px solid #2d2d30",
            overflow: "hidden",
            boxShadow: "0 20px 40px rgba(0,0,0,0.25)"
          }}>
            {/* Terminal Titlebar */}
            <div style={{
              background: "#18181b",
              padding: "12px 16px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              borderBottom: "1px solid #2d2d30"
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ width: 10, height: 10, borderRadius: "50%", background: "#ef4444", display: "inline-block" }} />
                <span style={{ width: 10, height: 10, borderRadius: "50%", background: "#f59e0b", display: "inline-block" }} />
                <span style={{ width: 10, height: 10, borderRadius: "50%", background: "#22c55e", display: "inline-block" }} />
                <span style={{ marginLeft: 8, fontSize: "12px", fontFamily: "'DM Mono', monospace", color: "#a1a1aa" }}>kspr@enterprise:~</span>
              </div>
              <button
                onClick={runSimulation}
                disabled={runningSim}
                style={{
                  background: runningSim ? "#27272a" : "#3f3f46",
                  color: "#fff",
                  border: "none",
                  padding: "5px 12px",
                  borderRadius: "4px",
                  fontSize: "11px",
                  fontFamily: "'Montserrat', sans-serif",
                  fontWeight: 700,
                  cursor: runningSim ? "wait" : "pointer"
                }}
              >
                {runningSim ? "Ejecutando..." : "▶ Simular Ejecución CLI"}
              </button>
            </div>

            {/* Terminal Body */}
            <div style={{
              padding: "24px",
              fontFamily: "'DM Mono', monospace",
              fontSize: "13px",
              lineHeight: "1.6",
              minHeight: "240px",
              background: "#09090b"
            }}>
              {terminalTab === "install" && (
                <div>
                  <div style={{ color: "#71717a" }}># Instalar KSPR globalmente desde npm</div>
                  <div style={{ color: "#4ade80", margin: "8px 0" }}>$ npm install -g kspr-ai</div>
                  <div style={{ color: "#71717a", marginTop: "12px" }}># O ejecución instantánea sin instalación previa con npx</div>
                  <div style={{ color: "#4ade80", margin: "8px 0" }}>$ npx kspr-ai --help</div>
                  <div style={{ color: "#a1a1aa", marginTop: "12px" }}>✓ Disponible con wrappers Node.js (kspr.js), Bash (kspr.sh) y Bun (kspr.bun).</div>
                </div>
              )}

              {terminalTab === "analyze" && (
                <div>
                  <div style={{ color: "#71717a" }}># Analizar un directorio local especificando proveedor local o gemini</div>
                  <div style={{ color: "#4ade80", margin: "8px 0" }}>$ kspr ./mi-proyecto --output ./kspr-context --iterations 3 --provider local</div>
                  {simStep >= 1 && <div style={{ color: "#facc15", marginTop: "6px" }}>[1/3] Ingesta segura completada: 67 archivos analizados.</div>}
                  {simStep >= 2 && <div style={{ color: "#38bdf8", marginTop: "4px" }}>[2/3] Extracción estática de UI, rutas HTTP, SQL y dependencias...</div>}
                  {simStep >= 3 && <div style={{ color: "#a855f7", marginTop: "4px" }}>[3/3] Consolidando mapa cinético e iteraciones agénticas (3/3)...</div>}
                  {simStep >= 4 && (
                    <div style={{ color: "#4ade80", marginTop: "8px", borderTop: "1px dashed #27272a", paddingTop: "8px" }}>
                      ✓ KSPR completó el análisis con éxito<br />
                      Archivos analizados: 67 | Elementos UI: 1305 | Flujos: 605<br />
                      Directorio de salida: ./kspr-context
                    </div>
                  )}
                </div>
              )}

              {terminalTab === "git" && (
                <div>
                  <div style={{ color: "#71717a" }}># Clonar y analizar un repositorio Git remoto de forma segura</div>
                  <div style={{ color: "#4ade80", margin: "8px 0" }}>$ kspr . --git-url https://github.com/org/repo.git --output ./repo-context</div>
                  <div style={{ color: "#a1a1aa", marginTop: "8px" }}>Clonación superficial (--depth 1) en directorio temporal seguro sin ejecución de código.</div>
                </div>
              )}

              {terminalTab === "dev" && (
                <div>
                  <div style={{ color: "#71717a" }}># Iniciar el shell interactivo OpenCode con el logotipo ASCII</div>
                  <div style={{ color: "#4ade80", margin: "8px 0" }}>$ kspr --interactive</div>
                  <div style={{ color: "#e2e8f0", marginTop: "6px" }}>
                    XXXX<br/>
                    &nbsp;XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX<br/>
                    XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX<br/>
                    <span style={{ color: "#38bdf8" }}>  KSPR CLI — OpenCode Interactive Terminal Agent (v0.1.0)</span><br/>
                    <span style={{ color: "#a1a1aa" }}>  Escribe una consulta, referencia archivos con @ o usa /help para comandos.</span><br/>
                    <span style={{ color: "#4ade80" }}>kspr (architect)&gt; /help</span>
                  </div>
                </div>
              )}
            </div>
          </div>
        </section>

        {/* Feature Grid */}
        <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "24px", marginBottom: 70 }}>
          <div style={{ background: "var(--white)", border: "1px solid var(--line)", borderRadius: "12px", padding: "28px" }}>
            <Shield size={24} style={{ marginBottom: 16, color: "#151515" }} />
            <h3 style={{ margin: "0 0 10px", fontSize: "18px", fontWeight: 700, fontFamily: "'Montserrat', sans-serif" }}>Análisis Estático Seguro</h3>
            <p style={{ margin: 0, color: "var(--muted)", fontSize: "14px", lineHeight: "1.6", fontFamily: "'Montserrat', sans-serif" }}>
              KSPR nunca ejecuta el código del repositorio analizado. Extrae componentes, rutas HTTP, eventos y consultas SQL puramente por heurísticas y AST seguros.
            </p>
          </div>

          <div style={{ background: "var(--white)", border: "1px solid var(--line)", borderRadius: "12px", padding: "28px" }}>
            <Cpu size={24} style={{ marginBottom: 16, color: "#151515" }} />
            <h3 style={{ margin: "0 0 10px", fontSize: "18px", fontWeight: 700, fontFamily: "'Montserrat', sans-serif" }}>Motor CLI & Backend FastAPI</h3>
            <p style={{ margin: 0, color: "var(--muted)", fontSize: "14px", lineHeight: "1.6", fontFamily: "'Montserrat', sans-serif" }}>
              Diseñado para ser ejecutado desde la terminal o integrado como API FastAPI con soporte para Google Gemini y gateways OpenAI-compatibles.
            </p>
          </div>

          <div style={{ background: "var(--white)", border: "1px solid var(--line)", borderRadius: "12px", padding: "28px" }}>
            <FolderArchive size={24} style={{ marginBottom: 16, color: "#151515" }} />
            <h3 style={{ margin: "0 0 10px", fontSize: "18px", fontWeight: 700, fontFamily: "'Montserrat', sans-serif" }}>Paquetes de Contexto Masivo</h3>
            <p style={{ margin: 0, color: "var(--muted)", fontSize: "14px", lineHeight: "1.6", fontFamily: "'Montserrat', sans-serif" }}>
              Exporta carpetas estructuradas con inventario UI, mapa de flujos, contratos, riesgos y contradicciones listos para entregar a agentes de IA.
            </p>
          </div>
        </section>

        {/* Quick CLI Reference */}
        <section style={{ background: "var(--white)", border: "1px solid var(--line)", borderRadius: "12px", padding: "36px", marginBottom: 60 }}>
          <h2 style={{ fontSize: "20px", marginTop: 0, marginBottom: 20, fontWeight: 700, fontFamily: "'Montserrat', sans-serif" }}>Referencia Rápida de Metodologías CLI</h2>
          <div style={{ display: "grid", gap: "14px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 16px", background: "#f8f9fa", borderRadius: "8px", border: "1px solid var(--line)", flexWrap: "wrap", gap: 8 }}>
              <code style={{ fontFamily: "'DM Mono', monospace", fontSize: "13px" }}>npm install -g kspr-ai && kspr --help</code>
              <span style={{ color: "var(--muted)", fontSize: "13px", fontFamily: "'Montserrat', sans-serif", fontWeight: 600 }}>Instalación global npm</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 16px", background: "#f8f9fa", borderRadius: "8px", border: "1px solid var(--line)", flexWrap: "wrap", gap: 8 }}>
              <code style={{ fontFamily: "'DM Mono', monospace", fontSize: "13px" }}>npx kspr-ai ./mi-proyecto --iterations 3</code>
              <span style={{ color: "var(--muted)", fontSize: "13px", fontFamily: "'Montserrat', sans-serif", fontWeight: 600 }}>Ejecución instantánea npx</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 16px", background: "#f8f9fa", borderRadius: "8px", border: "1px solid var(--line)", flexWrap: "wrap", gap: 8 }}>
              <code style={{ fontFamily: "'DM Mono', monospace", fontSize: "13px" }}>bash bin/kspr.sh ./repo --output ./context</code>
              <span style={{ color: "var(--muted)", fontSize: "13px", fontFamily: "'Montserrat', sans-serif", fontWeight: 600 }}>Wrapper Bash</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 16px", background: "#f8f9fa", borderRadius: "8px", border: "1px solid var(--line)", flexWrap: "wrap", gap: 8 }}>
              <code style={{ fontFamily: "'DM Mono', monospace", fontSize: "13px" }}>bun run bin/kspr.bun --interactive</code>
              <span style={{ color: "var(--muted)", fontSize: "13px", fontFamily: "'Montserrat', sans-serif", fontWeight: 600 }}>Wrapper Bun</span>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer style={{
        borderTop: "1px solid var(--line)",
        padding: "30px 5vw",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        background: "rgba(243, 242, 238, .8)",
        fontSize: "12px",
        color: "var(--muted)",
        fontFamily: "'Montserrat', sans-serif",
        fontWeight: 600
      }}>
        <div>KSPR AI · Terminal-First Reverse Engineering Agent</div>
        <div>Desarrollado y operado mediante terminal y CLI</div>
      </footer>
    </div>
  );
}
