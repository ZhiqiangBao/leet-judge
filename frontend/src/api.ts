export type User = {
  id: number;
  username: string;
  is_admin: boolean;
};

export type Language = {
  id: string;
  display_name: string;
  implemented: boolean;
  available: boolean;
  runtime_detected: boolean;
  reason: string | null;
};

export type ProblemMeta = {
  slug: string;
  title: string;
  difficulty: "easy" | "medium" | "hard";
  time_limit_ms: number;
  memory_limit_mb: number;
  tags: string[];
  solved: boolean;
  attempted: boolean;
  ac_languages: string[];
  weekly: boolean;
  added_at: string | null;
  languages: string[];
};

export type PublicTest = {
  args: unknown[];
  expected: unknown;
};

export type ProblemDetail = ProblemMeta & {
  statement_md: string;
  signature: Signature;
  starter: Record<string, string>;
  public_tests: PublicTest[];
  best_by_language: Record<string, number>;
  traps: TrapSlot[];
};

export type TrapSlot = {
  id: string;
  title: string;
  blurb: string;
  loaded: boolean;
  family: string;
  verified: boolean;
};

export type Signature = {
  class_name: string;
  method: string;
  params: { name: string; type: string }[];
  return_type: string;
  compare: "exact" | "any_order";
};

export type Submission = {
  id: number;
  problem_slug: string;
  language: string;
  status: string;
  verdict: string | null;
  details: Record<string, unknown> | null;
  compile_log: string | null;
  time_ms: number | null;
  created_at: string;
  judged_at: string | null;
  source?: string | null;
  username?: string;
  user_id?: number;
};

export type RunResult = {
  kind: "test";
  verdict: string;
  details: Record<string, unknown> | null;
  compile_log: string | null;
  time_ms: number | null;
  public_count: number;
};

export type RankEntry = {
  rank: number;
  username: string;
  time_ms: number;
  is_me: boolean;
};

export type Ranking = {
  slug: string;
  language: string;
  total: number;
  mine: RankEntry | null;
  entries: RankEntry[];
};

export type ScoreRow = {
  slug: string;
  title: string;
  language: string;
  time_ms: number;
  rank: number;
  total: number;
};

export type ScoreOverview = {
  complete: number;
  total_problems: number;
  rows: ScoreRow[];
  bingo: {
    slug: string;
    title: string;
    tags: string[];
    languages: string[];
    ac_languages: string[];
  }[];
};

export type DuelPlayer = {
  user_id: number;
  username: string;
  ac: boolean;
  time_ms: number | null;
  language: string | null;
  judged_at: string | null;
};

export type Duel = {
  code: string;
  slug: string;
  title: string;
  status: string;
  host: DuelPlayer;
  guest: DuelPlayer | null;
  winner_id: number | null;
  expires_at: string;
  started_at: string | null;
  is_host: boolean;
  is_guest: boolean;
};

export type AdminStats = {
  users: number;
  submissions: number;
  accepted: number;
  problems: number;
  by_problem: ProblemStat[];
};

export type ProblemStat = {
  slug: string;
  title: string;
  submissions: number;
  accepted: number;
};

export type LanguageStat = {
  language: string;
  submissions: number;
  accepted: number;
};

export type UserStat = {
  user_id: number;
  username: string;
  submissions: number;
  accepted: number;
  by_language: LanguageStat[];
};

