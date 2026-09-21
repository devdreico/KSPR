import { Bot, Plus, X } from "lucide-react";
import { useState } from "react";

export type AgentProfile = {
  id: string;
  description: string;
  prompt: string;
  mode: "primary" | "subagent";
  model?: string;
  permission: "ask" | "allow" | "deny";
};

type AgentManagerProps = {
  agents: AgentProfile[];
  activeAgent: string;
  onChange: (agents: AgentProfile[]) => void;
  onSelect: (agent: AgentProfile) => void;
  onClose: () => void;
};

export function AgentManager({ agents, activeAgent, onChange, onSelect, onClose }: AgentManagerProps) {
  const [id, setId] = useState("");
  const [description, setDescription] = useState("");
  const [prompt, setPrompt] = useState("");
  const [mode, setMode] = useState<AgentProfile["mode"]>("primary");
  const [permission, setPermission] = useState<AgentProfile["permission"]>("ask");

  function addAgent() {
    const agentId = id.trim().toLowerCase().replace(/[^a-z0-9._-]/g, "-");
    if (!agentId || !prompt.trim()) return;
    const profile: AgentProfile = { id: agentId, description: description.trim() || "Agente personalizado de KSPR", prompt: prompt.trim(), mode, permission };
    onChange([...agents.filter((agent) => agent.id !== agentId), profile]);
    setId("");
    setDescription("");
    setPrompt("");
  }

  function removeAgent(agentId: string) {
    onChange(agents.filter((agent) => agent.id !== agentId));
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box agent-modal" onClick={(event) => event.stopPropagation()}>
        <div className="modal-header">
          <h2><Bot size={18} /> Agentes de KSPR <small>{agents.length} personalizados</small></h2>
          <button className="modal-close" onClick={onClose} aria-label="Cerrar agentes"><X size={18} /></button>
        </div>
        <div className="agent-list">
          <div className={activeAgent === "KSPR I" ? "agent-row active" : "agent-row"}><div className="agent-row-icon"><Bot size={15} /></div><div className="agent-row-copy"><strong>KSPR AI</strong><small>Parsing y reconstrucción de conocimiento · primary</small></div><button className="agent-use" onClick={() => onSelect({ id: "kspr-i", description: "KSPR AI CLI TOOL", prompt: "", mode: "primary", permission: "ask" })}>Usar</button></div>
          <div className={activeAgent === "KSPR I · Plan" ? "agent-row active" : "agent-row"}><div className="agent-row-icon"><Bot size={15} /></div><div className="agent-row-copy"><strong>KSPR AI · Plan</strong><small>Planificación basada en evidencia · primary</small></div><button className="agent-use" onClick={() => onSelect({ id: "kspr-i-plan", description: "KSPR AI Plan", prompt: "Trabaja en modo plan: separa decisiones y no propongas acciones destructivas.", mode: "primary", permission: "deny" })}>Usar</button></div>
          {agents.map((agent) => <div className={activeAgent === agent.id ? "agent-row active" : "agent-row"} key={agent.id}><div className="agent-row-icon"><Bot size={15} /></div><div className="agent-row-copy"><strong>{agent.id}</strong><small>{agent.description} · {agent.mode} · {agent.permission}</small></div><button className="agent-use" onClick={() => onSelect(agent)}>Usar</button><button className="agent-remove" onClick={() => removeAgent(agent.id)} aria-label={`Eliminar ${agent.id}`}><X size={13} /></button></div>)}
        </div>
        <div className="agent-add">
          <span className="section-kicker">CREAR AGENTE</span>
          <div className="config-grid"><div className="modal-field"><label>Nombre</label><input value={id} onChange={(event) => setId(event.target.value)} placeholder="security-reviewer" /></div><div className="modal-field"><label>Modo</label><select value={mode} onChange={(event) => setMode(event.target.value as AgentProfile["mode"])}><option value="primary">Primary · seleccionable</option><option value="subagent">Subagent · auxiliar</option></select></div></div>
          <div className="modal-field"><label>Descripción</label><input value={description} onChange={(event) => setDescription(event.target.value)} placeholder="Audita riesgos y contradicciones" /></div>
          <div className="config-grid"><div className="modal-field"><label>Permisos</label><select value={permission} onChange={(event) => setPermission(event.target.value as AgentProfile["permission"])}><option value="ask">Preguntar</option><option value="allow">Permitir</option><option value="deny">Solo lectura</option></select></div><div className="modal-field"><label>Prompt del agente</label><input value={prompt} onChange={(event) => setPrompt(event.target.value)} placeholder="Analiza solo evidencia verificable..." /></div></div>
          <button className="modal-button primary" onClick={addAgent} disabled={!id.trim() || !prompt.trim()}><Plus size={14} /> Guardar agente</button>
        </div>
        <p className="modal-help">Los agentes se guardan localmente y su prompt se incorpora al Main Prompt de cada ejecución.</p>
      </div>
    </div>
  );
}
