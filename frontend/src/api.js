// Resolve the API base once: honour VITE_API_BASE if set, otherwise probe
// localhost:8000..8010 and use the first that answers /health. This lets the
// backend land on any free port (see ../run.py) without reconfiguring here.
const ENV_BASE = import.meta.env.VITE_API_BASE;
const CANDIDATES = ENV_BASE
  ? [ENV_BASE]
  : Array.from({ length: 11 }, (_, i) => `http://localhost:${8000 + i}`);

let basePromise = null;

async function probe(base) {
  try {
    const res = await fetch(base + "/health", { method: "GET" });
    return res.ok ? base : null;
  } catch {
    return null; // nothing listening on that port
  }
}

async function resolveBase() {
  for (const base of CANDIDATES) {
    const hit = await probe(base);
    if (hit) return hit;
  }
  return CANDIDATES[0]; // none answered — let calls surface a clear error
}

function getBase() {
  return (basePromise ||= resolveBase());
}

async function req(method, path, body) {
  const base = await getBase();
  const res = await fetch(base + path, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) {
    const detail = data?.detail || res.statusText;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

export const api = {
  base: getBase, // resolved API base, for display
  health: () => req("GET", "/health"),

  // nodes (schema v3) — generic create + bulk by node type
  addNode: (type, body) => req("POST", `/nodes/${type}`, body),
  bulkNodes: (type, rows) => req("POST", `/nodes/${type}/bulk`, { rows }),

  // predict / agent
  predict: (b) => req("POST", "/predict", b),
  train: () => req("POST", "/predict/train"),
  chat: (message) => req("POST", "/agent/chat", { message }),
  listSites: () => req("GET", "/sites"),
  deleteSite: (siteId) => req("DELETE", `/sites/${siteId}`),
};