const CERTAINTY_WORDS = {
  "0.1": "almost unsure",
  "0.2": "a little sure",
  "0.3": "slightly sure",
  "0.4": "somewhat sure",
  "0.5": "moderately sure",
  "0.6": "fairly sure",
  "0.7": "quite sure",
  "0.8": "very sure",
  "0.9": "almost certain",
  "1.0": "certain",
};

const STATUS_LABELS = {
  FullRuleMatch: "All rule conditions met",
  PartialMatch: "Some conditions met",
  WeakMatch: "Weak evidence",
};

export function formatCf(value) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "0.000";
  return num.toFixed(3);
}

export function certaintyWords(value) {
  const key = Number(value).toFixed(1);
  return CERTAINTY_WORDS[key] || key;
}

export function statusText(status) {
  return STATUS_LABELS[status] || "Weak evidence";
}

export function isSafeHttpsUrl(value) {
  return typeof value === "string" && value.startsWith("https://");
}

export function triageClass(level) {
  return level ? `triage-${level}` : "triage-PrimaryCare";
}
