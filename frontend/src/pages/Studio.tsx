import { useEffect, useMemo, useRef, useState, type ChangeEvent, type FormEvent, type KeyboardEvent } from "react";
import {
  ArrowUp,
  Check,
  ChevronDown,
  Command,
  FileText,
  HelpCircle,
  LoaderCircle,
  Menu,
  Mic,
  Paperclip,
  Plus,
  Search,
  Settings2,
  Sparkles,
  Square,
  Terminal,
  X,
} from "lucide-react";
import { ArtifactPanel } from "../components/ArtifactPanel";
import { ContextPanel } from "../components/ContextPanel";
import { MessageContent } from "../components/MessageContent";
import { McpManager, type McpServerConfig } from "../components/McpManager";
import { AgentManager, type AgentProfile } from "../components/AgentManager";
import {
  checkProviderStatus,
  ingestArchive,
  runAnalysis,
  transcribeAudio,
  type AnalysisResult,
  type GeminiModel,
  type ProviderAuth,
  type SourceFile,
} from "../lib/api";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  files?: string[];
  meta?: string;
  createdAt: number;
};

type SessionRecord = {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  messages: ChatMessage[];
  contextFiles?: SourceFile[];
  model?: { providerId: string; modelId: string };
  variant?: string;
  agent?: string;
  permissionMode?: PermissionMode;
};

type ModelOption = GeminiModel & { providerId: string; providerName: string; variants?: string[]; custom?: boolean };

type RecognitionResult = { isFinal: boolean; 0: { transcript: string } };
type RecognitionEvent = { resultIndex: number; results: RecognitionResult[] };
type Recognition = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  start: () => void;
  stop: () => void;
  onresult: ((event: RecognitionEvent) => void) | null;
  onerror: (() => void) | null;
  onend: (() => void) | null;
};
type RecognitionConstructor = new () => Recognition;

type CommandItem = { id: string; title: string; description: string; slash: string; shortcut?: string; template?: string };
type PermissionMode = "ask" | "allow" | "deny";

const DEFAULT_MODELS: ModelOption[] = [
  { id: "kspr-local", name: "KSPR Local", description: "Modo determinista para comprobar la interfaz sin una API externa.", providerId: "local", providerName: "KSPR", variants: ["default"] },
  { id: "gemini-2.5-flash", name: "Gemini 2.5 Flash", description: "Modelo rápido y equilibrado de Google.", providerId: "gemini", providerName: "Google Gemini", variants: ["low", "high"] },
  { id: "gemini-2.5-pro", name: "Gemini 2.5 Pro", description: "Modelo avanzado para razonamiento y código.", providerId: "gemini", providerName: "Google Gemini", variants: ["low", "high"] },
];

const COMMANDS: CommandItem[] = [
  { id: "new", title: "Nueva sesión", description: "Abre una conversación limpia", slash: "/new", shortcut: "⌘⇧S" },
  { id: "sessions", title: "Cambiar de sesión", description: "Busca entre las conversaciones guardadas", slash: "/sessions", shortcut: "⌘L" },
  { id: "models", title: "Cambiar modelo", description: "Abre el catálogo por proveedor", slash: "/models", shortcut: "⌘M" },
  { id: "provider", title: "Conectar proveedor", description: "Añade una API y descubre sus modelos", slash: "/connect" },
  { id: "config", title: "Configuración de KSPR AI CLI TOOL", description: "Tema, agente, Main Prompt y comandos", slash: "/config" },
  { id: "agents", title: "Gestionar agentes", description: "Crea agentes con prompt, modo y permisos", slash: "/agents" },
  { id: "mcp", title: "Configurar MCP", description: "Gestiona el endpoint de contexto externo", slash: "/mcp" },
  { id: "permissions", title: "Permisos del agente", description: "Define si las acciones requieren aprobación", slash: "/permissions" },
  { id: "export", title: "Exportar conversación", description: "Descarga la sesión actual como Markdown", slash: "/export", shortcut: "⌘⇧E" },
  { id: "share", title: "Compartir conversación", description: "Copia una transcripción portable de la sesión", slash: "/share" },
  { id: "editor", title: "Editor de mensaje", description: "Enfoca el editor de conversación", slash: "/editor", shortcut: "⌘E" },
  { id: "init", title: "Inicializar agente", description: "Abre el Main Prompt inicial de KSPR AI CLI TOOL", slash: "/init" },
  { id: "compact", title: "Compactar sesión", description: "Reduce el contexto visible de la conversación", slash: "/compact" },
  { id: "thinking", title: "Mostrar revisiones", description: "Alterna el paquete de revisiones agenticas", slash: "/thinking" },
  { id: "details", title: "Detalles de ejecución", description: "Muestra el paquete técnico de salida", slash: "/details" },
  { id: "context", title: "Ver contexto adjunto", description: "Inspecciona y navega los archivos de esta sesión", slash: "/context" },
  { id: "undo", title: "Deshacer turno", description: "Retira el último turno de la conversación", slash: "/undo", shortcut: "⌘Z" },
  { id: "redo", title: "Rehacer turno", description: "Restaura el turno retirado", slash: "/redo", shortcut: "⌘⇧Z" },
  { id: "themes", title: "Cambiar tema", description: "Abre los temas de interfaz", slash: "/themes" },
  { id: "help", title: "Ayuda y comandos", description: "Consulta las acciones disponibles", slash: "/help" },
];

const starterPrompts = [
  "Mapea la funcionalidad de este sistema legado",
  "¿Qué botones y eventos cambian el estado?",
  "Propón los endpoints que reemplazan esta interfaz",
];

const AGENT_MODES = ["KSPR I", "KSPR I · Plan", "KSPR I · Review"] as const;

function id(prefix: string) {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function newSession(): SessionRecord {
  const now = Date.now();
  return { id: id("session"), title: "Nueva sesión", createdAt: now, updatedAt: now, messages: [] };
}

function readSessions(): SessionRecord[] {
  try {
    const parsed = JSON.parse(localStorage.getItem("kspr_sessions") || "[]") as SessionRecord[];
    if (Array.isArray(parsed) && parsed.length) return parsed;
  } catch {
    // Datos locales corruptos no deben impedir abrir el workspace.
  }
  return [newSession()];
}

const INITIAL_SESSIONS = readSessions();

function titleFor(messages: ChatMessage[], fallback: string) {
  const first = messages.find((message) => message.role === "user")?.content.trim();
  return first ? first.replace(/\s+/g, " ").slice(0, 52) : fallback;
}

function parseCustomCommands(value: string): CommandItem[] {
  return value.split("\n").map((line) => line.trim()).filter(Boolean).flatMap((line) => {
    const match = line.match(/^\/(\S+)\s*(?:—|-|:)\s*(.*?)(?:\s+::\s+(.+))?$/);
    if (!match) return [];
    return [{ id: `custom:${match[1]}`, title: `/${match[1]}`, description: match[2] || "Comando personalizado de KSPR", slash: `/${match[1]}`, template: match[3] || match[2] }];
  });
}

function expandCommandTemplate(command: CommandItem, argsText: string) {
  const args = argsText.trim() ? argsText.trim().split(/\s+/) : [];
  return (command.template || command.description)
    .replace(/\$ARGUMENTS/g, argsText.trim())
    .replace(/\$(\d+)/g, (_match, index: string) => args[Number(index) - 1] || "")
    .trim();
}

function readCustomModels(): ModelOption[] {
  try {
    const parsed = JSON.parse(localStorage.getItem("kspr_custom_models") || "[]") as ModelOption[];
    return Array.isArray(parsed) ? parsed.filter((model) => model.custom && model.id && model.providerId) : [];
  } catch {
    return [];
  }
}

function readCustomAgents(): AgentProfile[] {
  try {
    const parsed = JSON.parse(localStorage.getItem("kspr_agents") || "[]") as AgentProfile[];
    return Array.isArray(parsed) ? parsed.filter((agent) => agent?.id && agent?.prompt) : [];
  } catch {
    return [];
  }
}

function getSpeechRecognition(): RecognitionConstructor | undefined {
  const browser = window as typeof window & { SpeechRecognition?: RecognitionConstructor; webkitSpeechRecognition?: RecognitionConstructor };
  return browser.SpeechRecognition || browser.webkitSpeechRecognition;
}

function sessionMarkdown(session: SessionRecord) {
  return [`# ${session.title}`, "", `> Exportado por KSPR AI CLI TOOL · ${new Date(session.updatedAt).toLocaleString()}`, "", ...session.messages.flatMap((message) => [`## ${message.role === "user" ? "Usuario" : "KSPR AI CLI TOOL"}`, "", message.content, message.files?.length ? `\nArchivos: ${message.files.join(", ")}` : "", ""])].join("\n");
}

function exportSession(session: SessionRecord | undefined) {
  if (!session) return;
  const markdown = sessionMarkdown(session);
  const link = document.createElement("a");
  link.href = URL.createObjectURL(new Blob([markdown], { type: "text/markdown;charset=utf-8" }));
  link.download = `${session.title.toLowerCase().replace(/[^a-z0-9]+/gi, "-").replace(/^-|-$/g, "") || "kspr-session"}.md`;
  link.click();
  URL.revokeObjectURL(link.href);
}

function downloadJson(filename: string, value: unknown) {
  const link = document.createElement("a");
  link.href = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2)], { type: "application/json;charset=utf-8" }));
  link.download = filename;
  link.click();
  URL.revokeObjectURL(link.href);
}

