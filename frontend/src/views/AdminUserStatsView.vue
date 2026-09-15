<template>
  <main class="page">
    <h1>用户总览</h1>
    <p class="hint">按用户 id 聚合。语言提交数和通过率写在行内；点一行看该用户日志。</p>
    <p v-if="error" class="err">{{ error }}</p>
    <p v-else-if="!rows.length" class="hint">还没有用户。</p>
    <table v-else>
      <thead>
        <tr>
          <th>ID</th>
          <th>用户名</th>
          <th class="num">提交</th>
          <th class="num">AC</th>
          <th class="num">通过率</th>
          <th>各语言</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="u in rows"
          :key="u.user_id"
          class="clickable"
          @click="goLog(u.user_id)"
        >
          <td>{{ u.user_id }}</td>
          <td>{{ u.username }}</td>
          <td class="num">{{ u.submissions }}</td>
          <td class="num">{{ u.accepted }}</td>
          <td class="num">{{ formatPassRate(u.accepted, u.submissions) }}</td>
          <td>
            <span v-if="!u.by_language.length">—</span>
            <span v-else class="lang-pills">
              <span v-for="lang in u.by_language" :key="lang.language" class="lang-pill">
                {{ languageShort(lang.language) }}
                {{ lang.accepted }}/{{ lang.submissions }}
                {{ formatPassRate(lang.accepted, lang.submissions) }}
              </span>
            </span>
          </td>
        </tr>
      </tbody>
    </table>
  </main>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { Admin, type UserStat } from "../api";
import { formatPassRate } from "../format";
import { languageShort } from "../languages";

const router = useRouter();
const rows = ref<UserStat[]>([]);
const error = ref("");

onMounted(async () => {
  try {
    rows.value = await Admin.userStats();
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  }
});

function goLog(userId: number) {
  void router.push(`/admin/data/users/${userId}`);
}
</script>
