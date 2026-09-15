<template>
  <div v-if="isLogin" class="auth-shell">
    <button class="ghost theme-fab" type="button" @click="onToggleTheme">
      {{ theme === "light" ? "深色背景" : "浅色背景" }}
    </button>
    <router-view />
  </div>
  <div v-else class="app-shell">
    <header class="topbar">
      <router-link class="brand" to="/">Leet Hub</router-link>
      <nav>
        <router-link to="/">题目</router-link>
        <template v-if="user?.is_admin">
          <router-link
            to="/admin/data/problems"
            active-class=""
            exact-active-class=""
            :class="{ 'router-link-active': onData }"
          >
            数据
          </router-link>
          <router-link
            to="/admin/bank/remote"
            active-class=""
            exact-active-class=""
            :class="{ 'router-link-active': onBank }"
          >
            题库
          </router-link>
          <router-link to="/admin/guide">手册</router-link>
        </template>
        <template v-else>
          <router-link to="/scores">成绩</router-link>
          <router-link to="/submissions">提交记录</router-link>
        </template>
      </nav>
      <span class="spacer" />
      <span v-if="user" class="user">{{ user.username }}</span>
      <button class="ghost" type="button" @click="onToggleTheme">
        {{ theme === "light" ? "深色" : "浅色" }}
      </button>
      <button class="ghost" @click="logout">退出</button>
    </header>
    <nav v-if="onData" class="subnav">
      <router-link to="/admin/data/problems">每题统计</router-link>
      <router-link to="/admin/data/users">用户总览</router-link>
    </nav>
    <nav v-if="onBank" class="subnav">
      <router-link to="/admin/bank/remote">远程同步</router-link>
      <router-link to="/admin/bank/local">本机导入</router-link>
      <router-link to="/admin/bank/files">按文件上传</router-link>
      <router-link to="/admin/bank/publish">发布</router-link>
    </nav>
    <router-view />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Auth, type User } from "./api";
import { readTheme, toggleTheme, type Theme } from "./theme";

const route = useRoute();
const router = useRouter();
const user = ref<User | null>(null);
const isLogin = computed(() => route.path === "/login");
const onAdmin = computed(() => Boolean(user.value?.is_admin) && route.path.startsWith("/admin"));
const onData = computed(() => onAdmin.value && route.path.startsWith("/admin/data"));
const onBank = computed(() => onAdmin.value && route.path.startsWith("/admin/bank"));
const theme = ref<Theme>(readTheme());

function onToggleTheme() {
  theme.value = toggleTheme();
}

async function refresh() {
  if (isLogin.value) {
    user.value = null;
    return;
  }
  try {
    user.value = await Auth.me();
  } catch {
    user.value = null;
  }
}

async function logout() {
  await Auth.logout();
  user.value = null;
  await router.push("/login");
}

onMounted(refresh);
watch(() => route.path, refresh);
</script>
