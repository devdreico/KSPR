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
    <div className="app-shell">
      {/* Topbar */}
      <header className="topbar">
        <div className="brand">
          <img src="/casper-ai-logo.png" alt="KSPR AI" className="brand-logo" />
          <div>
            <strong>KSPR CLI</strong>
            <span>Reverse Engineering AI Agent</span>
          </div>
        </div>
        <div className="topbar-meta">
          <span className="live-dot" />
          <span>v0.1.0 · Terminal-First</span>
          <div className="divider" />
          <a
            href="https://github.com"
            target="_blank"
            rel="noreferrer"
            style={{ color: "var(--ink)", textDecoration: "none", fontWeight: 600, display: "flex", alignItems: "center", gap: 6 }}
          >
            GitHub <ArrowRight size={13} />
          </a>
        </div>
      </header>

      {/* Main Content */}
      <main>
        {/* Hero Section */}
        <section className="hero" style={{ flexDirection: "column", alignItems: "flex-start", gap: 32, paddingBottom: 40 }}>
          <div className="section-kicker">
            <Sparkles size={13} style={{ display: "inline", marginRight: 6 }} /> KSPR ENGINE · CLI INTERFACE
          </div>
          <h1 style={{ maxWidth: "100%", margin: 0 }}>
            Transforma sistemas legados en <em>mapas técnicos</em> desde la terminal.
          </h1>
          <p style={{ maxWidth: "700px", fontSize: "17px" }}>
            KSPR CLI es un agente agéntico de ingeniería inversa que escanea repositorios, extrae UI, rutas, eventos y dependencias de forma estática y segura, generando paquetes Markdown auditables para humanos y agentes.
          </p>

          {/* Quick Install Bar */}
          <div style={{ display: "flex", flexWrap: "wrap", gap: 14, marginTop: 10, width: "100%", maxWidth: "760px" }}>
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
              <span>pip install -e '.'</span>
              <button
                onClick={() => copyToClipboard("pip install -e '.'", "install-cmd")}
                style={{ background: "transparent", border: "none", color: "#aaa", cursor: "pointer", display: "flex", alignItems: "center", gap: 4 }}
                title="Copiar comando"
              >
                {copiedCmd === "install-cmd" ? <Check size={14} color="#4ade80" /> : <Copy size={14} />}
                <span style={{ fontSize: "11px" }}>{copiedCmd === "install-cmd" ? "Copiado" : "Copiar"}</span>
              </button>
            </div>
            <a
              href="#terminal-docs"
              style={{
                background: "#151515",
                color: "#fff",
                padding: "14px 24px",
                borderRadius: "10px",
                textDecoration: "none",
                fontWeight: 600,
                fontSize: "14px",
                display: "flex",
                alignItems: "center",
                gap: 8,
                transition: "background 0.2s"
              }}
            >
              <Terminal size={16} /> Ver guía CLI
            </a>
          </div>
        </section>

        {/* Interactive Terminal Demo */}
        <section id="terminal-docs" style={{ marginTop: 20, marginBottom: 60 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
            <h2 style={{ fontSize: "22px", margin: 0, fontWeight: 600 }}>Terminal de KSPR CLI</h2>
            <div style={{ display: "flex", gap: 8 }}>
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
                  fontWeight: 500
                }}
              >
                1. Instalación
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
                  fontWeight: 500
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
                  fontWeight: 500
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
                  fontWeight: 500
                }}
              >
                4. Desarrollo Core
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
                <span style={{ marginLeft: 8, fontSize: "12px", fontFamily: "'DM Mono', monospace", color: "#a1a1aa" }}>bash - kspr@enterprise:~</span>
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
                  fontFamily: "'DM Mono', monospace",
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
                  <div style={{ color: "#71717a" }}># Clonar el repositorio y configurar entorno virtual</div>
                  <div style={{ color: "#4ade80", margin: "8px 0" }}>$ python -m venv .venv && source .venv/bin/activate</div>
                  <div style={{ color: "#71717a", marginTop: "12px" }}># Instalar KSPR en modo editable con dependencias de desarrollo</div>
                  <div style={{ color: "#4ade80", margin: "8px 0" }}>$ pip install -e '.[dev]'</div>
                  <div style={{ color: "#a1a1aa", marginTop: "12px" }}>✓ KSPR Engine instalado correctamente. Ya puedes usar el comando <code style={{ color: "#f43f5e" }}>kspr</code>.</div>
                </div>
              )}

              {terminalTab === "analyze" && (
                <div>
                  <div style={{ color: "#71717a" }}># Analizar un directorio local y exportar artefactos Markdown</div>
                  <div style={{ color: "#4ade80", margin: "8px 0" }}>$ python cli/kspr.py ./mi-proyecto --output ./kspr-context --iterations 3</div>
                  {simStep >= 1 && <div style={{ color: "#facc15", marginTop: "6px" }}>[1/3] Ingesta segura completada: 42 archivos soportados.</div>}
                  {simStep >= 2 && <div style={{ color: "#38bdf8", marginTop: "4px" }}>[2/3] Extracción estática de UI, rutas, SQL y dependencias...</div>}
                  {simStep >= 3 && <div style={{ color: "#a855f7", marginTop: "4px" }}>[3/3] Consolidando mapa cinético e iteraciones agénticas (3/3)...</div>}
                  {simStep >= 4 && (
                    <div style={{ color: "#4ade80", marginTop: "8px", borderTop: "1px dashed #27272a", paddingTop: "8px" }}>
                      ✓ KSPR completó el análisis: anal_98124f<br />
                      Archivos: 42 | UI: 14 | Flujos: 8 | Artefactos: 5<br />
                      Salida: /workspaces/KSPR/kspr-context
                    </div>
                  )}
                </div>
              )}

              {terminalTab === "git" && (
                <div>
                  <div style={{ color: "#71717a" }}># Analizar un repositorio Git remoto directamente en modo lectura</div>
                  <div style={{ color: "#4ade80", margin: "8px 0" }}>$ python cli/kspr.py . --git-url https://github.com/org/repo.git --output ./repo-context</div>
                  <div style={{ color: "#a1a1aa", marginTop: "8px" }}>Clonación superficial (--depth 1) en directorio temporal seguro sin ejecución de código.</div>
                </div>
              )}

              {terminalTab === "dev" && (
                <div>
                  <div style={{ color: "#71717a" }}># Ejecutar el conjunto completo de pruebas unitarias (Pytest)</div>
                  <div style={{ color: "#4ade80", margin: "8px 0" }}>$ pytest</div>
                  <div style={{ color: "#e2e8f0", marginTop: "6px" }}>
                    ============================= test session starts ==============================<br />
                    platform linux -- Python 3.14.2, pytest-9.1.1<br />
                    collected 27 items<br />
                    <span style={{ color: "#4ade80" }}>backend/tests/test_analyzer.py . [ 3%]</span><br />
                    <span style={{ color: "#4ade80" }}>backend/tests/test_api.py ..... [ 22%]</span><br />
                    <span style={{ color: "#4ade80" }}>backend/tests/test_auth.py ............ [ 66%]</span><br />
                    <span style={{ color: "#4ade80" }}>======================== 27 passed in 7.98s ========================</span>
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
            <h3 style={{ margin: "0 0 10px", fontSize: "18px", fontWeight: 600 }}>Análisis Estático Seguro</h3>
            <p style={{ margin: 0, color: "var(--muted)", fontSize: "14px", lineHeight: "1.6" }}>
              KSPR nunca ejecuta el código del repositorio analizado. Extrae componentes, rutas HTTP, eventos y consultas SQL puramente por heurísticas y AST seguros.
            </p>
          </div>

          <div style={{ background: "var(--white)", border: "1px solid var(--line)", borderRadius: "12px", padding: "28px" }}>
            <Cpu size={24} style={{ marginBottom: 16, color: "#151515" }} />
            <h3 style={{ margin: "0 0 10px", fontSize: "18px", fontWeight: 600 }}>Motor CLI & Backend FastAPI</h3>
            <p style={{ margin: 0, color: "var(--muted)", fontSize: "14px", lineHeight: "1.6" }}>
              Diseñado para ser ejecutado desde la terminal o integrado como API FastAPI con soporte para Google Gemini y gateways OpenAI-compatibles.
            </p>
          </div>

          <div style={{ background: "var(--white)", border: "1px solid var(--line)", borderRadius: "12px", padding: "28px" }}>
            <FolderArchive size={24} style={{ marginBottom: 16, color: "#151515" }} />
            <h3 style={{ margin: "0 0 10px", fontSize: "18px", fontWeight: 600 }}>Paquetes de Contexto Masivo</h3>
            <p style={{ margin: 0, color: "var(--muted)", fontSize: "14px", lineHeight: "1.6" }}>
              Exporta carpetas estructuradas con inventario UI, mapa de flujos, contratos, riesgos y contradicciones listos para entregar a agentes de IA.
            </p>
          </div>
        </section>

        {/* Quick CLI Reference */}
        <section style={{ background: "var(--white)", border: "1px solid var(--line)", borderRadius: "12px", padding: "36px", marginBottom: 60 }}>
          <h2 style={{ fontSize: "20px", marginTop: 0, marginBottom: 20, fontWeight: 600 }}>Referencia Rápida de Comandos CLI</h2>
          <div style={{ display: "grid", gap: "14px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 16px", background: "#f8f9fa", borderRadius: "8px", border: "1px solid var(--line)" }}>
              <code style={{ fontFamily: "'DM Mono', monospace", fontSize: "13px" }}>python cli/kspr.py &lt;source&gt; --output &lt;dir&gt;</code>
              <span style={{ color: "var(--muted)", fontSize: "13px" }}>Analiza directorio local o archivo ZIP</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 16px", background: "#f8f9fa", borderRadius: "8px", border: "1px solid var(--line)" }}>
              <code style={{ fontFamily: "'DM Mono', monospace", fontSize: "13px" }}>python cli/kspr.py . --git-url &lt;url&gt; --iterations 3</code>
              <span style={{ color: "var(--muted)", fontSize: "13px" }}>Clona y analiza repositorio Git remoto</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 16px", background: "#f8f9fa", borderRadius: "8px", border: "1px solid var(--line)" }}>
              <code style={{ fontFamily: "'DM Mono', monospace", fontSize: "13px" }}>uvicorn kspr_engine.main:app --app-dir backend --reload</code>
              <span style={{ color: "var(--muted)", fontSize: "13px" }}>Inicia el servidor backend local FastAPI</span>
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
        color: "var(--muted)"
      }}>
        <div>KSPR AI · Terminal-First Reverse Engineering Agent</div>
        <div>Desarrollado y operado mediante terminal y CLI</div>
      </footer>
    </div>
  );
}
