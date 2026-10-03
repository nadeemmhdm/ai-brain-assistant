import { BASE, authFetch, j, jAuth } from "./api";

const json = (method: string, body?: any): RequestInit => ({ method, headers: { "Content-Type": "application/json" }, body: body === undefined ? undefined : JSON.stringify(body) });

export const api2 = {
  analyzeFile: async (file: File) => jAuth(await authFetch(`${BASE}/api/files/analyze`, { method: "POST", headers: { "X-Filename": file.name }, body: file })),
  // conversations
  forkConversation: (id: string, message_id: string) => authFetch(`${BASE}/api/conversations/${id}/fork`, json("POST", { message_id })).then(jAuth),
  searchConversations: (q: string) => authFetch(`${BASE}/api/conversations?q=${encodeURIComponent(q)}`).then(j<any[]>),
  setActionStatus: (mid: string, status: string, note?: string, content?: string) =>
    authFetch(`${BASE}/api/messages/${mid}/action`, json("PATCH", { status, note, content })),

  // memory
  listMemories: () => authFetch(`${BASE}/api/memory`).then(j<any[]>),
  addMemory: (content: string) => authFetch(`${BASE}/api/memory`, json("POST", { content })).then(jAuth),
  deleteMemory: (id: string) => authFetch(`${BASE}/api/memory/${id}`, { method: "DELETE" }),

  // brain: teach / import / watch
  teach: (topic: string, question: string, answer: string) => authFetch(`${BASE}/api/brain/teach`, json("POST", { topic, question, answer })).then(jAuth),
  importText: (topic: string, title: string, text: string) => authFetch(`${BASE}/api/brain/import`, json("POST", { topic, title, text })).then(jAuth),
  watchList: () => authFetch(`${BASE}/api/brain/watch`).then(j<any[]>),
  watchAdd: (topic: string, interval_hours: number) => authFetch(`${BASE}/api/brain/watch`, json("POST", { topic, interval_hours })).then(jAuth),
  watchToggle: (id: string, enabled: boolean) => authFetch(`${BASE}/api/brain/watch/${id}`, json("PATCH", { enabled })),
  watchRemove: (id: string) => authFetch(`${BASE}/api/brain/watch/${id}`, { method: "DELETE" }),

  // models
  modelStatus: () => authFetch(`${BASE}/api/model/status`).then(j<any>),
  localModels: () => authFetch(`${BASE}/api/model/local`).then(j<any>),
  loadModel: (role: string, filename: string) => authFetch(`${BASE}/api/model/load`, json("POST", { role, filename })).then(jAuth),
  assignModel: (role: string, filename: string) => authFetch(`${BASE}/api/model/assign`, json("POST", { role, filename })).then(jAuth),
  unloadModel: (role: string) => authFetch(`${BASE}/api/model/unload`, json("POST", { role, filename: "" })).then(jAuth),
  importModel: (path: string, mode: "link" | "copy") => authFetch(`${BASE}/api/model/import`, json("POST", { path, mode })).then(jAuth),
  uploadModel: async (file: File) => {
    const res = await authFetch(`${BASE}/api/model/import/upload`, { method: "POST", headers: { "X-Model-Filename": file.name }, body: file });
    return jAuth(res);
  },
  removeImport: (filename: string) => authFetch(`${BASE}/api/model/import/remove`, json("POST", { filename })),
  hfSearch: (q: string) => authFetch(`${BASE}/api/model/hf/search?q=${encodeURIComponent(q)}`).then(jAuth),
  hfFiles: (repo: string) => authFetch(`${BASE}/api/model/hf/files?repo=${encodeURIComponent(repo)}`).then(jAuth),
  hfDownload: (repo: string, filename: string) => authFetch(`${BASE}/api/model/hf/download`, json("POST", { repo, filename })).then(jAuth),
  downloads: (kind?: string) => authFetch(`${BASE}/api/model/downloads${kind ? `?kind=${kind}` : ""}`).then(j<any[]>),
  cancelDownload: (id: string) => authFetch(`${BASE}/api/model/downloads/${id}/cancel`, { method: "POST" }),
  hfTokenStatus: () => authFetch(`${BASE}/api/model/hf/token`).then(j<{ set: boolean }>),
  hfTokenSet: (token: string) => authFetch(`${BASE}/api/model/hf/token`, json("POST", { token })).then(jAuth),
  hfTokenClear: () => authFetch(`${BASE}/api/model/hf/token`, { method: "DELETE" }),

  // voice
  voiceStatus: () => authFetch(`${BASE}/api/voice/status`).then(j<any>),
  voiceSetup: () => authFetch(`${BASE}/api/voice/setup`, { method: "POST" }).then(jAuth),
  voiceSetupStatus: () => authFetch(`${BASE}/api/voice/setup/status`).then(j<any>),
  voiceCatalog: () => authFetch(`${BASE}/api/voice/catalog`).then(j<any[]>),
  installStt: (size: string) => authFetch(`${BASE}/api/voice/stt/install`, json("POST", { size })).then(jAuth),
  installVoice: (voice_id: string) => authFetch(`${BASE}/api/voice/tts/install`, json("POST", { voice_id })).then(jAuth),
  stt: async (blob: Blob): Promise<string> => {
    const res = await authFetch(`${BASE}/api/voice/stt`, { method: "POST", body: blob });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(body.detail || "Transcription failed");
    return body.text as string;
  },
  tts: async (text: string, voice?: string): Promise<Blob> => {
    const res = await authFetch(`${BASE}/api/voice/tts`, json("POST", { text, voice }));
    if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || "Speech failed");
    return res.blob();
  },

  // google
  googleStatus: () => authFetch(`${BASE}/api/google/status`).then(j<any>),
  googleConnect: () => authFetch(`${BASE}/api/google/connect`).then(jAuth),
  googleDisconnect: () => authFetch(`${BASE}/api/google/disconnect`, { method: "POST" }),
  googleExecute: (action: string, params: any, grant: "once" | "chat" | "always" | "standing", conversation_id?: string | null) =>
    authFetch(`${BASE}/api/google/execute`, json("POST", { action, params, grant, conversation_id })).then(jAuth),
  googlePermissions: () => authFetch(`${BASE}/api/google/permissions`).then(j<any[]>),
  googleRevoke: (id: string) => authFetch(`${BASE}/api/google/permissions/${id}`, { method: "DELETE" }),

  // mcp
  mcpCatalog: () => authFetch(`${BASE}/api/mcp/catalog`).then(j<any[]>),
  mcpDiagnostics: () => authFetch(`${BASE}/api/mcp/diagnostics`).then(j<any>),
  mcpServers: () => authFetch(`${BASE}/api/mcp/servers`).then(j<any[]>),
  mcpInstall: (key: string, path?: string) => authFetch(`${BASE}/api/mcp/install`, json("POST", { key, path })).then(jAuth),
  mcpInstallCustom: (name: string, command: string, args: string[]) => authFetch(`${BASE}/api/mcp/install-custom`, json("POST", { name, command, args })).then(jAuth),
  mcpRemove: (id: string) => authFetch(`${BASE}/api/mcp/servers/${id}`, { method: "DELETE" }),
  mcpStart: (id: string) => authFetch(`${BASE}/api/mcp/servers/${id}/start`, { method: "POST" }).then(jAuth),
  mcpStop: (id: string) => authFetch(`${BASE}/api/mcp/servers/${id}/stop`, { method: "POST" }),
  mcpTools: (id: string) => authFetch(`${BASE}/api/mcp/servers/${id}/tools`).then(jAuth),
  mcpCall: (id: string, tool: string, args: any, grant: "once" | "chat" | "always", conversation_id?: string | null) =>
    authFetch(`${BASE}/api/mcp/servers/${id}/call`, json("POST", { tool, arguments: args, grant, conversation_id })).then(jAuth),

  // skills
  listSkills: () => authFetch(`${BASE}/api/skills`).then(j<any[]>),
  createSkill: (name: string, description: string, instructions: string, icon?: string) =>
    authFetch(`${BASE}/api/skills`, json("POST", { name, description, instructions, icon })).then(jAuth),
  updateSkill: (id: string, name: string, description: string, instructions: string, icon: string) =>
    authFetch(`${BASE}/api/skills/${id}`, json("PUT", { name, description, instructions, icon })).then(jAuth),
  deleteSkill: (id: string) => authFetch(`${BASE}/api/skills/${id}`, { method: "DELETE" }).then(jAuth),

  // translate
  translateStatus: () => authFetch(`${BASE}/api/translate/status`).then(j<any>),
  translateSetup: () => authFetch(`${BASE}/api/translate/setup`, { method: "POST" }).then(jAuth),
  translateSetupStatus: () => authFetch(`${BASE}/api/translate/setup/status`).then(j<any>),
  translateCatalog: () => authFetch(`${BASE}/api/translate/catalog`).then(j<any[]>),
  translateInstall: (from_code: string, to_code: string) => authFetch(`${BASE}/api/translate/install`, json("POST", { from_code, to_code })).then(jAuth),

  // autonomous Teacher Mode
  teacherStatus: () => authFetch(`${BASE}/api/teacher/status`).then(j<any>),
  teacherCurriculum: (topic: string) => authFetch(`${BASE}/api/teacher/curriculum`, json("POST", { topic })).then(jAuth),
  teacherCurriculumStream: async (topic: string, onEvent: (event:any)=>void, signal?:AbortSignal) => {
    const res=await authFetch(`${BASE}/api/teacher/curriculum/stream`,{...json("POST",{topic}),signal});
    if(!res.ok) return jAuth(res);
    if(!res.body) throw new Error("Teacher stream unavailable");
    const reader=res.body.getReader(), decoder=new TextDecoder(); let buffer="";
    while(true){
      const {value,done}=await reader.read(); if(done) break;
      buffer+=decoder.decode(value,{stream:true});
      const chunks=buffer.split("\n\n"); buffer=chunks.pop()||"";
      for(const chunk of chunks){
        const line=chunk.split("\n").find(x=>x.startsWith("data:"));
        if(line) onEvent(JSON.parse(line.slice(5).trim()));
      }
    }
  },

  // privacy-scoped cloud training teachers
  cloudTrainingProviders: () => authFetch(`${BASE}/api/training/cloud/providers`).then(j<any>),
  cloudTrainingConfigure: (body: any) => authFetch(`${BASE}/api/training/cloud/providers`, json("PUT", body)).then(jAuth),
  cloudTrainingClearKey: (provider: string) => authFetch(`${BASE}/api/training/cloud/providers/${encodeURIComponent(provider)}/key`, { method: "DELETE" }).then(jAuth),
  cloudTrainingDistill: (dataset_id: string) => authFetch(`${BASE}/api/training/cloud/distill`, json("POST", { dataset_id })).then(jAuth),

  // updates
  checkUpdates: (force = false) => authFetch(`${BASE}/api/updates?force=${force}`).then(j<any>),
  installUpdate: () => authFetch(`${BASE}/api/updates/install`, { method: "POST" }).then(jAuth),
};
