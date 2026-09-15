<template>
  <main class="page admin-grid">
    <h1>发布题目</h1>
    <p class="hint">
      导入后默认不公开。只有点「发布」之后，普通登录才能在题目列表里看到并提交。你自己做题走顶栏「题目」，那里能看见全部导入题（含未发布）。
    </p>
    <p v-if="message" class="ac">{{ message }}</p>
    <p class="err">{{ error }}</p>
    <table v-if="rows.length">
      <thead>
        <tr>
          <th>题目</th>
          <th>难度</th>
          <th>状态</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="row.slug">
          <td>
            <router-link class="title-link" :to="`/problems/${row.slug}`">{{ row.title }}</router-link>
            <div class="muted">{{ row.slug }}</div>
          </td>
          <td :class="row.difficulty">{{ row.difficulty }}</td>
          <td>{{ row.published ? "已发布" : "未发布" }}</td>
          <td>
            <button class="ghost" type="button" :disabled="busy === row.slug" @click="toggle(row)">
              {{ row.published ? "撤回" : "发布" }}
            </button>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-else class="hint">还没有导入题目。先到「本机导入」上传 zip。</p>
  </main>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { Admin, type CatalogItem } from "../api";

const rows = ref<CatalogItem[]>([]);
const message = ref("");
const error = ref("");
const busy = ref("");

async function load() {
  error.value = "";
  rows.value = await Admin.catalog();
}

async function toggle(row: CatalogItem) {
  busy.value = row.slug;
  try {
    const res = await Admin.publish(row.slug, !row.published);
    row.published = res.published;
    message.value = res.published ? `已发布 ${row.title}` : `已撤回 ${row.title}`;
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
    message.value = "";
  } finally {
    busy.value = "";
  }
}

onMounted(async () => {
  try {
    await load();
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  }
});
</script>
