const LOCAL_HOSTS = new Set(["127.0.0.1", "localhost"]);

export const API_BASE = LOCAL_HOSTS.has(window.location.hostname)
  ? "http://127.0.0.1:8000"
  : "https://gastro-kg-expert-system.vercel.app";

export const REQUEST_TIMEOUT_MS = 60000;
export const SLOW_NOTICE_MS = 5000;
