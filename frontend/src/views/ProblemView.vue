<template>
  <div class="workspace" v-if="problem">
    <section class="statement">
      <div class="tabs">
        <button type="button" :class="{ on: leftTab === 'desc' }" @click="leftTab = 'desc'">题目</button>
        <button v-if="hasGrid" type="button" :class="{ on: leftTab === 'grid' }" @click="leftTab = 'grid'">网格</button>
        <button type="button" :class="{ on: leftTab === 'rank' }" @click="leftTab = 'rank'">排行</button>
      </div>
      <template v-if="leftTab === 'desc'">
        <h1>{{ problem.title }}</h1>
        <div class="meta">
          <span :class="problem.difficulty">{{ difficultyLabel(problem.difficulty) }}</span>
          <span>{{ problem.time_limit_ms }} ms</span>
          <span>{{ problem.memory_limit_mb }} MB</span>
          <span v-if="problem.solved" class="ac">已通过</span>
          <span v-for="t in displayTags" :key="t" class="chip">{{ tagLabel(t) }}</span>
        </div>
        <div class="md" v-html="html"></div>
      </template>
      <div v-else-if="leftTab === 'grid'" class="grid-tab">
        <GridPlay :signature="problem.signature" :tests="problem.public_tests || []" />
      </div>
      <div class="rank-box" v-else>
        <p class="hint" v-if="!ranking">正在加载排行…</p>
        <p class="hint" v-else-if="ranking.mine">
          当前语言你第 {{ ranking.mine.rank }} / {{ ranking.total }} 名 · 最好 {{ ranking.mine.time_ms }} ms
        </p>
        <p class="hint" v-else>当前语言还没有 AC，提交通过后计入排行（测试不计成绩）。</p>
        <table v-if="ranking?.entries.length">
          <thead>
            <tr>
              <th>名次</th>
              <th>用户</th>
              <th>最好耗时</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="e in ranking.entries" :key="e.username" :class="{ me: e.is_me }">
              <td>{{ e.rank }}</td>
              <td>{{ e.username }}{{ e.is_me ? "（我）" : "" }}</td>
              <td>{{ e.time_ms }} ms</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
    <section class="editor-pane">
      <CodeEditor v-model="source" :language="language" />
      <div class="console" v-if="result">
        <div class="console-head">
          <span v-if="resultKind === 'test'" class="muted">测试结果（不计成绩）</span>
          <span v-else class="muted">提交结果</span>
          <span :class="(result.verdict || result.status || '').toLowerCase()">
            {{ result.verdict || result.status }}
          </span>
          <span v-if="result.time_ms != null" class="muted">{{ result.time_ms }} ms</span>
          <span v-if="ghostLine" class="muted">{{ ghostLine }}</span>
        </div>
        <p v-if="failLine" class="hint bar-hint">{{ failLine }}</p>
        <pre v-if="result.compile_log">{{ result.compile_log }}</pre>
        <div v-if="details?.message">{{ details.message }}</div>
        <ul v-if="visibleCases.length">
          <li v-for="c in visibleCases" :key="c.index">
            Case {{ Number(c.index) + 1 }} {{ c.passed ? "通过" : "失败" }}
            <span v-if="c.args">
              输入 {{ JSON.stringify(c.args) }} 期望 {{ JSON.stringify(c.expected) }}
              <template v-if="!c.passed && c.got !== undefined"> 实际 {{ JSON.stringify(c.got) }}</template>
            </span>
          </li>
        </ul>
      </div>
      <div class="editor-bar">
        <select v-model="language">
          <option v-for="lang in visibleLanguages" :key="lang.id" :value="lang.id" :disabled="!lang.available">
            {{ languageLabel(lang.id, lang.display_name) }}{{ lang.available ? "" : lang.implemented ? "（未安装编译器）" : "（接口保留）" }}
          </option>
        </select>
        <span class="draft-hint muted">{{ draftHint }}</span>
        <span v-if="bestLine" class="draft-hint muted">{{ bestLine }}</span>
        <span class="spacer" />
        <button class="ghost" type="button" :disabled="!!busy" @click="startDuel">约战</button>
        <button class="ghost" type="button" :disabled="!!busy" @click="resetStarter">重置</button>
        <button class="btn-run" type="button" :disabled="!!busy" @click="runTests">
          {{ busy === "test" ? "测试中…" : "测试" }}
        </button>
        <button class="btn-submit" type="button" :disabled="!!busy" @click="submit">
          {{ busy === "submit" ? "评测中…" : "提交" }}
        </button>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import CodeEditor from "../components/CodeEditor.vue";
