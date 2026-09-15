<template>
  <main class="page">
    <h1>我的提交</h1>
    <p class="hint">仅正式提交。名次见顶栏「成绩」。测试运行不会出现在此。</p>
    <table>
      <thead>
        <tr>
          <th>ID</th>
          <th>题目</th>
          <th>语言</th>
          <th>结果</th>
          <th>耗时</th>
          <th>时间</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="s in rows" :key="s.id">
          <td>{{ s.id }}</td>
          <td>
            <router-link :to="`/problems/${s.problem_slug}`">{{ s.problem_slug }}</router-link>
          </td>
          <td>{{ languageLabel(s.language) }}</td>
          <td :class="(s.verdict || s.status).toLowerCase()">{{ s.verdict || s.status }}</td>
          <td>{{ s.time_ms ?? "—" }}</td>
          <td>{{ s.created_at }}</td>
        </tr>
      </tbody>
    </table>
  </main>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { Submissions, type Submission } from "../api";
import { languageLabel } from "../languages";

const rows = ref<Submission[]>([]);

onMounted(async () => {
  rows.value = await Submissions.list();
});
</script>