export function Studio() {
  const [sessions, setSessions] = useState<SessionRecord[]>(INITIAL_SESSIONS);
  const [activeSessionId, setActiveSessionId] = useState(INITIAL_SESSIONS[0].id);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [files, setFiles] = useState<SourceFile[]>([]);
  const [contextFiles, setContextFiles] = useState<SourceFile[]>(INITIAL_SESSIONS[0].contextFiles || []);
  const [models, setModels] = useState<ModelOption[]>(() => [...DEFAULT_MODELS, ...readCustomModels()]);
  const [customAgents, setCustomAgents] = useState<AgentProfile[]>(readCustomAgents);
  const [modelId, setModelId] = useState(INITIAL_SESSIONS[0].model?.modelId || DEFAULT_MODELS[0].id);
  const [providerId, setProviderId] = useState(INITIAL_SESSIONS[0].model?.providerId || DEFAULT_MODELS[0].providerId);
  const [modelVariant, setModelVariant] = useState(INITIAL_SESSIONS[0].variant || "default");
  const [modelEffort, setModelEffort] = useState(() => localStorage.getItem("kspr_model_effort") || "medium");
  const [geminiApiKey, setGeminiApiKey] = useState("");
  const [geminiAuthMode, setGeminiAuthMode] = useState<"api_key" | "bearer">("api_key");
  const [compatibleApiKey, setCompatibleApiKey] = useState("");
  const [compatibleBaseUrl, setCompatibleBaseUrl] = useState("https://api.openai.com/v1");
  const [providerConfigs, setProviderConfigs] = useState<Record<string, ProviderAuth>>({});
  const [theme, setTheme] = useState(() => localStorage.getItem("kspr_theme") || "light");
  const [personalityMd, setPersonalityMd] = useState(() => localStorage.getItem("kspr_main_prompt") || "# KSPR Main Prompt\nEres KSPR I, una inteligencia artificial experta en ingeniería inversa de sistemas legados. Analiza con rigor, precisión y estructura.");
  const [agentMode, setAgentMode] = useState(() => localStorage.getItem("kspr_agent_mode") || "KSPR I");
  const [permissionMode, setPermissionMode] = useState<PermissionMode>(() => (localStorage.getItem("kspr_permission_mode") as PermissionMode) || "ask");
  const [mcpConfig, setMcpConfig] = useState(() => localStorage.getItem("kspr_mcp_config") || "mcp://local-context-server");
  const [mcpServers, setMcpServers] = useState<Record<string, McpServerConfig>>(() => {
    try {
      const parsed = JSON.parse(localStorage.getItem("kspr_mcp_servers") || "null") as Record<string, McpServerConfig> | null;
      if (parsed && typeof parsed === "object") return parsed;
    } catch {
      // Una configuración MCP local corrupta no debe impedir abrir el workspace.
    }
    return { "kspr-context": { type: "remote", url: localStorage.getItem("kspr_mcp_config") || "mcp://local-context-server", enabled: true } };
  });
  const [customCommands, setCustomCommands] = useState(() => localStorage.getItem("kspr_custom_commands") || "");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [sessionSearch, setSessionSearch] = useState("");
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const [commandQuery, setCommandQuery] = useState("");
  const [commandIndex, setCommandIndex] = useState(0);
  const [apiHubOpen, setApiHubOpen] = useState(false);
  const [modelSearch, setModelSearch] = useState("");
  const [customModelOpen, setCustomModelOpen] = useState(false);
  const [customModelId, setCustomModelId] = useState("");
  const [customModelName, setCustomModelName] = useState("");
  const [customModelProvider, setCustomModelProvider] = useState("openai-compatible");
  const [configModalOpen, setConfigModalOpen] = useState(false);
  const [helpModalOpen, setHelpModalOpen] = useState(false);
  const [mcpModalOpen, setMcpModalOpen] = useState(false);
  const [agentModalOpen, setAgentModalOpen] = useState(false);
  const [connectProvider, setConnectProvider] = useState("gemini");
  const [customProviderId, setCustomProviderId] = useState("");
  const [customProviderName, setCustomProviderName] = useState("");
  const [connectKey, setConnectKey] = useState("");
  const [connectBaseUrl, setConnectBaseUrl] = useState("https://api.openai.com/v1");
  const [providerStatus, setProviderStatus] = useState("No conectado");
  const [providerConnected, setProviderConnected] = useState(false);
  const [running, setRunning] = useState(false);
  const [runProgress, setRunProgress] = useState(0);
  const [runStage, setRunStage] = useState("Preparando contexto");
  const [liveResponse, setLiveResponse] = useState("");
  const [recording, setRecording] = useState(false);
  const [showReviews, setShowReviews] = useState(false);
  const [contextModalOpen, setContextModalOpen] = useState(false);
  const [selectedContextPath, setSelectedContextPath] = useState("");
  const [draggingFiles, setDraggingFiles] = useState(false);
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [undoneMessages, setUndoneMessages] = useState<ChatMessage[]>([]);
  const composerRef = useRef<HTMLTextAreaElement | null>(null);
  const recognitionRef = useRef<Recognition | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const abortControllerRef = useRef<AbortController | null>(null);

  const activeSession = sessions.find((session) => session.id === activeSessionId);
  const selectedModel = models.find((model) => model.id === modelId && model.providerId === providerId) || models[0];
  const hasConversation = messages.length > 0;
  const filteredSessions = useMemo(() => sessions.filter((session) => session.title.toLowerCase().includes(sessionSearch.toLowerCase())), [sessions, sessionSearch]);
  const filteredModels = useMemo(() => models.filter((model) => `${model.name} ${model.id} ${model.providerName}`.toLowerCase().includes(modelSearch.toLowerCase())), [models, modelSearch]);
  const allCommands = useMemo(() => [...COMMANDS, ...parseCustomCommands(customCommands)], [customCommands]);
  const filteredCommands = useMemo(() => allCommands.filter((command) => `${command.title} ${command.description} ${command.slash}`.toLowerCase().includes(commandQuery.toLowerCase())), [allCommands, commandQuery]);
  const showSlashMenu = draft.startsWith("/") && !draft.includes(" ");
  const fileQuery = draft.lastIndexOf("@") >= 0 ? draft.slice(draft.lastIndexOf("@") + 1) : "";
  const showFileMenu = fileQuery.length > 0 && !fileQuery.includes(" ") && files.length > 0;
  const filteredFiles = files.filter((file) => file.path.toLowerCase().includes(fileQuery.toLowerCase()));

  useEffect(() => {
    if (!contextFiles.length) {
      setSelectedContextPath("");
      return;
    }
    if (!contextFiles.some((file) => file.path === selectedContextPath)) setSelectedContextPath(contextFiles[0].path);
  }, [contextFiles, selectedContextPath]);

  useEffect(() => {
    const initial = sessions.find((session) => session.id === activeSessionId);
    if (initial) {
      setMessages(initial.messages || []);
      setContextFiles(initial.contextFiles || []);
    }
    // La sesión inicial se hidrata una vez al montar el workspace.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    setSessions((current) => current.map((session) => session.id === activeSessionId ? {
      ...session,
      messages,
      contextFiles,
      title: titleFor(messages, session.title),
      model: { providerId, modelId },
      variant: modelVariant,
      agent: agentMode,
      permissionMode,
      updatedAt: Date.now(),
    } : session));
  }, [activeSessionId, messages, contextFiles, providerId, modelId, modelVariant, agentMode, permissionMode]);

  useEffect(() => {
    localStorage.setItem("kspr_sessions", JSON.stringify(sessions.slice(0, 50)));
  }, [sessions]);

  useEffect(() => {
    localStorage.setItem("kspr_custom_models", JSON.stringify(models.filter((model) => model.custom)));
  }, [models]);

  useEffect(() => {
    localStorage.setItem("kspr_mcp_servers", JSON.stringify(mcpServers));
  }, [mcpServers]);

  useEffect(() => {
    localStorage.setItem("kspr_agents", JSON.stringify(customAgents));
  }, [customAgents]);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("kspr_theme", theme);
  }, [theme]);

  useEffect(() => {
    if (connectProvider === "gemini") {
      setConnectKey(geminiApiKey);
      return;
    }
    const providerKey = connectProvider === "custom" ? customProviderId : connectProvider;
    setConnectKey(providerConfigs[providerKey]?.apiKey || compatibleApiKey);
    setConnectBaseUrl(providerConfigs[providerKey]?.baseUrl || compatibleBaseUrl);
  }, [connectProvider, customProviderId, providerConfigs]);

  useEffect(() => {
    const listener = (event: globalThis.KeyboardEvent) => {
      const mod = event.metaKey || event.ctrlKey;
      const key = event.key.toLowerCase();
      if (mod && key === "k") {
        event.preventDefault();
        setCommandPaletteOpen(true);
        setCommandQuery("");
      }
      if (mod && key === "l") { event.preventDefault(); setSidebarOpen(true); }
      if (mod && key === "m") { event.preventDefault(); setApiHubOpen(true); }
      if (mod && event.key === ",") { event.preventDefault(); setConfigModalOpen(true); }
      if (mod && key === "e" && event.shiftKey) { event.preventDefault(); exportSession(activeSession); }
      else if (mod && key === "e") { event.preventDefault(); composerRef.current?.focus(); }
      if (mod && event.key.toLowerCase() === "s" && event.shiftKey) { event.preventDefault(); createSession(); }
      if (mod && key === "z" && event.shiftKey) { event.preventDefault(); redoLastTurn(); }
      else if (mod && key === "z") { event.preventDefault(); undoLastTurn(); }
      if (event.key === "Tab" && !mod && event.target instanceof HTMLElement && !["INPUT", "SELECT"].includes(event.target.tagName)) {
        event.preventDefault();
        setAgentMode((current) => {
          const index = AGENT_MODES.indexOf(current as typeof AGENT_MODES[number]);
          const next = AGENT_MODES[(index + 1) % AGENT_MODES.length];
          localStorage.setItem("kspr_agent_mode", next);
          return next;
        });
      }
      if (event.key === "Escape") {
        setCommandPaletteOpen(false);
        setApiHubOpen(false);
        setConfigModalOpen(false);
        setHelpModalOpen(false);
        setContextModalOpen(false);
        setMcpModalOpen(false);
        setAgentModalOpen(false);
      }
      if (event.key.toLowerCase() === "g" && event.ctrlKey && running) {
        event.preventDefault();
        abortControllerRef.current?.abort();
      }
    };
    window.addEventListener("keydown", listener);
    return () => window.removeEventListener("keydown", listener);
  }, [running, activeSession, messages, undoneMessages]);

  function authFor(provider: string): ProviderAuth {
    if (provider === "local") return { provider };
    if (provider === "gemini") return { provider, apiKey: geminiApiKey, authMode: geminiAuthMode };
    const configured = providerConfigs[provider];
    return { provider, apiKey: configured?.apiKey || compatibleApiKey, baseUrl: configured?.baseUrl || compatibleBaseUrl, authMode: configured?.authMode };
  }

  function selectModel(model: ModelOption) {
    setProviderId(model.providerId);
    setModelId(model.id);
    setModelVariant(model.variants?.[0] || "default");
    setApiHubOpen(false);
  }

  function selectAgent(agent: AgentProfile) {
    const label = agent.id === "kspr-i" ? "KSPR I" : agent.id === "kspr-i-plan" ? "KSPR I · Plan" : agent.id === "kspr-i-review" ? "KSPR I · Review" : agent.id;
    setAgentMode(label);
    setPermissionMode(agent.permission);
    localStorage.setItem("kspr_agent_mode", label);
    localStorage.setItem("kspr_permission_mode", agent.permission);
  }

  function promptForActiveAgent() {
    const custom = customAgents.find((agent) => agent.id === agentMode);
    if (custom?.prompt) return custom.prompt;
    if (agentMode === "KSPR I · Plan") return "Trabaja en modo plan: separa decisiones y no propongas acciones destructivas.";
    if (agentMode === "KSPR I · Review") return "Trabaja en modo revisión: busca contradicciones, riesgos y evidencia faltante.";
    return "";
  }

  function addCustomModel() {
    const modelIdValue = customModelId.trim();
    if (!modelIdValue) return;
    const model: ModelOption = {
      id: modelIdValue,
      name: customModelName.trim() || modelIdValue,
      description: "Modelo definido manualmente en KSPR.",
      providerId: customModelProvider,
      providerName: customModelProvider === "gemini" ? "Google Gemini" : "OpenAI-compatible",
      variants: ["default"],
      custom: true,
    };
    setModels((current) => [...current.filter((item) => !(item.id === model.id && item.providerId === model.providerId)), model]);
    selectModel(model);
    setCustomModelId("");
    setCustomModelName("");
    setCustomModelOpen(false);
  }

  function exportConfiguration() {
    const providerModels = models.reduce<Record<string, Record<string, { name: string; description: string; variants?: string[] }>>>((groups, model) => {
      groups[model.providerId] ||= {};
      groups[model.providerId][model.id] = { name: model.name, description: model.description, variants: model.variants };
      return groups;
    }, {});
    const commands = Object.fromEntries(parseCustomCommands(customCommands).map((command) => [command.title.slice(1), { description: command.description, template: command.template || command.description }]));
    const defaultAgent = agentMode === "KSPR I" ? "kspr-i" : agentMode === "KSPR I · Plan" ? "kspr-i-plan" : agentMode === "KSPR I · Review" ? "kspr-i-review" : customAgents.some((agent) => agent.id === agentMode) ? agentMode : "kspr-i";
    downloadJson("kspr.config.json", {
      $schema: "https://kspr.dev/config.json",
      model: `${providerId}/${modelId}`,
      small_model: "gemini/gemini-2.5-flash",
      provider: {
        ...Object.fromEntries(Object.entries(providerModels).map(([key, modelMap]) => [key, { name: key === "gemini" ? "Google Gemini" : key === "local" ? "KSPR" : "OpenAI-compatible", options: providerConfigs[key]?.baseUrl ? { baseURL: providerConfigs[key]?.baseUrl } : key === "openai-compatible" ? { baseURL: compatibleBaseUrl } : {}, models: modelMap }])),
      },
      agent: {
        "kspr-i": { description: "KSPR AI CLI TOOL — knowledge reconstruction", mode: "primary", model: `${providerId}/${modelId}`, prompt: personalityMd },
        "kspr-i-plan": { description: "KSPR AI CLI TOOL · Plan — analysis without changes", mode: "primary", model: `${providerId}/${modelId}`, prompt: `${personalityMd}\nWork in plan mode: separate decisions and do not propose destructive actions.` },
        "kspr-i-review": { description: "KSPR AI CLI TOOL · Review — evidence review", mode: "primary", model: `${providerId}/${modelId}`, prompt: `${personalityMd}\nWork in review mode: look for contradictions, risks and missing evidence.` },
        ...Object.fromEntries(customAgents.map((agent) => [agent.id, { description: agent.description, mode: agent.mode, model: agent.model || `${providerId}/${modelId}`, prompt: agent.prompt, permission: agent.permission }])),
      },
      default_agent: defaultAgent,
      permission: permissionMode === "allow" ? "allow" : { "*": permissionMode },
      command: commands,
      mcp: mcpServers,
      theme,
      note: "Las credenciales nunca se exportan; reconecta cada proveedor desde /connect.",
    });
  }

  function importConfiguration(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    void file.text().then((raw) => {
      try {
        const config = JSON.parse(raw) as Record<string, unknown>;
        const providers = (config.provider || config.providers) as Record<string, unknown> | undefined;
        const importedModels: ModelOption[] = [];
        const importedProviderConfigs: Record<string, ProviderAuth> = {};
        if (providers && typeof providers === "object") {
          for (const [providerKey, providerValue] of Object.entries(providers)) {
            if (!providerValue || typeof providerValue !== "object") continue;
            const provider = providerValue as { name?: string; models?: Record<string, { name?: string; description?: string; variants?: string[] }> };
            const options = providerValue as { options?: { baseURL?: string } };
            if (options.options?.baseURL) importedProviderConfigs[providerKey] = { provider: providerKey, baseUrl: options.options.baseURL };
            for (const [modelKey, modelValue] of Object.entries(provider.models || {})) {
              importedModels.push({ id: modelKey, name: modelValue?.name || modelKey, description: modelValue?.description || "Modelo importado desde configuración KSPR.", providerId: providerKey, providerName: provider.name || providerKey, variants: modelValue?.variants?.length ? modelValue.variants : ["default"], custom: true });
            }
          }
        }
        if (Object.keys(importedProviderConfigs).length) setProviderConfigs((current) => ({ ...current, ...importedProviderConfigs }));
        if (importedModels.length) setModels((current) => [...current.filter((item) => !importedModels.some((incoming) => incoming.id === item.id && incoming.providerId === item.providerId)), ...importedModels]);
        const importedDefaultAgent = typeof config.default_agent === "string" ? config.default_agent : "KSPR I";
        const defaultAgent = importedDefaultAgent === "kspr-i" ? "KSPR I" : importedDefaultAgent === "kspr-i-plan" ? "KSPR I · Plan" : importedDefaultAgent === "kspr-i-review" ? "KSPR I · Review" : importedDefaultAgent;
        setAgentMode(defaultAgent);
        localStorage.setItem("kspr_agent_mode", defaultAgent);
        const importedPermission = typeof config.permission === "string" ? config.permission : config.permission && typeof config.permission === "object" ? (config.permission as { "*"?: string })["*"] : undefined;
        if (importedPermission === "ask" || importedPermission === "allow" || importedPermission === "deny") {
          setPermissionMode(importedPermission);
          localStorage.setItem("kspr_permission_mode", importedPermission);
        }
        const agents = config.agent as Record<string, { prompt?: string }> | undefined;
        const importedPrompt = typeof config.prompt === "string" ? config.prompt : agents?.["kspr-i"]?.prompt;
        if (importedPrompt) { setPersonalityMd(importedPrompt); localStorage.setItem("kspr_main_prompt", importedPrompt); }
        if (agents && typeof agents === "object") {
          const importedAgents = Object.entries(agents).filter(([key, agent]) => !["kspr-i", "kspr-i-plan", "kspr-i-review"].includes(key) && agent?.prompt).map(([key, agent]) => ({ id: key, description: (agent as { description?: string }).description || "Agente importado", prompt: agent.prompt || "", mode: ((agent as { mode?: string }).mode === "subagent" ? "subagent" : "primary") as AgentProfile["mode"], model: (agent as { model?: string }).model, permission: ((agent as { permission?: PermissionMode }).permission || "ask") as PermissionMode }));
          if (importedAgents.length) setCustomAgents(importedAgents);
        }
        const mcp = config.mcp as { endpoint?: string; [name: string]: unknown } | undefined;
        const namedMcp = mcp && Object.values(mcp).find((value) => value && typeof value === "object" && "url" in value) as { url?: string } | undefined;
        const importedMcp = mcp?.endpoint || namedMcp?.url;
        if (importedMcp) { setMcpConfig(importedMcp); localStorage.setItem("kspr_mcp_config", importedMcp); }
        if (mcp && typeof mcp === "object") {
          const importedServers = Object.fromEntries(Object.entries(mcp).filter(([key, value]) => key !== "endpoint" && value && typeof value === "object")) as Record<string, McpServerConfig>;
          if (Object.keys(importedServers).length) setMcpServers(importedServers);
        }
        const importedTheme = config.theme;
        if (importedTheme === "light" || importedTheme === "dark") setTheme(importedTheme);
        const commandConfig = config.command as Record<string, { description?: string; template?: string }> | undefined;
        if (commandConfig) {
          const lines = Object.entries(commandConfig).map(([name, command]) => `/${name} — ${command.description || "Comando KSPR"}${command.template ? ` :: ${command.template}` : ""}`);
          setCustomCommands(lines.join("\n"));
          localStorage.setItem("kspr_custom_commands", lines.join("\n"));
        }
        setError("");
      } catch {
        setError("El archivo de configuración no es un JSON válido.");
      }
    });
    event.target.value = "";
  }

  function appendDraft(text: string) {
    setDraft((current) => [current.trim(), text.trim()].filter(Boolean).join(current.trim() ? "\n" : ""));
  }

  function undoLastTurn() {
    const lastUserIndex = [...messages].map((message) => message.role).lastIndexOf("user");
    if (lastUserIndex < 0) return;
    setUndoneMessages(messages.slice(lastUserIndex));
    setMessages(messages.slice(0, lastUserIndex));
  }

  function redoLastTurn() {
    if (!undoneMessages.length) return;
    setMessages((current) => [...current, ...undoneMessages]);
    setUndoneMessages([]);
  }

  function createSession() {
    const session = newSession();
    setSessions((current) => [session, ...current]);
    setActiveSessionId(session.id);
    setMessages([]);
    setFiles([]);
    setContextFiles([]);
    setDraft("");
    setResult(null);
    setError("");
    setSidebarOpen(true);
  }

  function selectSession(session: SessionRecord) {
    setActiveSessionId(session.id);
    setMessages(session.messages || []);
    setFiles([]);
    setContextFiles(session.contextFiles || []);
    setDraft("");
    setResult(null);
    setError("");
    if (session.model) {
      setProviderId(session.model.providerId);
      setModelId(session.model.modelId);
    }
    setModelVariant(session.variant || "default");
    setPermissionMode(session.permissionMode || "ask");
    localStorage.setItem("kspr_permission_mode", session.permissionMode || "ask");
    if (session.agent) {
      setAgentMode(session.agent);
      localStorage.setItem("kspr_agent_mode", session.agent);
    }
    setSidebarOpen(window.innerWidth > 820);
  }

  function deleteSession(sessionId: string) {
    const remaining = sessions.filter((session) => session.id !== sessionId);
    const next = remaining.length ? remaining : [newSession()];
    setSessions(next);
    if (sessionId === activeSessionId) {
      setActiveSessionId(next[0].id);
      setMessages(next[0].messages || []);
      setContextFiles(next[0].contextFiles || []);
    }
  }

  async function ingestSelectedFiles(selected: File[]) {
    if (!selected.length) return;
    try {
      const archives = selected.filter((file) => file.name.toLowerCase().endsWith(".zip"));
      const regular = selected.filter((file) => !file.name.toLowerCase().endsWith(".zip"));
      const unpacked = (await Promise.all(archives.map((file) => ingestArchive(file)))).flat();
      const loaded = [...unpacked, ...(await Promise.all(regular.map(async (file) => ({ path: file.name, content: await file.text() }))))];
      if (loaded.length) {
        setFiles((current) => [...current.filter((item) => !loaded.some((newFile) => newFile.path === item.path)), ...loaded]);
        setContextFiles((current) => [...current.filter((item) => !loaded.some((newFile) => newFile.path === item.path)), ...loaded]);
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No se pudieron cargar los archivos");
    }
  }

  async function addFiles(event: ChangeEvent<HTMLInputElement>) {
    await ingestSelectedFiles(Array.from(event.target.files || []));
    event.target.value = "";
  }

  useEffect(() => {
    const onPaste = (event: globalThis.ClipboardEvent) => {
      const pastedFiles = Array.from(event.clipboardData?.files || []);
      if (!pastedFiles.length) return;
      event.preventDefault();
      void ingestSelectedFiles(pastedFiles);
    };
    const onDragOver = (event: globalThis.DragEvent) => {
      if (!event.dataTransfer?.files.length) return;
      event.preventDefault();
      setDraggingFiles(true);
    };
    const onDrop = (event: globalThis.DragEvent) => {
      if (!event.dataTransfer?.files.length) return;
      event.preventDefault();
      setDraggingFiles(false);
      void ingestSelectedFiles(Array.from(event.dataTransfer.files));
    };
    window.addEventListener("paste", onPaste);
    window.addEventListener("dragover", onDragOver);
    window.addEventListener("drop", onDrop);
    return () => {
      window.removeEventListener("paste", onPaste);
      window.removeEventListener("dragover", onDragOver);
      window.removeEventListener("drop", onDrop);
    };
  }, []);

  function removeFile(path: string) {
    setFiles((current) => current.filter((file) => file.path !== path));
    setContextFiles((current) => current.filter((file) => file.path !== path));
  }

  async function startRecording() {
    setError("");
    if (recording) {
      recognitionRef.current?.stop();
      recorderRef.current?.stop();
      return;
    }
    const Recognition = getSpeechRecognition();
    if (Recognition) {
      const recognition = new Recognition();
      recognition.lang = "es-CO";
      recognition.continuous = true;
      recognition.interimResults = false;
      recognition.onresult = (event) => {
        const transcript = event.results.slice(event.resultIndex).filter((item) => item.isFinal).map((item) => item[0].transcript).join(" ");
        if (transcript) appendDraft(transcript);
      };
      recognition.onerror = () => {
        setRecording(false);
        setError("No se pudo reconocer el audio. Revisa el permiso del micrófono.");
      };
      recognition.onend = () => {
        recognitionRef.current = null;
        setRecording(false);
      };
      recognitionRef.current = recognition;
      recognition.start();
      setRecording(true);
      return;
    }
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      setError("Este navegador no soporta grabación o reconocimiento de voz.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      audioChunksRef.current = [];
      recorder.ondataavailable = (event) => event.data.size && audioChunksRef.current.push(event.data);
      recorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        setRecording(false);
        try {
          appendDraft(await transcribeAudio(new Blob(audioChunksRef.current, { type: recorder.mimeType }), authFor("gemini")));
        } catch (cause) {
          setError(cause instanceof Error ? cause.message : "No se pudo transcribir el audio");
        }
      };
      recorderRef.current = recorder;
      recorder.start();
      setRecording(true);
    } catch {
      setError("No se pudo acceder al micrófono.");
    }
  }

  function executeCommand(commandId: string) {
    setCommandPaletteOpen(false);
    setCommandQuery("");
    if (commandId.startsWith("custom:")) {
      const command = allCommands.find((item) => item.id === commandId);
      if (command) setDraft(expandCommandTemplate(command, ""));
      return;
    }
    switch (commandId) {
      case "new": createSession(); break;
      case "sessions": setSidebarOpen(true); break;
      case "models": setApiHubOpen(true); break;
      case "provider": setApiHubOpen(true); break;
      case "config": setConfigModalOpen(true); break;
      case "agents": setAgentModalOpen(true); break;
      case "mcp": setMcpModalOpen(true); break;
      case "permissions": setConfigModalOpen(true); break;
      case "export": exportSession(activeSession); break;
      case "share": void shareSession(activeSession); break;
      case "editor": composerRef.current?.focus(); break;
      case "init": setConfigModalOpen(true); break;
      case "compact": setMessages((current) => [...current, { id: id("message"), role: "assistant", content: "Sesión compactada. KSPR conservará el contexto estructural y las decisiones relevantes.", meta: selectedModel.name, createdAt: Date.now() }]); break;
      case "thinking": setShowReviews((current) => !current); break;
      case "details": setShowReviews(true); break;
      case "context": setContextModalOpen(true); break;
      case "undo": undoLastTurn(); break;
      case "redo": redoLastTurn(); break;
      case "themes": setConfigModalOpen(true); break;
      case "help": setHelpModalOpen(true); break;
      default: break;
    }
  }

  function handleCommandPaletteKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setCommandIndex((current) => Math.min(current + 1, Math.max(filteredCommands.length - 1, 0)));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setCommandIndex((current) => Math.max(current - 1, 0));
    } else if (event.key === "Enter" && filteredCommands[commandIndex]) {
      event.preventDefault();
      executeCommand(filteredCommands[commandIndex].id);
    }
  }

  function parseSlashCommand(text: string) {
    const match = text.match(/^\/([^\s]+)(?:\s+(.*))?$/);
    if (!match) return false;
    const aliases: Record<string, string> = { connect: "provider", provider: "provider", clear: "new", resume: "sessions", continue: "sessions", mo: "models", summarize: "compact" };
    const command = aliases[match[1]] || match[1];
    const custom = allCommands.find((item) => item.slash === `/${match[1]}`);
    if (!COMMANDS.some((item) => item.id === command) && !custom) return false;
    if (custom) {
      return expandCommandTemplate(custom, match[2] || "");
    }
    executeCommand(command);
    setDraft("");
    return true;
  }

  async function sendMessage(event?: FormEvent) {
    event?.preventDefault();
    let text = draft.trim();
    const slashResult = parseSlashCommand(text);
    if (slashResult === true) return;
    if (typeof slashResult === "string") text = slashResult;
    if ((!text && !files.length) || running || !selectedModel) return;
    setError("");
    setRunning(true);
    setRunProgress(0);
    setRunStage("Preparando contexto");
    setLiveResponse("");
    const abortController = new AbortController();
    abortControllerRef.current = abortController;
    const attachedFiles = files;
    const sourceFiles = [...attachedFiles];
    if (text) sourceFiles.push({ path: "chat-request.md", content: text });
    const userMessage: ChatMessage = { id: id("message"), role: "user", content: text || "Analiza los archivos adjuntos y recupera su funcionalidad.", files: attachedFiles.map((file) => file.path), createdAt: Date.now() };
    setMessages((current) => [...current, userMessage]);
    setDraft("");
    setFiles([]);
    const conversationContext = messages.slice(-12).map((message) => `${message.role === "user" ? "USUARIO" : "KSPR I"}: ${message.content}`).join("\n\n");
    const instruction = [
      "MAIN PROMPT DE KSPR I:", personalityMd,
      promptForActiveAgent() ? "\nPROMPT DEL AGENTE ACTIVO:\n" + promptForActiveAgent() : "",
      "", `AGENTE ACTIVO: ${agentMode}`, `MODO DE PERMISOS: ${permissionMode}`, `MODELO: ${providerId}/${modelId}`, `VARIANTE: ${modelVariant}`, `MCP CONTEXT ENDPOINT: ${mcpConfig}`,
      conversationContext ? "\nHISTORIAL RECIENTE DE LA SESIÓN:\n" + conversationContext : "",
      "", "MENSAJE DEL USUARIO:", text || "Analiza los archivos adjuntos y recupera su funcionalidad.",
    ].join("\n");
    try {
      const analysis = await runAnalysis({
        project_name: "KSPR workspace",
        files: sourceFiles,
        provider: selectedModel.providerId,
        model: selectedModel.id,
        variant: modelVariant,
        effort: modelEffort,
        instruction,
        iterations: 3,
        mode: "auto",
      }, authFor(selectedModel.providerId), abortController.signal, (progress) => {
        setRunProgress(progress.progress);
        setRunStage(progress.message || progress.stage);
      }, (delta) => setLiveResponse((current) => current + delta));
      setResult(analysis);
      setMessages((current) => [...current, { id: id("message"), role: "assistant", meta: `${selectedModel.providerName} · ${selectedModel.name}`, content: analysis.response_text || "El modelo terminó el análisis, pero no devolvió texto visible.", createdAt: Date.now() }]);
    } catch (cause) {
      if (cause instanceof DOMException && cause.name === "AbortError") {
        setError("Ejecución detenida.");
      } else {
        setError(cause instanceof Error ? cause.message : "KSPR no pudo completar el análisis");
      }
    } finally {
      abortControllerRef.current = null;
      setRunning(false);
    }
  }

  function handleComposerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void sendMessage();
    }
  }

  async function connectSelectedProvider() {
    setProviderStatus("Consultando modelos disponibles...");
    setProviderConnected(false);
    const providerKey = connectProvider === "custom" ? customProviderId.trim() : connectProvider;
    if (!providerKey) { setProviderStatus("Indica un identificador para el proveedor."); return; }
    const auth: ProviderAuth = { provider: providerKey, apiKey: connectKey, baseUrl: connectProvider === "gemini" ? undefined : connectBaseUrl, authMode: connectProvider === "gemini" ? geminiAuthMode : undefined };
    try {
      const status = await checkProviderStatus(auth);
      if (!status.connected) throw new Error(status.message);
      const providerName = connectProvider === "gemini" ? "Google Gemini" : connectProvider === "openai-compatible" ? "OpenAI-compatible" : customProviderName.trim() || providerKey;
      const loaded = status.models.map((model) => ({ ...model, providerId: providerKey, providerName }));
      setModels((current) => [...current.filter((model) => model.providerId !== providerKey), ...(loaded.length ? loaded : current.filter((model) => model.providerId === providerKey))]);
      if (connectProvider === "gemini") { setGeminiApiKey(connectKey); setGeminiAuthMode(geminiAuthMode); }
      else { setCompatibleApiKey(connectKey); setCompatibleBaseUrl(connectBaseUrl); }
      setProviderConfigs((current) => ({ ...current, [providerKey]: auth }));
      if (loaded.length) selectModel(loaded[0]);
      setProviderConnected(true);
      setProviderStatus(`${status.models.length} modelos disponibles`);
    } catch (cause) {
      setProviderStatus(cause instanceof Error ? cause.message : "No se pudo conectar con el proveedor");
    }
  }

  function chooseFileReference(path: string) {
    const at = draft.lastIndexOf("@");
    setDraft(`${draft.slice(0, at)}@${path} `);
  }

  function stopRunning() {
    abortControllerRef.current?.abort();
  }

  async function copyMessage(message: ChatMessage) {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopiedMessageId(message.id);
      window.setTimeout(() => setCopiedMessageId((current) => current === message.id ? null : current), 1400);
    } catch {
      setError("No se pudo copiar el mensaje al portapapeles.");
    }
  }

  async function shareSession(session: SessionRecord | undefined) {
    if (!session) return;
    try {
      await navigator.clipboard.writeText(sessionMarkdown(session));
      setError("Transcripción copiada: ya puedes compartirla con otro agente.");
    } catch {
      setError("No se pudo copiar la transcripción de la sesión.");
    }
  }

  return (
    <div className={`app-shell app-shell-v2 ${sidebarOpen ? "sidebar-is-open" : "sidebar-is-closed"}`}>
      <aside className="session-sidebar">
        <div className="sidebar-brand"><img src="/casper-ai-logo.png" alt="KSPR AI" /><div><strong>KSPR AI</strong><span>Empresarial</span></div><button className="sidebar-icon" onClick={() => setSidebarOpen(false)} aria-label="Cerrar barra lateral"><Menu size={16} /></button></div>
        <button className="sidebar-new-session" onClick={createSession}><Plus size={15} /> Nueva sesión <span>⌘⇧S</span></button>
        <label className="session-search"><Search size={14} /><input value={sessionSearch} onChange={(event) => setSessionSearch(event.target.value)} placeholder="Buscar sesiones" /></label>
        <div className="workspace-label"><span>WORKSPACE</span><strong>kspr / empresarial</strong></div>
        <div className="session-list"><span className="session-group-label">Recientes</span>{filteredSessions.map((session) => <div className={session.id === activeSessionId ? "session-row active" : "session-row"} key={session.id}><button onClick={() => selectSession(session)}><span>{session.title}</span><small>{session.messages.length ? `${session.messages.length} mensajes` : "vacía"}</small></button>{session.id === activeSessionId && <button className="session-delete" onClick={() => deleteSession(session.id)} aria-label="Eliminar sesión"><X size={12} /></button>}</div>)}{!filteredSessions.length && <div className="session-empty">No hay sesiones que coincidan.</div>}</div>
        <div className="sidebar-bottom"><button onClick={() => setApiHubOpen(true)}><Sparkles size={15} /><span>APIs y Modelos</span><i className={providerConnected ? "connected-dot" : ""} /></button><button onClick={() => setConfigModalOpen(true)}><Settings2 size={15} /><span>Configuración</span><kbd>⌘,</kbd></button><div className="sidebar-agent"><img src="/casper-ai-logo.png" alt="" /><span><strong>{agentMode}</strong><small>Agente activo</small></span><ChevronDown size={13} /></div></div>
      </aside>
      {sidebarOpen && <button className="mobile-sidebar-overlay" onClick={() => setSidebarOpen(false)} aria-label="Cerrar barra lateral" />}

      <div className="app-main">
        <header className="topbar workspace-topbar"><div className="workspace-title"><button className="mobile-menu" onClick={() => setSidebarOpen((open) => !open)} aria-label="Abrir barra lateral"><Menu size={17} /></button>{!sidebarOpen && <img className="brand-logo" src="/casper-ai-logo.png" alt="KSPR AI" />}<div><strong>{activeSession?.title || "Nueva sesión"}</strong><span>kspr / empresarial</span></div></div><div className="workspace-actions"><button className="command-trigger" onClick={() => { setCommandPaletteOpen(true); setCommandQuery(""); }}><Command size={14} /> Buscar comandos <kbd>⌘K</kbd></button><button className="top-icon-button" onClick={() => setHelpModalOpen(true)} aria-label="Ayuda"><HelpCircle size={16} /></button><button className="top-icon-button" onClick={() => setConfigModalOpen(true)} aria-label="Configuración"><Settings2 size={16} /></button></div></header>

        <main className="chat-page workspace-chat-page"><section className={hasConversation ? "chat-shell has-conversation" : "chat-shell"}><div className="conversation">
          {!hasConversation && <div className="welcome"><img src="/casper-ai-nombre-imagen-fondotransparente.png" alt="KSPR AI" style={{ maxWidth: '280px', height: 'auto', display: 'block', margin: '0 auto 22px' }} /><span className="eyebrow">KSPR AI · KSPR I ENGINE</span><h1>¿Qué quieres <em>entender?</em></h1><p>Escribe una instrucción, referencia archivos con <code>@</code> o usa <code>/</code> para comandos. KSPR I estudia la evidencia y devuelve una respuesta técnica accionable.</p><div className="starter-prompts">{starterPrompts.map((prompt) => <button key={prompt} onClick={() => setDraft(prompt)}>{prompt}<span>↗</span></button>)}</div></div>}
          {messages.map((message) => <article className={message.role === "user" ? "chat-message user-message" : "chat-message assistant-message"} key={message.id}>{message.role === "assistant" && <div className="message-avatar"><img src="/casper-ai-logo.png" alt="KSPR AI" /></div>}<div className="message-body">{message.role === "assistant" && <div className="message-meta"><strong>KSPR I</strong><span>{message.meta}</span></div>}<div className="message-content">{message.role === "assistant" ? <MessageContent content={message.content} /> : message.content}</div>{message.files && message.files.length > 0 && <div className="message-files">{message.files.map((file) => <span key={file}><FileText size={13} />{file}</span>)}</div>}{message.role === "assistant" && <div className="message-actions"><button type="button" onClick={() => void copyMessage(message)}>{copiedMessageId === message.id ? <Check size={12} /> : <FileText size={12} />}{copiedMessageId === message.id ? "Copiado" : "Copiar"}</button></div>}</div></article>)}
          {running && <article className="chat-message assistant-message"><div className="message-avatar"><img src="/casper-ai-logo.png" alt="KSPR AI" /></div><div className="message-body loading-message"><div className="message-meta"><strong>KSPR I</strong><span>{selectedModel?.name} · {runProgress}%</span></div>{liveResponse && <div className="streaming-preview"><MessageContent content={liveResponse} /></div>}<span><LoaderCircle size={15} className="spin" /> {runStage}...</span></div></article>}
          {result && !running && showReviews && <details className="package-drawer" open><summary><Sparkles size={15} /> Paquete de contexto generado <span>{result.artifacts.length} Markdown/JSON</span></summary><ArtifactPanel artifacts={result.artifacts} /></details>}
        </div>

          {contextFiles.length > 0 && <button type="button" className="context-launcher" onClick={() => setContextModalOpen(true)}><FileText size={13} /> Ver contexto adjunto <span>{contextFiles.length}</span></button>}
          {draggingFiles && <div className="drop-hint"><Paperclip size={13} /> Suelta los archivos para adjuntarlos a KSPR I</div>}
          <label className="permission-control"><span>PERMISOS</span><select value={permissionMode} onChange={(event) => { const next = event.target.value as PermissionMode; setPermissionMode(next); localStorage.setItem("kspr_permission_mode", next); }}><option value="ask">Preguntar antes de actuar</option><option value="allow">Permitir acciones</option><option value="deny">Solo lectura</option></select></label>
          {selectedModel?.variants && selectedModel.variants.length > 1 && <label className="variant-control"><span>VARIANTE</span><select value={modelVariant} onChange={(event) => setModelVariant(event.target.value)}>{selectedModel.variants.map((variant) => <option key={variant}>{variant}</option>)}</select></label>}
          {running && <button type="button" className="stop-response-button" onClick={stopRunning}><Square size={13} fill="currentColor" /> Detener respuesta <kbd>Ctrl+G</kbd></button>}
          <form className="composer-wrap opencode-composer" onSubmit={sendMessage}>{files.length > 0 && <div className="attachment-list">{files.map((file) => <span className="attachment-chip" key={file.path}><FileText size={13} />{file.path}<button type="button" onClick={() => removeFile(file.path)} aria-label={`Quitar ${file.path}`}><X size={12} /></button></span>)}</div>}{showSlashMenu && <div className="composer-popover slash-popover">{allCommands.filter((command) => command.slash.startsWith(draft)).slice(0, 6).map((command) => <button type="button" key={command.id} onClick={() => setDraft(`${command.slash} `)}><span><Command size={13} />{command.slash}</span><small>{command.description}</small></button>)}</div>}{showFileMenu && <div className="composer-popover file-popover">{filteredFiles.map((file) => <button type="button" key={file.path} onClick={() => chooseFileReference(file.path)}><FileText size={13} />@{file.path}</button>)}</div>}<textarea ref={composerRef} value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={handleComposerKeyDown} placeholder="Pregunta a KSPR I..." rows={3} spellCheck /><div className="composer-tools"><div className="composer-left"><label className="tool-button" title="Adjuntar archivos"><Paperclip size={17} /><input type="file" multiple accept=".zip,.py,.js,.jsx,.ts,.tsx,.cs,.java,.sql,.html,.vue,.php,.md,.txt,.json,.yaml,.yml" onChange={addFiles} /></label><button type="button" className={recording ? "tool-button recording" : "tool-button"} onClick={() => void startRecording()} title={recording ? "Detener grabación" : "Grabar y transcribir audio"}>{recording ? <Square size={15} fill="currentColor" /> : <Mic size={17} />}</button><button type="button" className="composer-select" onClick={() => setApiHubOpen(true)}><span>{selectedModel?.providerName} / <strong>{selectedModel?.name}</strong></span><ChevronDown size={14} /></button><span className="agent-pill"><Sparkles size={12} /> {agentMode}</span></div><button className="send-button" type="submit" disabled={running || (!draft.trim() && !files.length)} aria-label="Enviar mensaje">{running ? <LoaderCircle size={17} className="spin" /> : <ArrowUp size={18} />}</button></div>{error && <div className="composer-error">{error}</div>}</form><div className="chat-disclaimer">KSPR I puede equivocarse. Verifica evidencias antes de modificar producción · <button onClick={() => setCommandPaletteOpen(true)}>⌘K para comandos</button></div></section></main>
        <footer><span>KSPR / OBSERVABILITY FOR LEGACY SYSTEMS</span><span><Terminal size={11} /> Secure static analysis · No code execution</span></footer>
      </div>

      {commandPaletteOpen && <div className="modal-overlay command-overlay" onClick={() => setCommandPaletteOpen(false)}><div className="command-palette" onClick={(event) => event.stopPropagation()}><div className="command-search"><Search size={16} /><input autoFocus value={commandQuery} onChange={(event) => { setCommandQuery(event.target.value); setCommandIndex(0); }} onKeyDown={handleCommandPaletteKeyDown} placeholder="Buscar comandos..." /></div><div className="command-list">{filteredCommands.map((command, index) => <button className={index === commandIndex ? "command-highlighted" : ""} key={command.id} onClick={() => executeCommand(command.id)}><span className="command-icon"><Command size={14} /></span><span><strong>{command.title}</strong><small>{command.description}</small></span><em>{command.shortcut || command.slash}</em></button>)}{!filteredCommands.length && <div className="command-empty">No hay comandos que coincidan.</div>}</div><div className="command-footer"><span>↑↓ navegar</span><span>↵ ejecutar</span><span>esc cerrar</span></div></div></div>}
            {apiHubOpen && (
        <div className="modal-overlay" onClick={() => setApiHubOpen(false)}>
          <div className="modal-box model-modal api-hub-modal" onClick={(event) => event.stopPropagation()}>
            <div className="modal-header">
              <h2><Sparkles size={18} /> Conexión de APIs y Modelos</h2>
              <button className="modal-close" onClick={() => setApiHubOpen(false)}><X size={18} /></button>
            </div>
            <p className="modal-help-inline" style={{ marginBottom: "14px" }}>Único sitio para agregar APIs, seleccionar proveedor y elegir tu modelo activo.</p>

            <div className="api-hub-section" style={{ marginBottom: "16px" }}>
              <strong style={{ display: "block", fontSize: "11px", fontWeight: "600", marginBottom: "8px", color: "var(--ink)" }}>1. Proveedor y Credenciales API</strong>
              <div className="provider-cards">
                <button className={connectProvider === "gemini" ? "provider-card active" : "provider-card"} onClick={() => setConnectProvider("gemini")}>
                  <Sparkles size={17} />
                  <span><strong>Google Gemini</strong><small>Gemini API</small></span>
                  {connectProvider === "gemini" && <Check size={14} />}
                </button>
                <button className={connectProvider === "openai-compatible" ? "provider-card active" : "provider-card"} onClick={() => setConnectProvider("openai-compatible")}>
                  <Terminal size={17} />
                  <span><strong>OpenAI-compatible</strong><small>OpenRouter, Groq, etc.</small></span>
                  {connectProvider === "openai-compatible" && <Check size={14} />}
                </button>
                <button className={connectProvider === "custom" ? "provider-card active" : "provider-card"} onClick={() => setConnectProvider("custom")}>
                  <Command size={17} />
                  <span><strong>Personalizado</strong><small>/chat/completions</small></span>
                  {connectProvider === "custom" && <Check size={14} />}
                </button>
              </div>
              {connectProvider === "custom" && (
                <div className="config-grid">
                  <div className="modal-field"><label>Provider ID</label><input value={customProviderId} onChange={(event) => setCustomProviderId(event.target.value.replace(/[^a-zA-Z0-9._-]/g, "-"))} placeholder="mi-proveedor" /></div>
                  <div className="modal-field"><label>Nombre visible</label><input value={customProviderName} onChange={(event) => setCustomProviderName(event.target.value)} placeholder="Mi proveedor" /></div>
                </div>
              )}
              <div className="modal-field">
                <label>{connectProvider === "gemini" ? "Google Gemini API Key" : "API Key / Token Bearer"}</label>
                <input type="password" value={connectKey} onChange={(event) => setConnectKey(event.target.value)} placeholder={connectProvider === "gemini" ? "AIzaSy..." : "sk-..."} />
              </div>
              {connectProvider !== "gemini" && (
                <div className="modal-field">
                  <label>Base URL del endpoint</label>
                  <input value={connectBaseUrl} onChange={(event) => setConnectBaseUrl(event.target.value)} placeholder="https://api.openai.com/v1" />
                </div>
              )}
              <button type="button" className="modal-button primary full-button" onClick={() => void connectSelectedProvider()} style={{ marginTop: "4px" }}>Conectar y Listar Modelos</button>
              {providerStatus && <div className={providerConnected ? "provider-status connected" : "provider-status"}>{providerStatus}</div>}
            </div>

            <div className="api-hub-section" style={{ borderTop: "1px solid var(--line)", paddingTop: "14px" }}>
              <strong style={{ display: "block", fontSize: "11px", fontWeight: "600", marginBottom: "8px", color: "var(--ink)" }}>2. Seleccionar Modelo Activo</strong>
              <div className="modal-search" style={{ margin: "6px 0" }}>
                <Search size={14} />
                <input value={modelSearch} onChange={(event) => setModelSearch(event.target.value)} placeholder="Filtrar modelos disponibles..." />
              </div>
              <div className="model-list" style={{ maxHeight: "200px", margin: "6px 0" }}>
                {filteredModels.map((model) => (
                  <button className={model.id === selectedModel?.id && model.providerId === providerId ? "model-option selected" : "model-option"} key={`${model.providerId}:${model.id}`} onClick={() => selectModel(model)}>
                    <span className="model-mark"><Sparkles size={14} /></span>
                    <span><strong>{model.name}</strong><small>{model.providerName} · {model.description}</small></span>
                    {model.custom && <em className="custom-model-tag">custom</em>}
                    {model.id === selectedModel?.id && model.providerId === providerId && <Check size={15} />}
                  </button>
                ))}
                {!filteredModels.length && <div className="command-empty">No hay modelos. Conecta un proveedor arriba o añade un modelo manual.</div>}
              </div>

              {!customModelOpen ? (
                <button type="button" className="modal-button" style={{ width: "100%", marginTop: "6px" }} onClick={() => setCustomModelOpen(true)}>+ Añadir modelo manual</button>
              ) : (
                <div className="custom-model-form">
                  <div className="config-grid">
                    <div className="modal-field"><label>Proveedor</label><select value={customModelProvider} onChange={(event) => setCustomModelProvider(event.target.value)}><option value="openai-compatible">OpenAI-compatible</option><option value="gemini">Google Gemini</option><option value="local">KSPR Local</option></select></div>
                    <div className="modal-field"><label>ID del modelo</label><input value={customModelId} onChange={(event) => setCustomModelId(event.target.value)} placeholder="gpt-4o / gemini-2.5-pro" /></div>
                  </div>
                  <div className="modal-field"><label>Nombre visible</label><input value={customModelName} onChange={(event) => setCustomModelName(event.target.value)} placeholder="Mi modelo personalizado" /></div>
                  <div style={{ display: "flex", gap: "8px" }}>
                    <button type="button" className="modal-button primary" onClick={addCustomModel}>Guardar y Seleccionar</button>
                    <button type="button" className="modal-button" onClick={() => setCustomModelOpen(false)}>Cancelar</button>
                  </div>
                </div>
              )}
            </div>

            <div className="api-hub-section" style={{ borderTop: "1px solid var(--line)", paddingTop: "14px" }}>
              <strong style={{ display: "block", fontSize: "11px", fontWeight: "600", marginBottom: "8px", color: "var(--ink)" }}>3. Nivel de Esfuerzo (Model Effort / Razonamiento)</strong>
              <div className="provider-cards" style={{ gridTemplateColumns: "repeat(4, 1fr)" }}>
                <button type="button" className={modelEffort === "low" ? "provider-card active" : "provider-card"} onClick={() => { setModelEffort("low"); localStorage.setItem("kspr_model_effort", "low"); }}>
                  <span><strong>Low</strong><small>Rápido</small></span>
                  {modelEffort === "low" && <Check size={14} />}
                </button>
                <button type="button" className={modelEffort === "medium" ? "provider-card active" : "provider-card"} onClick={() => { setModelEffort("medium"); localStorage.setItem("kspr_model_effort", "medium"); }}>
                  <span><strong>Medium</strong><small>Equilibrado</small></span>
                  {modelEffort === "medium" && <Check size={14} />}
                </button>
                <button type="button" className={modelEffort === "high" ? "provider-card active" : "provider-card"} onClick={() => { setModelEffort("high"); localStorage.setItem("kspr_model_effort", "high"); }}>
                  <span><strong>High</strong><small>Deep thinking</small></span>
                  {modelEffort === "high" && <Check size={14} />}
                </button>
                <button type="button" className={modelEffort === "default" ? "provider-card active" : "provider-card"} onClick={() => { setModelEffort("default"); localStorage.setItem("kspr_model_effort", "default"); }}>
                  <span><strong>Default</strong><small>Estándar</small></span>
                  {modelEffort === "default" && <Check size={14} />}
                </button>
              </div>
            </div>

          </div>
        </div>
      )}

      {configModalOpen && <div className="modal-overlay" onClick={() => setConfigModalOpen(false)}><div className="modal-box config-modal" onClick={(event) => event.stopPropagation()}><div className="modal-header"><h2><Settings2 size={18} /> Configuración de KSPR I</h2><button className="modal-close" onClick={() => setConfigModalOpen(false)}><X size={18} /></button></div><div className="config-grid"><div className="modal-field"><label>Tema de interfaz</label><select value={theme} onChange={(event) => setTheme(event.target.value)}><option value="light">Phantom Light</option><option value="dark">Carbon Dark</option></select></div><div className="modal-field"><label>Agente activo</label><select value={agentMode} onChange={(event) => { setAgentMode(event.target.value); localStorage.setItem("kspr_agent_mode", event.target.value); }}><option>KSPR I</option><option>KSPR I · Plan</option><option>KSPR I · Review</option></select></div></div><div className="modal-field"><label>MCP Context Endpoint</label><input value={mcpConfig} onChange={(event) => { setMcpConfig(event.target.value); localStorage.setItem("kspr_mcp_config", event.target.value); }} placeholder="mcp://local-context-server" /></div><div className="modal-field"><label>Main Prompt de KSPR I (.md)</label><p className="modal-help-inline">Se aplica antes del mensaje en todos los modelos conectados.</p><textarea className="prompt-editor" value={personalityMd} onChange={(event) => { setPersonalityMd(event.target.value); localStorage.setItem("kspr_main_prompt", event.target.value); }} /></div><div className="modal-field"><label>Comandos personalizados</label><p className="modal-help-inline">Un comando por línea: <code>/nombre — descripción</code>.</p><textarea className="command-editor" value={customCommands} onChange={(event) => { setCustomCommands(event.target.value); localStorage.setItem("kspr_custom_commands", event.target.value); }} placeholder="/inventario — Genera un inventario UI completo" /></div><div className="config-transfer"><strong>Configuración portable</strong><span>Exporta proveedores, modelos, agente, comandos y Main Prompt sin credenciales.</span><div><button className="modal-button secondary" onClick={exportConfiguration}>Exportar JSON</button><label className="modal-button secondary import-config">Importar JSON<input type="file" accept="application/json,.json" onChange={importConfiguration} /></label></div></div><div className="modal-actions"><button className="modal-button" onClick={() => setConfigModalOpen(false)}>Guardar configuración</button></div></div></div>}
      {helpModalOpen && <div className="modal-overlay" onClick={() => setHelpModalOpen(false)}><div className="modal-box help-modal" onClick={(event) => event.stopPropagation()}><div className="modal-header"><h2><HelpCircle size={18} /> Comandos de KSPR I</h2><button className="modal-close" onClick={() => setHelpModalOpen(false)}><X size={18} /></button></div><div className="help-list">{allCommands.map((command) => <div key={command.id}><code>{command.slash}</code><span><strong>{command.title}</strong><small>{command.description}</small></span></div>)}</div><p className="modal-help">También puedes usar <code>@archivo</code> para referenciar un archivo adjunto y <code>⌘K</code> / <code>Ctrl+K</code> para abrir la paleta.</p></div></div>}
      {mcpModalOpen && <McpManager servers={mcpServers} onChange={setMcpServers} onClose={() => setMcpModalOpen(false)} />}
      {agentModalOpen && <AgentManager agents={customAgents} activeAgent={agentMode} onChange={setCustomAgents} onSelect={selectAgent} onClose={() => setAgentModalOpen(false)} />}
      {contextModalOpen && <ContextPanel files={contextFiles} selectedPath={selectedContextPath} onSelect={setSelectedContextPath} onRemove={removeFile} permissionMode={permissionMode} onInsert={appendDraft} onClose={() => setContextModalOpen(false)} />}
    </div>
  );
}