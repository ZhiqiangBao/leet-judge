<template>
  <main class="page admin-grid">
    <h1>按文件上传</h1>
    <p class="hint">
      填写题目目录名。新题一次选齐四个文件；已有题可只改其中几份。失败看下方红字。需要空函数模板时，写入成功后再点「生成 starter」。见
      <router-link to="/admin/guide">手册</router-link>。
    </p>
    <p v-if="message" class="ac">{{ message }}</p>
    <p class="err">{{ error }}</p>
    <label>题目 slug（目录名）</label>
    <input v-model="slug" placeholder="two-sum" autocomplete="off" />
    <label>meta.yaml</label>
    <input type="file" accept=".yaml,.yml,text/yaml" @change="onPick('meta', $event)" />
    <label>statement.md</label>
    <input type="file" accept=".md,text/markdown" @change="onPick('statement', $event)" />
    <label>signature.yaml</label>
    <input type="file" accept=".yaml,.yml,text/yaml" @change="onPick('signature', $event)" />
    <label>tests.jsonl</label>
    <input type="file" accept=".jsonl,.json,text/plain" @change="onPick('tests', $event)" />
    <p class="hint" v-if="picked">已选：{{ picked }}</p>
    <div class="row">
      <button class="primary" type="button" :disabled="busy" @click="submit">写入目录</button>
      <button v-if="lastSlug" class="ghost" type="button" :disabled="busy" @click="makeStarters">
        为 {{ lastSlug }} 生成 starter
      </button>
    </div>
  </main>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { Admin } from "../api";

const slug = ref("");
const message = ref("");
const error = ref("");
const busy = ref(false);
const lastSlug = ref("");
const files = ref<{ meta?: File; statement?: File; signature?: File; tests?: File }>({});

const picked = computed(() => {
  const names: string[] = [];
  if (files.value.meta) names.push("meta.yaml");
  if (files.value.statement) names.push("statement.md");
  if (files.value.signature) names.push("signature.yaml");
  if (files.value.tests) names.push("tests.jsonl");
  return names.join("、");
});

function onPick(field: "meta" | "statement" | "signature" | "tests", ev: Event) {
  const input = ev.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) {
    const next = { ...files.value };
    delete next[field];
    files.value = next;
    return;
  }
  files.value = { ...files.value, [field]: file };
}

function show(err: unknown) {
  error.value = err instanceof Error ? err.message : String(err);
  message.value = "";
}

async function submit() {
  const name = slug.value.trim();
  if (!name) {
    error.value = "请填写 slug";
    return;
  }
  if (!picked.value) {
    error.value = "请至少选择一个文件";
    return;
  }
  const body = new FormData();
  body.set("slug", name);
  if (files.value.meta) body.set("meta", files.value.meta, "meta.yaml");
  if (files.value.statement) body.set("statement", files.value.statement, "statement.md");
  if (files.value.signature) body.set("signature", files.value.signature, "signature.yaml");
  if (files.value.tests) body.set("tests", files.value.tests, "tests.jsonl");
  busy.value = true;
  try {
    error.value = "";
    const res = await Admin.mergeFiles(body);
    lastSlug.value = res.slug;
    message.value = `已写入 problems/${res.slug}/，评测机现有 ${res.count} 题。需要模板再点「生成 starter」。`;
  } catch (err) {
    show(err);
  } finally {
    busy.value = false;
  }
}

async function makeStarters() {
  const name = lastSlug.value.trim();
  if (!name) return;
  busy.value = true;
  try {
    error.value = "";
    const res = await Admin.writeStarters(name);
    const langs = res.wrote.length ? res.wrote.join("、") : "无";
    const extra = res.skipped.length ? ` 跳过：${res.skipped.join("、")}。` : "";
    message.value = `已生成 starter：${langs}。${extra}`;
  } catch (err) {
    show(err);
  } finally {
    busy.value = false;
  }
}
</script>
