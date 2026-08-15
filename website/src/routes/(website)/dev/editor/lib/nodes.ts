export const NODE_TYPES = [
  "start",
  "story",
  "choice",
  "condition",
  "ending",
  "loop",
  "resource",
  "loop_start",
  "loop_check",
] as const;
export type NodeType = (typeof NODE_TYPES)[number];

interface Base {
  id: string;
  type: NodeType;
  x: number;
  y: number;
  parentId?: string;
}

export interface StartNode extends Base {
  type: "start";
  title: string;
  text: string;
  choices: string[];
}

export interface StoryNode extends Base {
  type: "story";
  title: string;
  text: string;
}

export interface ChoiceNode extends Base {
  type: "choice";
  title: string;
  prompt: string;
  choices: string[];
}

export const CONDITION_OPERATORS = [">", "<", ">=", "<=", "==", "!="] as const;
export type NodeOperator = (typeof CONDITION_OPERATORS)[number];

export const MUTATION_OPERATORS = ["add"] as const;
export type ConditionOperator = NodeOperator | (typeof MUTATION_OPERATORS)[number];

export const OPERATOR_LABELS: Record<ConditionOperator, string> = {
  ">": "greater than",
  "<": "less than",
  ">=": "greater than or equal to",
  "<=": "less than or equal to",
  "==": "equal to",
  "!=": "not equal to",
  add: "add to",
};

export interface ConditionNode extends Base {
  type: "condition";
  title: string;
  resource: string;
  operator: ConditionOperator;
  value: number;
  silent: boolean;
}

export interface EndingNode extends Base {
  type: "ending";
  title: string;
  text: string;
}

export interface LoopNode extends Base {
  type: "loop";
  title: string;
  note: string;
  loops: number;
  condition: { resource: string; operator: NodeOperator; value: number };
}

export interface LoopStartNode extends Base {
  type: "loop_start";
  title: string;
}

export interface LoopCheckNode extends Base {
  type: "loop_check";
  title: string;
}

export interface ResourceNode extends Base {
  type: "resource";
  title: string;
  initial: number;
}

export type UderNode =
  | StartNode
  | StoryNode
  | ChoiceNode
  | ConditionNode
  | EndingNode
  | LoopNode
  | ResourceNode
  | LoopStartNode
  | LoopCheckNode;

export interface NodeEdge {
  id: string;
  from: string;
  fromPort: number;
  to: string;
  toSide?: "left" | "right";
}

export const NODE_LABELS: Record<NodeType, string> = {
  start: "Start",
  story: "Story",
  choice: "Choice",
  condition: "Condition",
  ending: "Ending",
  loop: "Loop",
  resource: "Resource",
  loop_start: "Loop Start",
  loop_check: "Loop Check",
};

export const NODE_ICONS: Record<NodeType, string> = {
  start: "mdi:play",
  story: "mdi:file-document-outline",
  choice: "mdi:source-branch",
  condition: "mdi:filter-variant",
  ending: "mdi:flag-outline",
  loop: "mdi:refresh",
  resource: "mdi:cube-outline",
  loop_start: "mdi:play-circle-outline",
  loop_check: "mdi:check-decagram-outline",
};

export const NODE_COLORS: Record<NodeType, string> = {
  start: "#a3e635",
  story: "#34d399",
  choice: "#fbbf24",
  condition: "#22d3ee",
  ending: "#a78bfa",
  loop: "#fb923c",
  resource: "#f87171",
  loop_start: "#fb923c",
  loop_check: "#f59e0b",
};

export const LOOP_W = 560;
export const LOOP_H = 520;
export const LOOP_TOP = 40;

export function uid(): string {
  return Math.random().toString(36).slice(2, 10) + Date.now().toString(36).slice(-4);
}

export function createNode(type: NodeType, x = 100, y = 100): UderNode {
  const base = { id: uid(), x, y };
  switch (type) {
    case "start":
      return { ...base, type: "start", title: "Start", text: "", choices: [""] };
    case "story":
      return { ...base, type: "story", title: "Story", text: "" };
    case "choice":
      return { ...base, type: "choice", title: "Choice", prompt: "", choices: ["", ""] };
    case "condition":
      return {
        ...base,
        type: "condition",
        title: "Condition",
        resource: "",
        operator: ">=" as ConditionOperator,
        value: 1,
        silent: false,
      };
    case "ending":
      return { ...base, type: "ending", title: "Ending", text: "" };
    case "loop":
      return {
        ...base,
        type: "loop",
        title: "Loop",
        note: "",
        loops: 3,
        condition: { resource: "", operator: ">=" as NodeOperator, value: 1 },
      };
    case "resource":
      return { ...base, type: "resource", title: "Resource", initial: 0 };
    case "loop_start":
      return { ...base, type: "loop_start", title: "Loop Start" };
    case "loop_check":
      return { ...base, type: "loop_check", title: "Loop Check" };
  }
}

export function nodeOutputs(n: UderNode): number {
  if (n.type === "choice" || n.type === "start") return Math.max(1, n.choices.length);
  if (n.type === "ending" || n.type === "resource" || n.type === "loop") return 0;
  return 1;
}

export function nodeTitle(n: UderNode): string {
  return n.title || NODE_LABELS[n.type];
}
