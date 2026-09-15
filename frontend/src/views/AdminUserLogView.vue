<template>
  <main class="page">
    <p class="hint">
      <router-link to="/admin/data/users">用户总览</router-link>
      · 提交日志
    </p>
    <h1>{{ heading }}</h1>
    <p class="hint" v-if="user">
      总提交 {{ user.submissions }}，AC {{ user.accepted }}，通过率
      {{ formatPassRate(user.accepted, user.submissions) }}。
    </p>
    <table v-if="user?.by_language.length" class="lang-table">
      <thead>
        <tr>
          <th>语言</th>
          <th class="num">提交</th>
          <th class="num">AC</th>
          <th class="num">通过率</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="lang in user.by_language" :key="lang.language">
          <td>{{ languageLabel(lang.language) }}</td>
          <td class="num">{{ lang.submissions }}</td>
          <td class="num">{{ lang.accepted }}</td>
          <td class="num">{{ formatPassRate(lang.accepted, lang.submissions) }}</td>
        </tr>
      </tbody>
    </table>
    <p v-if="error" class="err">{{ error }}</p>
    <table>
      <thead>
        <tr>
          <th>题目</th>
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
            <router-link :to="`/admin/data/problems/${s.problem_slug}`" @click.stop>
              {{ s.problem_slug }}
            </router-link>
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
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { Admin, type Submission, type UserStat } from "../api";
import { formatPassRate, formatWhen } from "../format";
import { languageLabel } from "../languages";

const route = useRoute();
const userId = Number(route.params.userId);
const user = ref<UserStat | null>(null);
const rows = ref<Submission[]>([]);
const error = ref("");
const openId = ref<number | null>(null);
const openSource = ref("");
const heading = computed(() => (user.value ? user.value.username : `用户 ${userId}`));

onMounted(async () => {
  try {
    const users = await Admin.userStats();
    user.value = users.find((row) => row.user_id === userId) || null;
    rows.value = await Admin.submissions({ userId, limit: 300 });
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
