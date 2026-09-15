<template>
  <main class="page">
    <h1>我的成绩</h1>
    <p class="hint">
      同一题、同一语言，取最好一次 AC 的耗时排名。测试运行不计入。已集齐全部语言
      {{ overview?.complete ?? 0 }} / {{ overview?.total_problems ?? 0 }} 题。
    </p>
    <h2>技能树</h2>
    <p class="hint">点亮该族下任意一题的任意语言 AC。点击跳到题单筛选。</p>
    <div class="tag-row">
      <button
        v-for="fam in families"
        :key="fam.id"
        type="button"
        class="chip"
        :class="{ on: fam.lit }"
        @click="goFamily(fam.tags)"
      >
        {{ fam.label }}
      </button>
    </div>
    <h2>语言 bingo</h2>
    <table v-if="overview?.bingo.length">
      <thead>
        <tr>
          <th>题目</th>
          <th>语言</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in overview.bingo" :key="row.slug">
          <td>
            <router-link :to="`/problems/${row.slug}`">{{ row.title }}</router-link>
          </td>
          <td>
            <LangBingo :languages="row.languages" :ac="row.ac_languages" />
          </td>
        </tr>
      </tbody>
    </table>
    <h2>排名明细</h2>
    <p v-if="!overview?.rows.length" class="hint">还没有 AC 记录。通过提交（不是测试）后会出现在这里。</p>
    <table v-else>
      <thead>
        <tr>
          <th>题目</th>
          <th>语言</th>
          <th>最好耗时</th>
          <th>名次</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="r in overview.rows" :key="`${r.slug}-${r.language}`">
          <td>
            <router-link :to="`/problems/${r.slug}`">{{ r.title }}</router-link>
          </td>
          <td>{{ languageLabel(r.language) }}</td>
          <td>{{ r.time_ms }} ms</td>
          <td>第 {{ r.rank }} / {{ r.total }} 名</td>
        </tr>
      </tbody>
    </table>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import LangBingo from "../components/LangBingo.vue";
import { Scores, type ScoreOverview } from "../api";
import { languageLabel } from "../languages";
import { TAG_FAMILIES } from "../tags";

const router = useRouter();
const overview = ref<ScoreOverview | null>(null);

const families = computed(() => {
  const bingo = overview.value?.bingo || [];
  return TAG_FAMILIES.map((fam) => {
    const lit = bingo.some(
      (row) =>
        row.ac_languages.length > 0 && fam.tags.some((t) => row.tags.includes(t)),
    );
    return { ...fam, lit };
  });
});

onMounted(async () => {
  overview.value = await Scores.overview();
});

function goFamily(tags: string[]) {
  void router.push({ path: "/", query: { tags: tags.join(",") } });
}
</script>