import GridPlay from "../components/GridPlay.vue";
import { renderStatement } from "../markdown";
import {
  Duels,
  Languages,
  Problems,
  Submissions,
  type Language,
  type ProblemDetail,
  type Ranking,
  type RunResult,
  type Submission,
} from "../api";
import { WEEKLY_TAG, tagLabel } from "../tags";
import { languageLabel } from "../languages";

const route = useRoute();
const router = useRouter();
const problem = ref<ProblemDetail | null>(null);
const languages = ref<Language[]>([]);
const language = ref("python3");
const buffers = reactive<Record<string, string>>({});
const saved = reactive<Record<string, string>>({});
const fetched = new Set<string>();
const busy = ref<"test" | "submit" | null>(null);
const resultKind = ref<"test" | "submit">("submit");
const result = ref<(Submission | RunResult) | null>(null);
const ranking = ref<Ranking | null>(null);
const leftTab = ref<"desc" | "rank" | "grid">("desc");
const draftHint = ref("草稿会自动保存");
const ready = ref(false);
let saveTimer = 0;
let loadGen = 0;

const source = computed({
  get: () => buffers[language.value] ?? "",
  set: (value) => {
    buffers[language.value] = value;
  },
});

const details = computed(() => (result.value?.details || null) as Record<string, unknown> | null);
const cases = computed(
  () => (Array.isArray(details.value?.cases) ? details.value?.cases : []) as Array<Record<string, unknown>>,
);
const hintText = computed(() => {
  const hint = details.value?.hint as { text?: string } | undefined;
  return hint?.text || "";
});
const failLine = computed(() => {
  const kill = details.value?.kill as { title?: string; cleared?: boolean } | undefined;
  if (kill?.cleared) return "";
  if (resultKind.value === "submit" && kill?.title && hintText.value) {
    return `${kill.title} · ${hintText.value}`;
  }
  return hintText.value;
});
const visibleCases = computed(() => cases.value.filter((c) => !c.hidden && c.args));
const ghostLine = ref("");
const bestLine = computed(() => {
  if (!problem.value) return "";
  const best = problem.value.best_by_language?.[language.value];
  if (best == null) return "该语言还没有 AC";
  return `该语言最好 ${best} ms`;
});
const html = computed(() => renderStatement(problem.value?.statement_md || ""));
const displayTags = computed(() => {
  if (!problem.value) return [];
  return problem.value.weekly ? [WEEKLY_TAG, ...problem.value.tags] : problem.value.tags;
});
const hasGrid = computed(() => {
  const types = problem.value?.signature?.params.map((p) => p.type) || [];
  return types.some((t) => t === "List[List[int]]" || t === "List[str]");
});
const visibleLanguages = computed(() => {
  const allow = problem.value?.languages;
  if (allow == null) return languages.value;
  const allowed = new Set(allow);
  return languages.value.filter((l) => allowed.has(l.id));
});

onMounted(async () => {
  languages.value = await Languages.list();
  await load();
});

onBeforeUnmount(() => {
  void flushDraft();
});

watch(() => route.params.slug, load);
watch(language, (next, prev) => {
  if (!ready.value || !problem.value || next === prev) return;
  window.clearTimeout(saveTimer);
  if (buffers[next] === undefined) buffers[next] = starterOf(next);
  if (prev) void flushDraft(prev);
  void hydrate(next);
  if (leftTab.value === "rank") void loadRanking();
  else ranking.value = null;
});
watch(leftTab, (tab) => {
  if (tab === "rank") void loadRanking();
});
watch(source, () => {
  if (!ready.value) return;
  const lang = language.value;
  window.clearTimeout(saveTimer);
  saveTimer = window.setTimeout(() => {
    if (language.value !== lang) return;
    void flushDraft(lang);
  }, 1200);
});

function difficultyLabel(d: string) {
  return d === "easy" ? "Easy" : d === "medium" ? "Medium" : d === "hard" ? "Hard" : d;
}

function starterOf(lang: string) {
  if (!problem.value) return "";
  return problem.value.starter[lang] || "";
}

async function hydrate(lang: string) {
  if (!problem.value) return;
  const slug = problem.value.slug;
  const starter = starterOf(lang);
  if (buffers[lang] === undefined) buffers[lang] = starter;
  if (fetched.has(lang)) {
    draftHint.value = buffers[lang] === starter ? "使用模板，编辑后自动保存" : "已恢复上次离开时的代码";
    return;
  }
  const gen = loadGen;
  try {
    const draft = await Problems.getDraft(slug, lang);
    if (gen !== loadGen || problem.value?.slug !== slug || draft.language !== lang) return;
    fetched.add(lang);
    const untouched = buffers[lang] === starter || buffers[lang] === undefined;
    if (untouched) {
      buffers[lang] = draft.source;
      saved[lang] = draft.source;
    }
    if (language.value === lang) {
      draftHint.value = draft.from_starter ? "使用模板，编辑后自动保存" : "已恢复上次离开时的代码";
    }
  } catch {
    if (gen !== loadGen || problem.value?.slug !== slug) return;
    fetched.add(lang);
    if (buffers[lang] === undefined) buffers[lang] = starter;
  }
}

