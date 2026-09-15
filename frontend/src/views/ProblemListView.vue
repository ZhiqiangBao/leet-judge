<template>
  <main class="page problem-list">
    <h1>题库</h1>
    <div class="list-toolbar">
      <input v-model="search" class="search" placeholder="搜索题目" />
      <button
        v-for="d in difficulties"
        :key="d.id"
        type="button"
        class="chip"
        :class="[d.id, { on: selectedDiffs.includes(d.id) }]"
        @click="toggleDiff(d.id)"
      >
        {{ d.label }}
      </button>
    </div>
    <div class="tag-row">
      <button
        v-for="t in allTags"
        :key="t"
        type="button"
        class="chip"
        :class="{ on: selectedTags.includes(t) }"
        @click="toggleTag(t)"
      >
        {{ tagLabel(t) }}
      </button>
    </div>
    <table>
      <thead>
        <tr>
          <th>状态</th>
          <th>题目</th>
          <th>知识点</th>
          <th>难度</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="p in filtered" :key="p.slug">
          <td>
            <span v-if="p.solved" class="ac">AC</span>
            <span v-else-if="p.attempted" class="muted">尝试过</span>
            <span v-else class="muted">—</span>
          </td>
          <td>
            <router-link class="title-link" :to="`/problems/${p.slug}`">{{ p.title }}</router-link>
            <span v-if="!p.published" class="muted"> 未发布</span>
            <LangBingo compact :languages="p.languages" :ac="p.ac_languages" />
          </td>
          <td>
            <span v-for="t in tagsOf(p)" :key="t" class="chip tiny">{{ tagLabel(t) }}</span>
          </td>
          <td :class="p.difficulty">{{ difficultyLabel(p.difficulty) }}</td>
        </tr>
      </tbody>
    </table>
    <p v-if="!filtered.length" class="hint">没有符合筛选的题目。管理员导入后须先在「题库 → 发布」公开，普通登录才能看见。</p>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Problems, type ProblemMeta } from "../api";
import { WEEKLY_TAG, tagLabel } from "../tags";
import LangBingo from "../components/LangBingo.vue";

const difficulties = [
  { id: "easy", label: "Easy" },
  { id: "medium", label: "Medium" },
  { id: "hard", label: "Hard" },
];

const route = useRoute();
const router = useRouter();
const problems = ref<ProblemMeta[]>([]);
const search = ref("");
const selectedDiffs = ref<string[]>([]);
const selectedTags = ref<string[]>([]);

function tagsOf(p: ProblemMeta) {
  return p.weekly ? [WEEKLY_TAG, ...p.tags] : p.tags;
}

const allTags = computed(() => {
  const set = new Set<string>();
  if (problems.value.some((p) => p.weekly)) set.add(WEEKLY_TAG);
  for (const p of problems.value) for (const t of p.tags) set.add(t);
  const rest = [...set].filter((t) => t !== WEEKLY_TAG).sort();
  return set.has(WEEKLY_TAG) ? [WEEKLY_TAG, ...rest] : rest;
});

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase();
  return problems.value.filter((p) => {
    const tags = tagsOf(p);
    if (q && !p.title.toLowerCase().includes(q) && !p.slug.includes(q)) return false;
    if (selectedDiffs.value.length && !selectedDiffs.value.includes(p.difficulty)) return false;
    if (selectedTags.value.length && !selectedTags.value.some((t) => tags.includes(t))) return false;
    return true;
  });
});

onMounted(async () => {
  problems.value = await Problems.list();
  readQuery();
});

watch([search, selectedDiffs, selectedTags], writeQuery);

function readQuery() {
  const q = route.query;
  search.value = typeof q.q === "string" ? q.q : "";
  selectedDiffs.value = typeof q.difficulty === "string" && q.difficulty ? q.difficulty.split(",") : [];
  const tags = typeof q.tags === "string" && q.tags ? q.tags.split(",") : [];
  if (q.weekly === "1" || q.weekly === "true") {
    if (!tags.includes(WEEKLY_TAG)) tags.unshift(WEEKLY_TAG);
  }
  selectedTags.value = tags;
}

function writeQuery() {
  const query: Record<string, string> = {};
  if (search.value.trim()) query.q = search.value.trim();
  if (selectedDiffs.value.length) query.difficulty = selectedDiffs.value.join(",");
  if (selectedTags.value.length) query.tags = selectedTags.value.join(",");
  void router.replace({ query });
}

function toggleDiff(id: string) {
  selectedDiffs.value = selectedDiffs.value.includes(id)
    ? selectedDiffs.value.filter((x) => x !== id)
    : [...selectedDiffs.value, id];
}

function toggleTag(id: string) {
  selectedTags.value = selectedTags.value.includes(id)
    ? selectedTags.value.filter((x) => x !== id)
    : [...selectedTags.value, id];
}

function difficultyLabel(d: string) {
  return d === "easy" ? "Easy" : d === "medium" ? "Medium" : d === "hard" ? "Hard" : d;
}
</script>
