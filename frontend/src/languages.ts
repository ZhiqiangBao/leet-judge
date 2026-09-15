export const LANGUAGE_LABELS: Record<string, string> = {
  python3: "Python 3",
  c: "C",
  cpp17: "C++20",
  javascript: "JavaScript (Node)",
  typescript: "TypeScript",
  go: "Go",
  rust: "Rust",
  zig: "Zig",
};

export const LANGUAGE_SHORT: Record<string, string> = {
  python3: "Py",
  c: "C",
  cpp17: "C++",
  javascript: "JS",
  typescript: "TS",
  go: "Go",
  rust: "Rs",
  zig: "Zig",
};

export const LANGUAGE_ORDER = Object.keys(LANGUAGE_LABELS);

export function languageShort(id: string): string {
  return LANGUAGE_SHORT[id] || id;
}

export function languageLabel(id: string, fallback?: string): string {
  return LANGUAGE_LABELS[id] || fallback || id;
}

export function languageQueryId(input: string): string {
  const t = input.trim().toLowerCase();
  if (!t) return "";
  if (t === "c++20" || t === "cpp20" || t === "c++" || t === "cxx") return "cpp17";
  for (const [id, label] of Object.entries(LANGUAGE_LABELS)) {
    if (label.toLowerCase() === t) return id;
  }
  return input.trim();
}
