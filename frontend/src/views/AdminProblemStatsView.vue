<template>
  <main class="page">
    <h1>每题统计</h1>
    <p class="hint">通过率 = AC / 全部正式提交。测试运行不计。点一行看该题日志。</p>
    <p v-if="error" class="err">{{ error }}</p>
    <p v-else-if="!rows.length" class="hint">还没有题目。</p>
    <table v-else>
      <thead>
        <tr>
          <th>题目</th>
          <th class="num">提交</th>
          <th class="num">AC</th>
          <th class="num">通过率</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="p in rows"
          :key="p.slug"
          class="clickable"
          @click="goLog(p.slug)"
        >
          <td>{{ p.title }}</td>
          <td class="num">{{ p.submissions }}</td>
          <td class="num">{{ p.accepted }}</td>
          <td class="num">{{ formatPassRate(p.accepted, p.submissions) }}</td>
        </tr>
      </tbody>
    </table>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { Admin, type ProblemStat } from "../api";
import { formatPassRate } from "../format";

const router = useRouter();
const stats = ref<ProblemStat[]>([]);
const error = ref("");
const rows = computed(() =>
  [...stats.value].sort((a, b) => b.submissions - a.submissions || a.slug.localeCompare(b.slug)),
);

onMounted(async () => {
  try {
    stats.value = await Admin.problemStats();
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  }
});

function goLog(slug: string) {
  void router.push(`/admin/data/problems/${encodeURIComponent(slug)}`);
}
</script>