async function parseError(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) {
      return body.detail.map((d: { msg?: string }) => d.msg || JSON.stringify(d)).join("; ");
    }
  } catch {
    /* ignore */
  }
  return res.statusText;
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (init?.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const res = await fetch(path, { credentials: "include", ...init, headers });
  if (res.status === 401) {
    throw Object.assign(new Error("unauthorized"), { status: 401 });
  }
  if (!res.ok) {
    throw Object.assign(new Error(await parseError(res)), { status: res.status });
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const Auth = {
  me: () => api<User>("/api/auth/me"),
  login: (username: string, password: string) =>
    api<User>("/api/auth/login", { method: "POST", body: JSON.stringify({ username, password }) }),
  register: (username: string, password: string) =>
    api<User>("/api/auth/register", { method: "POST", body: JSON.stringify({ username, password }) }),
  logout: () => api<{ ok: boolean }>("/api/auth/logout", { method: "POST" }),
};

export const Problems = {
  list: () => api<ProblemMeta[]>("/api/problems"),
  get: (slug: string) => api<ProblemDetail>(`/api/problems/${slug}`),
  submit: (slug: string, language: string, source: string) =>
    api<Submission>(`/api/problems/${slug}/submit`, {
      method: "POST",
      body: JSON.stringify({ language, source }),
    }),
  run: (slug: string, language: string, source: string) =>
    api<RunResult>(`/api/problems/${slug}/run`, {
      method: "POST",
      body: JSON.stringify({ language, source }),
    }),
  ranking: (slug: string, language: string) =>
    api<Ranking>(`/api/problems/${slug}/ranking?language=${encodeURIComponent(language)}`),
  getDraft: (slug: string, language: string) =>
    api<{ language: string; source: string; from_starter: boolean; updated_at: string | null }>(
      `/api/problems/${slug}/draft?language=${encodeURIComponent(language)}`,
    ),
  saveDraft: (slug: string, language: string, source: string) =>
    api(`/api/problems/${slug}/draft`, {
      method: "PUT",
      body: JSON.stringify({ language, source }),
    }),
};

export const Scores = {
  mine: () => api<ScoreRow[]>("/api/scores"),
  overview: () => api<ScoreOverview>("/api/scores/overview"),
};

export const Duels = {
  create: (slug: string) =>
    api<Duel>("/api/duels/", { method: "POST", body: JSON.stringify({ slug }) }),
  join: (code: string) => api<Duel>(`/api/duels/${encodeURIComponent(code)}/join`, { method: "POST" }),
  get: (code: string) => api<Duel>(`/api/duels/${encodeURIComponent(code)}`),
};

export const Submissions = {
  list: (slug?: string) => api<Submission[]>(`/api/submissions${slug ? `?slug=${encodeURIComponent(slug)}` : ""}`),
  get: (id: number) => api<Submission>(`/api/submissions/${id}`),
};

export const Languages = {
  list: () => api<Language[]>("/api/languages"),
};

export const Admin = {
  guide: () => api<{ markdown: string }>("/api/admin/guide"),
  stats: () => api<AdminStats>("/api/admin/stats"),
  problemStats: () => api<ProblemStat[]>("/api/admin/stats/problems"),
  userStats: () => api<UserStat[]>("/api/admin/stats/users"),
  submissions: (q?: { slug?: string; username?: string; userId?: number; language?: string; limit?: number }) => {
    const params = new URLSearchParams();
    if (q?.slug) params.set("slug", q.slug);
    if (q?.username) params.set("username", q.username);
    if (q?.userId != null) params.set("user_id", String(q.userId));
    if (q?.language) params.set("language", q.language);
    if (q?.limit != null) params.set("limit", String(q.limit));
    const qs = params.toString();
    return api<Submission[]>(`/api/admin/submissions${qs ? `?${qs}` : ""}`);
  },
  submission: (id: number) => api<Submission>(`/api/admin/submissions/${id}`),
  create: (body: unknown) => api("/api/admin/problems", { method: "POST", body: JSON.stringify(body) }),
  update: (slug: string, body: unknown) =>
    api(`/api/admin/problems/${slug}`, { method: "PUT", body: JSON.stringify(body) }),
  replaceTests: (slug: string, tests: unknown[]) =>
    api(`/api/admin/problems/${slug}/tests`, { method: "PUT", body: JSON.stringify({ tests }) }),
  appendTests: (slug: string, tests: unknown[]) =>
    api(`/api/admin/problems/${slug}/tests:append`, { method: "POST", body: JSON.stringify({ tests }) }),
  reload: () => api<{ ok: boolean; count: number }>("/api/admin/reload", { method: "POST" }),
  syncGit: () =>
    api<{
      ok: boolean;
      count: number;
      unchanged: boolean;
      slugs: string[];
      needs_restart: boolean;
      before: string;
      after: string;
    }>("/api/admin/sync-git", { method: "POST" }),
  importProblems: (body: FormData) =>
    api<{ ok: boolean; slugs: string[]; count: number }>("/api/admin/problems/import", {
      method: "POST",
      body,
    }),
  mergeFiles: (body: FormData) =>
    api<{ ok: boolean; slug: string; count: number }>("/api/admin/problems/files", {
      method: "POST",
      body,
    }),
  writeStarters: (slug: string) =>
    api<{ ok: boolean; slug: string; wrote: string[]; skipped: string[] }>(
      `/api/admin/problems/${encodeURIComponent(slug)}/starters`,
      { method: "POST" },
    ),
};
