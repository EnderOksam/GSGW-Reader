export interface CommentAuthor {
  id: number;
  login: string;
  displayName: string;
  avatarUrl: string | null;
  provider: string;
  isLegacy: boolean;
}

export interface Reaction {
  emoji: string;
  count: number;
  mine: boolean;
  users: string[];
}

export interface Comment {
  id: number;
  chapter: string;
  parentId: number | null;
  body: string;
  isLegacy: boolean;
  createdAt: string;
  updatedAt: string | null;
  edited: boolean;
  author: CommentAuthor;
  reactions: Reaction[];
}

export interface Me {
  id: number;
  login: string;
  displayName: string;
  avatarUrl: string | null;
  provider: string;
  isLegacy: boolean;
  isAdmin: boolean;
}

const base = "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${base}${path}`, {
    credentials: "same-origin",
    headers: init?.body ? { "Content-Type": "application/json" } : undefined,
    ...init,
  });
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) {
    throw new Error((data && data.error) || `Request failed (${res.status})`);
  }
  return data as T;
}

export function getMe(): Promise<{ user: Me | null }> {
  return request("/api/me");
}

export interface CommentCounts {
  total: number;
  roots: number;
  replies: number;
}

export interface RootCommentsResponse extends CommentCounts {
  comments: Comment[];
  replyCounts: Record<string, number>;
}

export function getCommentCount(chapter: string): Promise<CommentCounts> {
  return request(`/api/comments?chapter=${encodeURIComponent(chapter)}&scope=count`);
}

export function getRootComments(chapter: string): Promise<RootCommentsResponse> {
  return request(`/api/comments?chapter=${encodeURIComponent(chapter)}&scope=roots`);
}

export function getReplies(id: number): Promise<{ comments: Comment[]; total: number }> {
  return request(`/api/comments/${id}/replies`);
}

export function postComment(chapter: string, body: string, parentId: number | null): Promise<{ comment: Comment }> {
  return request("/api/comments", {
    method: "POST",
    body: JSON.stringify({ chapter, body, parentId }),
  });
}

export function editComment(id: number, body: string): Promise<{ ok: boolean }> {
  return request(`/api/comments/${id}`, { method: "PATCH", body: JSON.stringify({ body }) });
}

export function deleteComment(id: number): Promise<{ ok: boolean }> {
  return request(`/api/comments/${id}`, { method: "DELETE" });
}

export function toggleReaction(id: number, emoji: string): Promise<{ reactions: Reaction[] }> {
  return request(`/api/comments/${id}/reactions/${encodeURIComponent(emoji)}`, { method: "POST" });
}

export function getChapterReactions(chapter: string): Promise<{ reactions: Reaction[] }> {
  return request(`/api/chapter-reactions?chapter=${encodeURIComponent(chapter)}`);
}

export function toggleChapterReaction(
  chapter: string,
  emoji: string
): Promise<{ reactions: Reaction[] }> {
  return request("/api/chapter-reactions", {
    method: "POST",
    body: JSON.stringify({ chapter, emoji }),
  });
}

export function getCounts(chapters: string[]): Promise<{ counts: Record<string, number> }> {
  return request(`/api/counts?chapters=${encodeURIComponent(chapters.join(","))}`);
}

export function loginUrl(returnTo: string): string {
  return `/api/auth/discord?returnTo=${encodeURIComponent(returnTo)}`;
}

export function githubLoginUrl(returnTo: string): string {
  return `/api/auth/github?returnTo=${encodeURIComponent(returnTo)}`;
}

export function logoutUrl(returnTo: string): string {
  return `/api/auth/logout?returnTo=${encodeURIComponent(returnTo)}`;
}
