import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";
import "katex/dist/katex.min.css";
import "./style.css";
import { applyTheme, readTheme } from "./theme";

applyTheme(readTheme());
createApp(App).use(router).mount("#app");
