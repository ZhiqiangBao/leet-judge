<template>
  <div ref="root" class="editor-wrap"></div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import * as monaco from "monaco-editor";
import { readTheme, THEME_EVENT } from "../theme";
import editorWorker from "monaco-editor/esm/vs/editor/editor.worker?worker";
import jsonWorker from "monaco-editor/esm/vs/language/json/json.worker?worker";
import tsWorker from "monaco-editor/esm/vs/language/typescript/ts.worker?worker";

self.MonacoEnvironment = {
  getWorker(_workerId: string, label: string) {
    if (label === "json") return new jsonWorker();
    if (label === "javascript" || label === "typescript") return new tsWorker();
    return new editorWorker();
  },
};

const props = defineProps<{ modelValue: string; language: string }>();
const emit = defineEmits<{ "update:modelValue": [string] }>();
const root = ref<HTMLDivElement | null>(null);
let editor: monaco.editor.IStandaloneCodeEditor | null = null;
const models = new Map<string, monaco.editor.ITextModel>();
let applying = false;

const monacoLang: Record<string, string> = {
  python3: "python",
  c: "c",
  cpp17: "cpp",
  javascript: "javascript",
  typescript: "typescript",
  go: "go",
  rust: "rust",
  zig: "plaintext",
};

function configurePythonIndent() {
  monaco.languages.setLanguageConfiguration("python", {
    comments: {
      lineComment: "#",
      blockComment: ["'''", "'''"],
    },
    brackets: [
      ["{", "}"],
      ["[", "]"],
      ["(", ")"],
    ],
    autoClosingPairs: [
      { open: "{", close: "}" },
      { open: "[", close: "]" },
      { open: "(", close: ")" },
      { open: '"', close: '"', notIn: ["string"] },
      { open: "'", close: "'", notIn: ["string", "comment"] },
    ],
    surroundingPairs: [
      { open: "{", close: "}" },
      { open: "[", close: "]" },
      { open: "(", close: ")" },
      { open: '"', close: '"' },
      { open: "'", close: "'" },
    ],
    onEnterRules: [
      {
        beforeText:
          /^\s*(?:def|class|for|if|elif|else|while|try|with|finally|except|async|match|case).*?:\s*(?:#.*)?$/,
        action: { indentAction: monaco.languages.IndentAction.Indent },
      },
      {
        beforeText: /^\s*(?:break|continue|raise|return|pass)\b.*$/,
        action: { indentAction: monaco.languages.IndentAction.Outdent },
      },
    ],
    indentationRules: {
      increaseIndentPattern:
        /^\s*(?:class|def|elif|else|except|finally|for|if|try|with|while|async\s+(?:def|for|with)|match|case)\b.*:\s*(?:#.*)?$/,
      decreaseIndentPattern: /^\s*(?:elif|else|except|finally)\b.*/,
    },
    folding: { offSide: true },
  });
}

function monacoTheme() {
  return readTheme() === "light" ? "vs" : "vs-dark";
}

function onThemeChange() {
  monaco.editor.setTheme(monacoTheme());
}

function modelFor(language: string, value: string) {
  let model = models.get(language);
  if (!model || model.isDisposed()) {
    model = monaco.editor.createModel(value, monacoLang[language] || "plaintext");
    models.set(language, model);
  }
  return model;
}

onMounted(() => {
  if (!root.value) return;
  configurePythonIndent();
  editor = monaco.editor.create(root.value, {
    model: modelFor(props.language, props.modelValue),
    theme: monacoTheme(),
    automaticLayout: true,
    minimap: { enabled: false },
    fontSize: 14,
    scrollBeyondLastLine: false,
    tabSize: 4,
    insertSpaces: true,
    detectIndentation: false,
    autoIndent: "full",
  });
  editor.onDidChangeModelContent(() => {
    if (applying) return;
    emit("update:modelValue", editor?.getValue() || "");
  });
  window.addEventListener(THEME_EVENT, onThemeChange);
});

watch(
  () => [props.language, props.modelValue] as const,
  ([language, value]) => {
    if (!editor) return;
    const model = modelFor(language, value);
    applying = true;
    if (editor.getModel() !== model) editor.setModel(model);
    if (value !== model.getValue()) model.setValue(value);
    applying = false;
  },
);

onBeforeUnmount(() => {
  window.removeEventListener(THEME_EVENT, onThemeChange);
  editor?.dispose();
  for (const model of models.values()) model.dispose();
  models.clear();
});
</script>
