<template>
  <main class="page admin-grid">
    <h1>远程同步</h1>
    <p class="hint">
      本机先把题目推到 GitHub，再点「从 Git 同步」。只改了评测机磁盘上的题、没有推送：点「只重新加载磁盘」。见
      <router-link to="/admin/guide">手册</router-link>。
    </p>
    <p v-if="message" class="ac">{{ message }}</p>
    <p class="err">{{ error }}</p>
    <div class="row">
      <button class="primary" type="button" :disabled="busy" @click="syncGit">从 Git 同步</button>
      <button class="ghost" type="button" :disabled="busy" @click="reload">只重新加载磁盘</button>
    </div>
  </main>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { Admin } from "../api";

const message = ref("");
const error = ref("");
const busy = ref(false);

function show(err: unknown) {
  error.value = err instanceof Error ? err.message : String(err);
  message.value = "";
}

async function syncGit() {
  busy.value = true;
  try {
    error.value = "";
    const res = await Admin.syncGit();
    if (res.unchanged) {
      message.value = `远程没有新提交。评测机现有 ${res.count} 题。`;
    } else {
      const slugs = res.slugs.length ? res.slugs.join("、") : "无新题目目录";
      const extra = res.needs_restart ? " 代码也有变更，需要在评测机上重启 local-leet。" : "";
      message.value = `已拉取并加载 ${res.count} 题。本次题目：${slugs}。${extra}`;
    }
  } catch (err) {
    show(err);
  } finally {
    busy.value = false;
  }
}

async function reload() {
  try {
    error.value = "";
    const res = await Admin.reload();
    message.value = `已加载 ${res.count} 题`;
  } catch (err) {
    show(err);
  }
}
</script>
