export interface MeUser {
  id: number;
  login: string;
  displayName: string;
  avatarUrl: string | null;
  provider: string;
  isLegacy: boolean;
  isAdmin: boolean;
  canPush: boolean;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
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

export function fetchMe(): Promise<{ user: MeUser | null }> {
  return request("/api/me");
}

export interface PushFile {
  name: string;
  content: string;
}

export interface PushResult {
  prUrl: string;
  branch: string;
}

export function pushChapters(payload: {
  book: string;
  translation: string;
  title: string;
  description: string;
  files: PushFile[];
}): Promise<PushResult> {
  return request("/api/dev/chapters/push", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function githubLoginUrl(scope: "repo"): string {
  return `/api/auth/github?returnTo=${encodeURIComponent("/dev/editor")}&scope=${scope}`;
}
