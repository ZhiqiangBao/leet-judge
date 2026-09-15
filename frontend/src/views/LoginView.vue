<template>
  <div class="auth-page">
    <form class="card" @submit.prevent="submit">
      <h1>Leet Hub</h1>
      <p class="hint">家庭局域网评测。{{ mode === "login" ? "登录后开始做题。" : "这里注册的是普通用户。管理员须在评测机本机打开 127.0.0.1:8081。" }}</p>
      <label>用户名</label>
      <input v-model="username" autocomplete="username" required minlength="3" maxlength="32" />
      <label>密码</label>
      <input v-model="password" type="password" autocomplete="current-password" required minlength="4" />
      <p class="err">{{ error }}</p>
      <div class="row">
        <button class="primary" type="submit">{{ mode === "login" ? "登录" : "注册" }}</button>
        <button class="ghost" type="button" @click="mode = mode === 'login' ? 'register' : 'login'">
          {{ mode === "login" ? "没有账号？注册" : "已有账号？登录" }}
        </button>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Auth } from "../api";

const router = useRouter();
const route = useRoute();
const mode = ref<"login" | "register">("login");
const username = ref("");
const password = ref("");
const error = ref("");

async function submit() {
  error.value = "";
  try {
    if (mode.value === "login") await Auth.login(username.value, password.value);
    else await Auth.register(username.value, password.value);
    const next = typeof route.query.next === "string" ? route.query.next : "/";
    await router.push(next);
  } catch (err) {
    error.value = err instanceof Error ? err.message : "失败";
  }
}
</script>
