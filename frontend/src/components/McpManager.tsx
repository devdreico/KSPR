import { Plus, Server, X } from "lucide-react";
import { useState } from "react";

export type McpServerConfig = {
  type: "remote" | "local";
  url?: string;
  command?: string[];
  enabled?: boolean;
};

type McpManagerProps = {
  servers: Record<string, McpServerConfig>;
  onChange: (servers: Record<string, McpServerConfig>) => void;
  onClose: () => void;
};

export function McpManager({ servers, onChange, onClose }: McpManagerProps) {
  const [name, setName] = useState("");
  const [type, setType] = useState<McpServerConfig["type"]>("remote");
  const [url, setUrl] = useState("");
  const [command, setCommand] = useState("");

  function addServer() {
    const serverName = name.trim().replace(/[^a-zA-Z0-9._-]/g, "-");
    if (!serverName) return;
    onChange({
      ...servers,
      [serverName]: {
        type,
        enabled: true,
        ...(type === "remote" ? { url: url.trim() } : { command: command.trim().split(/\s+/).filter(Boolean) }),
      },
    });
    setName("");
    setUrl("");
    setCommand("");
  }

  function removeServer(serverName: string) {
    const next = { ...servers };
    delete next[serverName];
    onChange(next);
  }

  function toggleServer(serverName: string) {
    const server = servers[serverName];
    if (!server) return;
    onChange({ ...servers, [serverName]: { ...server, enabled: server.enabled === false } });
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box mcp-modal" onClick={(event) => event.stopPropagation()}>
        <div className="modal-header">
          <h2><Server size={18} /> Servidores MCP <small>{Object.keys(servers).length} configurados</small></h2>
          <button className="modal-close" onClick={onClose} aria-label="Cerrar MCP"><X size={18} /></button>
        </div>
        <div className="mcp-list">
          {Object.entries(servers).map(([serverName, server]) => (
            <div className={server.enabled === false ? "mcp-row disabled" : "mcp-row"} key={serverName}>
              <div className="mcp-row-icon"><Server size={15} /></div>
              <div className="mcp-row-copy"><strong>{serverName}</strong><small>{server.type === "remote" ? server.url || "URL pendiente" : (server.command || []).join(" ") || "Comando pendiente"}</small></div>
              <button className="mcp-toggle" onClick={() => toggleServer(serverName)}>{server.enabled === false ? "Inactivo" : "Activo"}</button>
              <button className="mcp-remove" onClick={() => removeServer(serverName)} aria-label={`Eliminar ${serverName}`}><X size={13} /></button>
            </div>
          ))}
          {!Object.keys(servers).length && <div className="command-empty">No hay servidores MCP configurados.</div>}
        </div>
        <div className="mcp-add">
          <span className="section-kicker">AÑADIR SERVIDOR</span>
          <div className="config-grid">
            <div className="modal-field"><label>Nombre</label><input value={name} onChange={(event) => setName(event.target.value)} placeholder="docs-context" /></div>
            <div className="modal-field"><label>Tipo</label><select value={type} onChange={(event) => setType(event.target.value as McpServerConfig["type"])}><option value="remote">Remoto · URL</option><option value="local">Local · comando</option></select></div>
          </div>
          {type === "remote" ? <div className="modal-field"><label>URL MCP</label><input value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://example.com/mcp" /></div> : <div className="modal-field"><label>Comando</label><input value={command} onChange={(event) => setCommand(event.target.value)} placeholder="npx -y @modelcontextprotocol/server-filesystem" /></div>}
          <button className="modal-button primary" onClick={addServer} disabled={!name.trim() || (type === "remote" ? !url.trim() : !command.trim())}><Plus size={14} /> Añadir servidor</button>
        </div>
        <p className="modal-help">Los servidores se guardan en la configuración local del navegador. KSPR registra su definición, pero no ejecuta herramientas MCP en esta versión segura.</p>
      </div>
    </div>
  );
}
