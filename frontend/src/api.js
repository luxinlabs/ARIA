const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";
let activeRunId = null;

export function setActiveRunId(runId) {
  activeRunId = runId || null;
}

export function getActiveRunId() {
  return activeRunId;
}

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(activeRunId ? { "X-Run-Id": activeRunId } : {}),
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `Request failed: ${res.status}`);
  }

  if (res.status === 204) {
    return null;
  }

  return res.json();
}

export const apiBase = API_BASE;

export const ariaApi = {
  init(payload) {
    return request("/aria/init", { method: "POST", body: JSON.stringify(payload) });
  },
  sessions() {
    return request("/aria/sessions");
  },
  activateSession(runId) {
    return request(`/aria/sessions/${runId}/activate`, { method: "POST" });
  },
  deleteSession(runId) {
    return request(`/aria/sessions/${runId}`, { method: "DELETE" });
  },
  status() {
    return request("/aria/status");
  },
  memory() {
    return request("/aria/memory");
  },
  patchMemory(payload) {
    return request("/aria/memory", { method: "PATCH", body: JSON.stringify(payload) });
  },
  hypotheses() {
    return request("/aria/hypotheses");
  },
  experiments() {
    return request("/aria/experiments");
  },
  performance() {
    return request("/aria/performance");
  },
  step() {
    return request("/aria/step", { method: "POST" });
  },
  pause(reason) {
    return request("/aria/pause", { method: "POST", body: JSON.stringify({ reason }) });
  },
  reset() {
    return request("/aria/reset", { method: "POST" });
  },
};
