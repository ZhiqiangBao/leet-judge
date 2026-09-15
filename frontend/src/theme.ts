export type Theme = "dark" | "light";

export const THEME_KEY = "leet-hub-theme";
export const THEME_EVENT = "leet-hub-theme";

export function readTheme(): Theme {
  try {
    const value = localStorage.getItem(THEME_KEY);
    if (value === "light" || value === "dark") return value;
  } catch {
    /* private mode */
  }
  return "dark";
}

export function applyTheme(theme: Theme): void {
  document.documentElement.dataset.theme = theme;
  document.documentElement.style.colorScheme = theme;
  try {
    localStorage.setItem(THEME_KEY, theme);
  } catch {
    /* private mode */
  }
  window.dispatchEvent(new CustomEvent(THEME_EVENT, { detail: theme }));
}

export function toggleTheme(): Theme {
  const next: Theme = readTheme() === "light" ? "dark" : "light";
  applyTheme(next);
  return next;
}
