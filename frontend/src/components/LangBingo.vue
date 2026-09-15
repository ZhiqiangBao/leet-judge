<template>
  <div class="bingo" :class="{ compact }" v-if="langs.length">
    <span
      v-for="id in langs"
      :key="id"
      class="bingo-dot"
      :class="{ on: acSet.has(id) }"
      :title="titleFor(id)"
    >
      {{ languageShort(id) }}
    </span>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { languageLabel, languageShort } from "../languages";

const props = defineProps<{
  languages: string[];
  ac: string[];
  compact?: boolean;
}>();

const langs = computed(() => props.languages);
const acSet = computed(() => new Set(props.ac));

function titleFor(id: string) {
  return acSet.value.has(id) ? `${languageLabel(id)} 已通过` : `${languageLabel(id)} 未通过`;
}
</script>
