import { Check, FileText, List, Search, Terminal, X } from "lucide-react";
import { useMemo, useState } from "react";
import type { SourceFile } from "../lib/api";

type ContextPanelProps = {
  files: SourceFile[];
  selectedPath: string;
  onSelect: (path: string) => void;
  onRemove: (path: string) => void;
  permissionMode: "ask" | "allow" | "deny";
  onInsert: (text: string) => void;
  onClose: () => void;
};

type ToolName = "list" | "read" | "grep";

export function ContextPanel({ files, selectedPath, onSelect, onRemove, permissionMode, onInsert, onClose }: ContextPanelProps) {
  const selected = files.find((file) => file.path === selectedPath) || files[0];
  const [query, setQuery] = useState("");
  const [toolOutput, setToolOutput] = useState("");
  const [pendingTool, setPendingTool] = useState<ToolName | null>(null);
  const [toolName, setToolName] = useState("");
  const matches = useMemo(() => {
    if (!query.trim()) return [];
    try {
      const expression = new RegExp(query, "i");
      return files.flatMap((file) => file.content.split("\n").map((line, index) => expression.test(line) ? `${file.path}:${index + 1}  ${line.trim()}` : "").filter(Boolean)).slice(0, 120);
    } catch {
      return [];
    }
  }, [files, query]);

  function runTool(tool: ToolName) {
    setPendingTool(null);
    setToolName(tool);
    if (tool === "list") setToolOutput(files.map((file) => `${file.path} · ${file.content.split("\n").length} líneas`).join("\n") || "Sin archivos en el contexto.");
    if (tool === "read") setToolOutput(selected?.content || "Selecciona un archivo para leerlo.");
    if (tool === "grep") setToolOutput(matches.join("\n") || "Sin coincidencias para la expresión indicada.");
  }

  function requestTool(tool: ToolName) {
    if (permissionMode === "deny") {
      setToolName(tool);
      setToolOutput(`Herramienta ${tool} bloqueada: el agente está en modo solo lectura.`);
      return;
    }
    if (permissionMode === "ask") {
      setPendingTool(tool);
      return;
    }
    runTool(tool);
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box context-modal" onClick={(event) => event.stopPropagation()}>
        <div className="modal-header">
          <h2><FileText size={18} /> Contexto adjunto <small>{files.length} archivos</small></h2>
          <button className="modal-close" onClick={onClose} aria-label="Cerrar contexto"><X size={18} /></button>
        </div>
        {!files.length ? <div className="context-empty">Adjunta, pega o arrastra archivos al compositor para inspeccionarlos aquí.</div> : (
          <div className="context-layout">
            <aside className="context-nav">
              <span className="section-kicker">REFERENCIAS</span>
              {files.map((file) => <div className={file.path === selected?.path ? "context-file active" : "context-file"} key={file.path}>
                <button onClick={() => onSelect(file.path)}><FileText size={13} /><span>{file.path}</span></button>
                <button className="context-remove" onClick={() => onRemove(file.path)} aria-label={`Quitar ${file.path}`}><X size={12} /></button>
              </div>)}
            </aside>
            <div className="context-preview">
              {selected && <><div className="context-preview-head"><strong>{selected.path}</strong><span>{selected.content.split("\n").length} líneas</span></div><pre>{selected.content}</pre></>}
            </div>
          </div>
        )}
        <div className="context-tools">
          <div className="context-tools-head"><span className="section-kicker">HERRAMIENTAS DE CONTEXTO · {permissionMode}</span><span>read · list · grep</span></div>
          <div className="context-tool-row"><button onClick={() => requestTool("list")}><List size={13} /> list</button><button onClick={() => requestTool("read")}><FileText size={13} /> read seleccionado</button><div className="context-grep"><Search size={13} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="regex para grep" /><button onClick={() => requestTool("grep")}><Terminal size={13} /> grep</button></div></div>
          {pendingTool && <div className="context-approval"><span>El modo <strong>ask</strong> solicita aprobación para ejecutar <code>{pendingTool}</code> sobre el contexto.</span><button onClick={() => runTool(pendingTool)}><Check size={13} /> Aprobar una vez</button></div>}
          {toolName && <div className="context-tool-output"><div><strong>{toolName}</strong><button onClick={() => onInsert(toolOutput)} title="Insertar resultado en el prompt"><FileText size={13} /> Insertar</button></div><pre>{toolOutput}</pre></div>}
        </div>
      </div>
    </div>
  );
}
