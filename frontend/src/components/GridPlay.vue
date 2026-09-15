<template>
  <section v-if="boards.length" class="grid-play">
    <div v-for="(board, i) in boards" :key="i" class="grid-case">
      <p class="muted">
        示例 {{ i + 1 }}
        <span v-if="board.k != null"> · k = {{ board.k }}</span>
        <span v-if="board.expected !== undefined"> · 期望 {{ JSON.stringify(board.expected) }}</span>
      </p>
      <p v-if="board.tooBig" class="hint">示例过大，只显示左上角 24×24。</p>
      <div class="grid-board" :style="gridStyle(board)">
        <span
          v-for="(cell, idx) in board.cells"
          :key="idx"
          class="grid-cell"
          :class="cellClass(i, cell)"
          :title="String(cell.raw)"
        >
          {{ cell.label }}
        </span>
      </div>
      <button
        v-if="board.playable && board.k != null"
        class="ghost"
        type="button"
        @click="togglePlay(i)"
      >
        {{ playing === i ? "暂停" : "按秒播放" }} · 第 {{ ticks[i] ?? 0 }} 秒
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onBeforeUnmount, reactive, ref, watch } from "vue";
import type { PublicTest, Signature } from "../api";

const MAX = 24;

type Cell = { raw: string | number; label: string; row: number; col: number };
type Board = {
  rows: number;
  cols: number;
  cells: Cell[];
  tooBig: boolean;
  playable: boolean;
  k: number | null;
  expected: unknown;
  base: number[][];
};

const props = defineProps<{
  signature: Signature;
  tests: PublicTest[];
}>();

const boards = ref<Board[]>([]);
const ticks = reactive<Record<number, number>>({});
const playing = ref<number | null>(null);
let timer = 0;

watch(
  () => [props.signature, props.tests],
  () => {
    stop();
    boards.value = buildBoards(props.signature, props.tests);
    for (let i = 0; i < boards.value.length; i++) ticks[i] = 0;
  },
  { immediate: true },
);

onBeforeUnmount(stop);

function stop() {
  window.clearInterval(timer);
  playing.value = null;
}

function togglePlay(i: number) {
  if (playing.value === i) {
    stop();
    return;
  }
  stop();
  playing.value = i;
  const board = boards.value[i];
  ticks[i] = 0;
  timer = window.setInterval(() => {
    const k = board.k ?? 0;
    const next = (ticks[i] ?? 0) + 1;
    ticks[i] = next > k ? 0 : next;
  }, 700);
}

function gridStyle(board: Board) {
  return {
    gridTemplateColumns: `repeat(${board.cols}, 22px)`,
  };
}

function cellClass(boardIndex: number, cell: Cell) {
  const board = boards.value[boardIndex];
  const t = ticks[boardIndex] ?? 0;
  if (board.playable && board.base.length) {
    const { state, fresh } = fireAt(board.base, t);
    const v = state[cell.row]?.[cell.col];
    const isFresh = fresh[cell.row]?.[cell.col];
    return {
      wall: v === 1,
      fire: v === 2 && !isFresh,
      fresh: !!isFresh,
      empty: v === 0,
    };
  }
  const raw = cell.raw;
  if (raw === 1 || raw === "#") return { wall: true };
  if (raw === 2 || raw === "2") return { fire: true };
  if (raw === 0 || raw === ".") return { empty: true };
  return { other: true };
}

function buildBoards(sig: Signature, tests: PublicTest[]): Board[] {
  const gridIdx = sig.params.findIndex(
    (p) => p.type === "List[List[int]]" || p.type === "List[str]",
  );
  if (gridIdx < 0) return [];
  const kIdx = sig.params.findIndex((p, i) => i !== gridIdx && p.type === "int");
  const out: Board[] = [];
  for (const test of tests) {
    const raw = test.args[gridIdx];
    const matrix = asMatrix(raw);
    if (!matrix) continue;
    const fullR = matrix.length;
    const fullC = Math.max(0, ...matrix.map((row) => row.length));
    const tooBig = fullR > MAX || fullC > MAX;
    const view = matrix.slice(0, MAX).map((row) => row.slice(0, MAX));
    const rows = view.length;
    const cols = Math.max(0, ...view.map((row) => row.length));
    const cells: Cell[] = [];
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const v = view[r][c] ?? "";
        cells.push({ raw: v, label: String(v), row: r, col: c });
      }
    }
    const numeric = view.every((row) => row.every((v) => v === 0 || v === 1 || v === 2));
    const k = kIdx >= 0 && typeof test.args[kIdx] === "number" ? Number(test.args[kIdx]) : null;
    const base = numeric ? (view as number[][]) : [];
    out.push({
      rows,
      cols,
      cells,
      tooBig,
      playable: numeric && k != null && k >= 0 && k <= 400,
      k,
      expected: test.expected,
      base,
    });
  }
  return out;
}

function asMatrix(raw: unknown): (number | string)[][] | null {
  if (!Array.isArray(raw) || !raw.length) return null;
  if (typeof raw[0] === "string") {
    return (raw as string[]).map((s) => s.split(""));
  }
  if (Array.isArray(raw[0])) {
    return raw as (number | string)[][];
  }
  return null;
}

function fireAt(initial: number[][], t: number): { state: number[][]; fresh: boolean[][] } {
  const rows = initial.length;
  const cols = initial[0]?.length ?? 0;
  let state = initial.map((row) => row.slice());
  let fresh = state.map((row) => row.map((v) => v === 2));
  const dirs = [
    [1, 0],
    [-1, 0],
    [0, 1],
    [0, -1],
  ];
  for (let step = 1; step <= t; step++) {
    const next = state.map((row) => row.slice());
    const nxtFresh = state.map((row) => row.map(() => false));
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        if (state[r][c] !== 0) continue;
        const hit = dirs.some(([dr, dc]) => {
          const nr = r + dr;
          const nc = c + dc;
          return nr >= 0 && nc >= 0 && nr < rows && nc < cols && state[nr][nc] === 2;
        });
        if (hit) {
          next[r][c] = 2;
          nxtFresh[r][c] = true;
        }
      }
    }
    state = next;
    fresh = nxtFresh;
  }
  return { state, fresh };
}
</script>
