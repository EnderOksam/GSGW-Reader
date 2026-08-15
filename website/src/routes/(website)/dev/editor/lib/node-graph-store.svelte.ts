import {
  createNode,
  uid,
  type NodeEdge,
  type NodeType,
  type UderNode,
  LOOP_W,
  LOOP_H,
  LOOP_TOP,
} from "./nodes";

export const NODE_WIDTH = 220;
export const CANVAS_SIZE = 3000;

export const graph = $state({
  nodes: [createNode("start", 300, 200)] as UderNode[],
  edges: [] as NodeEdge[],
  selectedId: null as string | null,
  viewport: { x: 0, y: 0, scale: 1, width: 0, height: 0 },
});

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

export function clampChild(n: UderNode, loop: UderNode): UderNode {
  n.x = Math.max(loop.x + 12, Math.min(loop.x + LOOP_W - NODE_WIDTH - 12, n.x));
  n.y = Math.max(loop.y + LOOP_TOP + 12, Math.min(loop.y + LOOP_H - 92, n.y));
  return n;
}

export function loopAt(x: number, y: number, excludeId?: string): UderNode | null {
  for (const n of graph.nodes) {
    if (n.type !== "loop") continue;
    if (n.id === excludeId) continue;
    if (x >= n.x && x <= n.x + LOOP_W && y >= n.y && y <= n.y + LOOP_H) return n;
  }
  return null;
}

function isLocked(n: UderNode): boolean {
  return n.type === "loop_start" || n.type === "loop_check";
}

export function addNode(type: NodeType) {
  const v = graph.viewport;
  const cx = v.width > 0 ? (v.width / 2 - v.x) / v.scale : 200;
  const cy = v.height > 0 ? (v.height / 2 - v.y) / v.scale : 120;
  const spread = (graph.nodes.filter((x) => x.type === type).length % 6) * 30;

  if (type === "loop") {
    const loop = clampNode(createNode("loop", cx - LOOP_W / 2, cy - 40 + spread));
    const start = createNode("loop_start", loop.x + 24, loop.y + 60);
    const check = createNode("loop_check", loop.x + LOOP_W - NODE_WIDTH - 24, loop.y + 60);
    start.parentId = loop.id;
    check.parentId = loop.id;
    graph.nodes = [...graph.nodes, loop, start, check];
    graph.selectedId = loop.id;
    return;
  }

  let n = clampNode(createNode(type, cx - NODE_WIDTH / 2, cy - 40 + spread));
  const parent = loopAt(n.x + NODE_WIDTH / 2, n.y + 60);
  if (parent) {
    n.parentId = parent.id;
    n = clampChild(n, parent);
  }
  graph.nodes = [...graph.nodes, n];
  graph.selectedId = n.id;
}

export function deleteNode(id: string) {
  const n = graph.nodes.find((x) => x.id === id);
  if (!n) return;
  if (isLocked(n)) return;
  const doomed = new Set([id]);
  if (n.type === "loop") {
    for (const c of graph.nodes) if (c.parentId === id) doomed.add(c.id);
  }
  graph.nodes = graph.nodes.filter((x) => !doomed.has(x.id));
  graph.edges = graph.edges.filter((e) => !doomed.has(e.from) && !doomed.has(e.to));
  if (graph.selectedId && doomed.has(graph.selectedId)) graph.selectedId = null;
}

export function removeEdge(id: string) {
  graph.edges = graph.edges.filter((e) => e.id !== id);
}

export function addChoice(id: string) {
  graph.nodes = graph.nodes.map((n) =>
    n.id === id && (n.type === "choice" || n.type === "start") ? { ...n, choices: [...n.choices, ""] } : n
  );
}

export function removeChoice(id: string, i: number) {
  graph.nodes = graph.nodes.map((n) =>
    n.id === id && (n.type === "choice" || n.type === "start") ? { ...n, choices: n.choices.filter((_, j) => j !== i) } : n
  );
  graph.edges = graph.edges.filter((e) => !(e.from === id && e.fromPort === i));
  graph.edges = graph.edges.map((e) => (e.from === id && e.fromPort > i ? { ...e, fromPort: e.fromPort - 1 } : e));
}

export function settleNode(id: string) {
  const n = graph.nodes.find((x) => x.id === id);
  if (!n) return;
  if (isLocked(n) || n.type === "loop") return;
  const parent = loopAt(n.x + NODE_WIDTH / 2, n.y + 60);
  graph.nodes = graph.nodes.map((x) => {
    if (x.id !== id) return x;
    if (parent) {
      return { ...x, parentId: parent.id };
    }
    const copy = { ...x };
    delete copy.parentId;
    return copy;
  });
}
