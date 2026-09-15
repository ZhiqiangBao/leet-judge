export function formatPassRate(accepted: number, submissions: number): string {
  if (submissions <= 0) return "—";
  return `${((100 * accepted) / submissions).toFixed(1)}%`;
}

export function formatWhen(iso: string): string {
  if (!iso) return "—";
  return iso.replace("T", " ").replace("Z", "").slice(0, 19);
}
