<template>
  <main class="page duel-page" v-if="duel">
    <p class="hint">
      <router-link :to="`/problems/${duel.slug}`">← {{ duel.title }}</router-link>
    </p>
    <h1>约战 {{ duel.code }}</h1>
    <p class="hint">同一台评测机、两位登录用户。开始后该题第一次 AC 先到者赢；都过则以耗时短者赢。不公开源码。</p>
    <p class="meta">
      状态 {{ statusLabel(duel.status) }}
      <span v-if="duel.winner_id"> · 胜者 {{ winnerName }}</span>
    </p>
    <div class="duel-grid">
      <article class="stat" :class="{ me: duel.is_host }">
        <div class="l">房主</div>
        <div class="n">{{ duel.host.username }}</div>
        <p class="hint">{{ playerLine(duel.host) }}</p>
      </article>
      <article class="stat" :class="{ me: duel.is_guest }">
        <div class="l">对手</div>
        <div class="n">{{ duel.guest ? duel.guest.username : "等待加入…" }}</div>
        <p class="hint">{{ duel.guest ? playerLine(duel.guest) : "把链接发给局域网另一人" }}</p>
      </article>
    </div>
    <p v-if="duel.status === 'waiting' && duel.is_host" class="hint">链接：{{ share }}</p>
    <p v-if="error" class="err">{{ error }}</p>
    <div class="row">
      <router-link class="primary" :to="`/problems/${duel.slug}`">去做这题</router-link>
      <button v-if="canJoin" class="ghost" type="button" @click="join">加入</button>
    </div>
  </main>
  <main class="page" v-else>
    <p class="hint">{{ error || "加载房间…" }}</p>
  </main>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { Auth, Duels, type Duel, type DuelPlayer, type User } from "../api";
import { languageLabel } from "../languages";

const route = useRoute();
const duel = ref<Duel | null>(null);
const me = ref<User | null>(null);
const error = ref("");
let timer = 0;

const share = computed(() => (typeof window !== "undefined" ? window.location.href : ""));
const winnerName = computed(() => {
  if (!duel.value?.winner_id) return "";
  if (duel.value.host.user_id === duel.value.winner_id) return duel.value.host.username;
  return duel.value.guest?.username || "";
});
const canJoin = computed(() => {
  const d = duel.value;
  if (!d || !me.value) return false;
  if (d.status !== "waiting") return false;
  return !d.is_host && !d.is_guest;
});

onMounted(async () => {
  me.value = await Auth.me();
  await refresh();
  timer = window.setInterval(() => {
    void refresh();
  }, 2000);
});

onBeforeUnmount(() => window.clearInterval(timer));

async function refresh() {
  const code = String(route.params.code || "");
  try {
    duel.value = await Duels.get(code);
    error.value = "";
  } catch (err) {
    error.value = err instanceof Error ? err.message : "加载失败";
  }
}

async function join() {
  const code = String(route.params.code || "");
  try {
    duel.value = await Duels.join(code);
    error.value = "";
  } catch (err) {
    error.value = err instanceof Error ? err.message : "无法加入";
  }
}

function statusLabel(s: string) {
  if (s === "waiting") return "等待对手";
  if (s === "live") return "进行中";
  if (s === "finished") return "已结束";
  if (s === "expired") return "已过期";
  return s;
}

function playerLine(p: DuelPlayer) {
  if (!p.ac) return "尚未 AC";
  const lang = p.language ? languageLabel(p.language) : "";
  return `已 AC ${p.time_ms ?? "?"} ms${lang ? " · " + lang : ""}`;
}
</script>
