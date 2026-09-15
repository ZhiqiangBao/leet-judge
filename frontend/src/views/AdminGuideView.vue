<template>
  <main class="page">
    <h1>手册</h1>
    <p v-if="error" class="err">{{ error }}</p>
    <article class="md" v-else v-html="html" />
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { Admin } from "../api";
import { renderMarkdown } from "../markdown";

const markdown = ref("");
const error = ref("");
const html = computed(() => (markdown.value ? renderMarkdown(markdown.value) : ""));

onMounted(async () => {
  try {
    const res = await Admin.guide();
    markdown.value = res.markdown;
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  }
});
</script>