async function flushDraft(lang = language.value) {
  if (!problem.value) return;
  const text = buffers[lang] ?? "";
  if (text === (saved[lang] ?? "")) return;
  const slug = problem.value.slug;
  try {
    await Problems.saveDraft(slug, lang, text);
    if (problem.value?.slug !== slug) return;
    saved[lang] = text;
    if (language.value === lang) draftHint.value = "草稿已保存";
  } catch {
    if (language.value === lang) draftHint.value = "草稿保存失败";
  }
}

async function resetStarter() {
  const lang = language.value;
  buffers[lang] = starterOf(lang);
  saved[lang] = "";
  await flushDraft(lang);
  draftHint.value = "已恢复模板";
}

async function load() {
  ready.value = false;
  window.clearTimeout(saveTimer);
  loadGen += 1;
  fetched.clear();
  ranking.value = null;
  for (const key of Object.keys(buffers)) delete buffers[key];
  for (const key of Object.keys(saved)) delete saved[key];
  const slug = String(route.params.slug);
  problem.value = await Problems.get(slug);
  const vis = visibleLanguages.value;
  const pick = vis.find((l) => l.available) || vis[0];
  if (pick) language.value = pick.id;
  result.value = null;
  leftTab.value = "desc";
  ghostLine.value = "";
  buffers[language.value] = starterOf(language.value);
  await hydrate(language.value);
  ready.value = true;
}

async function loadRanking() {
  if (!problem.value) return;
  const slug = problem.value.slug;
  const lang = language.value;
  try {
    const data = await Problems.ranking(slug, lang);
    if (language.value !== lang || problem.value?.slug !== slug) return;
    ranking.value = data;
  } catch {
    if (language.value !== lang || problem.value?.slug !== slug) return;
    ranking.value = null;
  }
}

async function startDuel() {
  if (!problem.value) return;
  try {
    const room = await Duels.create(problem.value.slug);
    await router.push(`/duel/${room.code}`);
  } catch (err) {
    result.value = {
      kind: "test",
      verdict: "NA",
      details: { message: err instanceof Error ? err.message : "无法创建约战" },
      compile_log: null,
      time_ms: null,
      public_count: 0,
    };
    resultKind.value = "test";
  }
}

async function runTests() {
  if (!problem.value) return;
  await flushDraft(language.value);
  busy.value = "test";
  result.value = null;
  resultKind.value = "test";
  try {
    result.value = await Problems.run(problem.value.slug, language.value, buffers[language.value] ?? "");
  } catch (err) {
    result.value = {
      kind: "test",
      verdict: "NA",
      details: { message: err instanceof Error ? err.message : "测试失败" },
      compile_log: null,
      time_ms: null,
      public_count: 0,
    };
  } finally {
    busy.value = null;
  }
}

async function submit() {
  if (!problem.value) return;
  await flushDraft(language.value);
  busy.value = "submit";
  result.value = null;
  resultKind.value = "submit";
  ghostLine.value = "";
  const prevBest = problem.value.best_by_language?.[language.value] ?? null;
  try {
    let current = await Problems.submit(problem.value.slug, language.value, buffers[language.value] ?? "");
    result.value = current;
    for (let i = 0; i < 80 && (current.status === "queued" || current.status === "running"); i++) {
      await new Promise((r) => setTimeout(r, 350));
      current = await Submissions.get(current.id);
      result.value = current;
    }
    problem.value = await Problems.get(problem.value.slug);
    await loadRanking();
    if (current.verdict === "AC" && current.time_ms != null) {
      if (prevBest == null) ghostLine.value = "本题该语言首次 AC";
      else if (current.time_ms < prevBest) ghostLine.value = `比自己最好快 ${prevBest - current.time_ms} ms`;
      else if (current.time_ms > prevBest) ghostLine.value = `比自己最好慢 ${current.time_ms - prevBest} ms`;
      else ghostLine.value = "追平自己的最好成绩";
    }
  } catch (err) {
    result.value = {
      id: 0,
      problem_slug: problem.value.slug,
      language: language.value,
      status: "done",
      verdict: "NA",
      details: { message: err instanceof Error ? err.message : "提交失败" },
      compile_log: null,
      time_ms: null,
      created_at: "",
      judged_at: null,
    };
  } finally {
    busy.value = null;
  }
}
</script>
