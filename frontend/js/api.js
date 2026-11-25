import { API_BASE, REQUEST_TIMEOUT_MS } from "./config.js";

export class ApiError extends Error {
  constructor(status, message, errors = [], requestId = null) {
    super(message);
    this.status = status;
    this.errors = errors;
    this.requestId = requestId;
  }
}

async function fetchJson(url, options = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const response = await fetch(url, { ...options, signal: controller.signal });
    const contentType = response.headers.get("content-type") || "";
    const isJson = contentType.includes("application/json");
    const data = isJson ? await response.json() : null;

    if (!response.ok) {
      if (response.status === 429) {
        throw new ApiError(429, "Too many requests, wait a minute.", [], null);
      }
      const errors = data && Array.isArray(data.errors) ? data.errors : [];
      const requestId = data && data.requestId ? data.requestId : null;
      const msg = errors[0]?.message || `Request failed (${response.status}).`;
      throw new ApiError(response.status, msg, errors, requestId);
    }
    return data;
  } catch (err) {
    if (err instanceof ApiError) throw err;
    if (err.name === "AbortError") {
      throw new ApiError(0, "The request timed out after 60 seconds.", [], null);
    }
    throw new ApiError(0, "Unable to reach the screening API.", [], null);
  } finally {
    clearTimeout(timer);
  }
}

export function getForm() {
  return fetchJson(`${API_BASE}/api/form`);
}

export function getRules() {
  return fetchJson(`${API_BASE}/api/rules`);
}

export function runConsultation(payload) {
  return fetchJson(`${API_BASE}/api/consultations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function getSampleIndex() {
  return fetchJson("data/cases/index.json");
}

export function getSampleCase(caseId) {
  const safeId = encodeURIComponent(caseId);
  return fetchJson(`data/cases/${safeId}.json`);
}

export function getQueries() {
  return fetchJson("data/queries.json");
}

export function getPresets() {
  return fetchJson("data/presets.json");
}

export function ontologyDownloadUrl(name) {
  return `${API_BASE}/api/ontology/${encodeURIComponent(name)}`;
}
