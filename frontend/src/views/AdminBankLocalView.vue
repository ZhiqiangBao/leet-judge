<template>
  <main class="page admin-grid">
    <h1>本机导入</h1>
    <p class="hint">
      选一道题的文件夹，或选一个 zip（不用先解压），两种用一种即可。同名要换成这次的，勾选覆盖。操作见
      <router-link to="/admin/guide">手册</router-link>。
    </p>
    <p v-if="message" class="ac">{{ message }}</p>
    <p class="err">{{ error }}</p>
    <label class="row">
      <input v-model="overwrite" type="checkbox" />
      覆盖评测机上的同名题目
    </label>
    <label>上传 zip</label>
    <input ref="zipInput" type="file" accept=".zip,application/zip" @change="onZip" />
    <label>或选择本机题目文件夹</label>
    <input ref="dirInput" type="file" webkitdirectory multiple @change="onDir" />
  </main>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { Admin } from "../api";

const message = ref("");
const error = ref("");
const busy = ref(false);
const overwrite = ref(true);
const zipInput = ref<HTMLInputElement | null>(null);
const dirInput = ref<HTMLInputElement | null>(null);

function show(err: unknown) {
  error.value = err instanceof Error ? err.message : String(err);
  message.value = "";
}

function resetFiles() {
  if (zipInput.value) zipInput.value.value = "";
  if (dirInput.value) dirInput.value.value = "";
}

async function importForm(body: FormData) {
  if (busy.value) return;
  busy.value = true;
  try {
    error.value = "";
    body.set("overwrite", overwrite.value ? "true" : "false");
    const res = await Admin.importProblems(body);
    message.value = `已写入 ${res.slugs.join("、")}，评测机现有 ${res.count} 题。`;
    resetFiles();
  } catch (err) {
    show(err);
  } finally {
    busy.value = false;
  }
}

async function onZip(ev: Event) {
  const input = ev.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;
  const body = new FormData();
  body.append("file", file, file.name);
  await importForm(body);
}

async function onDir(ev: Event) {
  const input = ev.target as HTMLInputElement;
  const list = input.files;
  if (!list?.length) return;
  const body = new FormData();
  for (const file of Array.from(list)) {
    const rel = (file as File & { webkitRelativePath?: string }).webkitRelativePath || file.name;
    body.append("files", file, rel);
  }
  await importForm(body);
}
</script>
