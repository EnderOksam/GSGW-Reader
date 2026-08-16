import {
  createNode,
  uid,
  type NodeEdge,
  type NodeType,
  type UderNode,
} from "./nodes";
import {
  loadInteractiveCache,
  saveInteractiveCache,
} from "./uder-cache";

export const NODE_WIDTH = 220;
export const CANVAS_SIZE = 3000;

let initialNodes: UderNode[];
let initialEdges: NodeEdge[];
if (typeof window !== "undefined") {
  try {
    const cached = loadInteractiveCache();
    initialNodes = (cached?.nodes as UderNode[]) ?? [createNode("start", 300, 200)];
    initialEdges = (cached?.edges as NodeEdge[]) ?? [];
  } catch {
    initialNodes = [createNode("start", 300, 200)];
    initialEdges = [];
  }
} else {
  initialNodes = [createNode("start", 300, 200)];
  initialEdges = [];
}

export const graph = $state({
  nodes: initialNodes,
  edges: initialEdges,
  selectedId: null as string | null,
  viewport: { x: 0, y: 0, scale: 1, width: 0, height: 0 },
});

function persistCache() {
  if (typeof window !== "undefined") {
    saveInteractiveCache({ nodes: graph.nodes, edges: graph.edges });
  }
}

interface GraphSnapshot {
  nodes: UderNode[];
  edges: NodeEdge[];
}

let undoStack = $state<GraphSnapshot[]>([]);
let redoStack = $state<GraphSnapshot[]>([]);
const HISTORY_LIMIT = 100;

export function canUndo() {
  return undoStack.length > 0;
}

export function canRedo() {
  return redoStack.length > 0;
}

function snapshotState(): GraphSnapshot {
  return $state.snapshot({ nodes: graph.nodes, edges: graph.edges });
}

function pushUndo() {
  undoStack = [...undoStack, snapshotState()].slice(-HISTORY_LIMIT);
  redoStack = [];
}

export function captureHistory() {
  pushUndo();
}

export function undo() {
  const snap = undoStack.pop();
  if (!snap) return;
  redoStack = [...redoStack, snapshotState()];
  graph.nodes = snap.nodes;
  graph.edges = snap.edges;
  graph.selectedId = null;
  persistCache();
}

export function redo() {
  const snap = redoStack.pop();
  if (!snap) return;
  undoStack = [...undoStack, snapshotState()];
  graph.nodes = snap.nodes;
  graph.edges = snap.edges;
  graph.selectedId = null;
  persistCache();
}

export function addEdge(from: string, fromPort: number, to: string, toSide: "left" | "right") {
  if (graph.edges.some((e) => e.from === from && e.fromPort === fromPort && e.to === to)) return;
  pushUndo();
  graph.edges = [...graph.edges, { id: uid(), from, fromPort, to, toSide }];
  persistCache();
}

export function setViewport(v: { x: number; y: number; scale: number; width: number; height: number }) {
  graph.viewport = v;
}

export function setSelected(id: string | null) {
  graph.selectedId = id;
}

export function clampNode(n: UderNode): UderNode {
  n.x = Math.max(0, Math.min(CANVAS_SIZE - NODE_WIDTH, n.x));
  n.y = Math.max(0, Math.min(CANVAS_SIZE - 200, n.y));
  return n;
}

function isLocked(n: UderNode): boolean {
  return false;
}

export function addNode(type: NodeType) {
  pushUndo();
  const v = graph.viewport;
  const cx = v.width > 0 ? (v.width / 2 - v.x) / v.scale : 200;
  const cy = v.height > 0 ? (v.height / 2 - v.y) / v.scale : 120;
  const spread = (graph.nodes.filter((x) => x.type === type).length % 6) * 30;

  if (type === "loop_start" || type === "loop_check") {
    const pairId = uid();
    const start = clampNode(createNode("loop_start", cx - NODE_WIDTH - 10, cy - 40 + spread));
    const check = clampNode(createNode("loop_check", cx + 10, cy - 40 + spread));
    start.parentId = pairId;
    check.parentId = pairId;
    graph.nodes = [...graph.nodes, start, check];
    graph.selectedId = check.id;
    persistCache();
    return;
  }

  let n = clampNode(createNode(type, cx - NODE_WIDTH / 2, cy - 40 + spread));
  graph.nodes = [...graph.nodes, n];
  graph.selectedId = n.id;
  persistCache();
}

export function deleteNode(id: string) {
  pushUndo();
  const n = graph.nodes.find((x) => x.id === id);
  if (!n) return;
  if (isLocked(n)) return;
  const doomed = new Set([id]);
  if (n.type === "loop_start" || n.type === "loop_check") {
    const pairId = n.parentId;
    if (pairId) {
      const pair = graph.nodes.find((m) => m.id === pairId && m.parentId === pairId);
      if (pair) doomed.add(pair.id);
    }
  }
  graph.nodes = graph.nodes.filter((x) => !doomed.has(x.id));
  graph.edges = graph.edges.filter((e) => !doomed.has(e.from) && !doomed.has(e.to));
  if (graph.selectedId && doomed.has(graph.selectedId)) graph.selectedId = null;
  persistCache();
}

export function removeEdge(id: string) {
  pushUndo();
  graph.edges = graph.edges.filter((e) => e.id !== id);
  persistCache();
}

export function addChoice(id: string) {
  pushUndo();
  graph.nodes = graph.nodes.map((n) =>
    n.id === id && (n.type === "choice" || n.type === "start") ? { ...n, choices: [...n.choices, ""] } : n
  );
  persistCache();
}

export function removeChoice(id: string, i: number) {
  pushUndo();
  graph.nodes = graph.nodes.map((n) =>
    n.id === id && (n.type === "choice" || n.type === "start") ? { ...n, choices: n.choices.filter((_, j) => j !== i) } : n
  );
  graph.edges = graph.edges.filter((e) => !(e.from === id && e.fromPort === i));
  graph.edges = graph.edges.map((e) => (e.from === id && e.fromPort > i ? { ...e, fromPort: e.fromPort - 1 } : e));
  persistCache();
}

export function settleNode(id: string) {
  const n = graph.nodes.find((x) => x.id === id);
  if (!n) return;
  if (isLocked(n)) return;
}

export function resetGraphCache() {
  graph.nodes = [createNode("start", 300, 200)];
  graph.edges = [];
  graph.selectedId = null;
  undoStack = [];
  redoStack = [];
  persistCache();
}
