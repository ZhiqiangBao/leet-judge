<template>
  <main class="page">
    <p class="hint">
      <router-link to="/admin/data/problems">每题统计</router-link>
      · 提交日志
    </p>
    <h1>{{ title }}</h1>
    <p class="hint">最近 {{ rows.length }} 条正式提交。点行可看源码。测试运行不在这里。</p>
    <p v-if="error" class="err">{{ error }}</p>
    <table>
      <thead>
        <tr>
          <th>用户</th>
          <th>语言</th>
          <th>结果</th>
          <th>时间</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="s in rows"
          :key="s.id"
          class="clickable"
          :class="{ open: openId === s.id }"
          @click="toggle(s.id)"
        >
          <td>
            <router-link :to="`/admin/data/users/${s.user_id}`" @click.stop>{{ s.username }}</router-link>
          </td>
          <td>{{ languageLabel(s.language) }}</td>
          <td :class="(s.verdict || s.status).toLowerCase()">{{ s.verdict || s.status }}</td>
          <td>{{ formatWhen(s.created_at) }}</td>
        </tr>
      </tbody>
    </table>
    <pre class="source" v-if="openSource">{{ openSource }}</pre>
  </main>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { Admin, type Submission } from "../api";
import { formatWhen } from "../format";
import { languageLabel } from "../languages";

const route = useRoute();
const slug = String(route.params.slug || "");
const title = ref(slug);
const rows = ref<Submission[]>([]);
const error = ref("");
const openId = ref<number | null>(null);
const openSource = ref("");

onMounted(async () => {
  try {
    const stats = await Admin.problemStats();
    const hit = stats.find((row) => row.slug === slug);
    if (hit) title.value = hit.title;
    rows.value = await Admin.submissions({ slug, limit: 300 });
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  }
});

async function toggle(id: number) {
  if (openId.value === id) {
    openId.value = null;
    openSource.value = "";
    return;
  }
  openId.value = id;
  const detail = await Admin.submission(id);
  openSource.value = detail.source || "（无源码）";
}
</script>
