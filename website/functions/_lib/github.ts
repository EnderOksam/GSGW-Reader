import type { Env } from "./db";

const AUTHORIZE = "https://github.com/login/oauth/authorize";
const TOKEN = "https://github.com/login/oauth/access_token";
const API = "https://api.github.com";

const USER_AGENT = "GSGW-Reader";

export const UPSTREAM_OWNER = "EnderOksam";
export const UPSTREAM_REPO = "GSGW-Reader";

export type OAuthScope = "read:user" | "repo";

export function authorizeUrl(env: Env, redirectUri: string, state: string, scope: OAuthScope = "read:user"): string {
  const params = new URLSearchParams({
    client_id: env.GITHUB_CLIENT_ID,
    redirect_uri: redirectUri,
    scope,
    state,
  });
  return `${AUTHORIZE}?${params.toString()}`;
}

export interface TokenExchange {
  accessToken: string;
  scopes: string;
}

export async function exchangeCode(env: Env, code: string, redirectUri: string): Promise<TokenExchange> {
  const body = new URLSearchParams({
    client_id: env.GITHUB_CLIENT_ID,
    client_secret: env.GITHUB_CLIENT_SECRET,
    code,
    redirect_uri: redirectUri,
  });
  const res = await fetch(TOKEN, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      Accept: "application/json",
    },
    body: body.toString(),
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`GitHub token exchange failed (${res.status}): ${detail}`);
  }
  const data = (await res.json()) as { access_token?: string; scope?: string; error?: string };
  if (!data.access_token) {
    throw new Error(`GitHub token exchange returned no access_token: ${data.error ?? ""}`);
  }
  return { accessToken: data.access_token, scopes: data.scope ?? "" };
}

export interface GitHubUser {
  id: number;
  login: string;
  name?: string | null;
  avatar_url?: string | null;
}

export async function fetchUser(accessToken: string): Promise<GitHubUser> {
  const res = await fetch(`${API}/user`, {
    headers: {
      Authorization: `Bearer ${accessToken}`,
      Accept: "application/vnd.github+json",
      "User-Agent": USER_AGENT,
    },
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`GitHub user fetch failed (${res.status}): ${detail}`);
  }
  return (await res.json()) as GitHubUser;
}

export function avatarUrl(user: GitHubUser): string {
  return user.avatar_url || `https://github.com/${user.login}.png`;
}

export function displayName(user: GitHubUser): string {
  return user.name || user.login;
}

export class GitHubActionError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function gitRequest(token: string, method: string, path: string, body?: unknown): Promise<Response> {
  return fetch(`${API}${path}`, {
    method,
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": USER_AGENT,
      ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}

function extractMessage(detail: string): string {
  try {
    const parsed = JSON.parse(detail) as { message?: string };
    if (parsed?.message) return parsed.message;
  } catch {}
  return detail.slice(0, 200);
}

async function gitCall<T>(
  token: string,
  method: string,
  path: string,
  body?: unknown,
  ok: number[] = [200, 201, 202]
): Promise<T> {
  const res = await gitRequest(token, method, path, body);
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new GitHubActionError(extractMessage(detail), res.status);
  }
  return (await res.json()) as T;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function ensureFork(token: string, login: string): Promise<void> {
  const existing = await gitRequest(token, "GET", `/repos/${login}/${UPSTREAM_REPO}`);
  if (existing.status === 200) return;
  if (existing.status !== 404) {
    const detail = await existing.text().catch(() => "");
    throw new GitHubActionError(extractMessage(detail), existing.status);
  }
  await gitCall(token, "POST", `/repos/${UPSTREAM_OWNER}/${UPSTREAM_REPO}/forks`, {});
  for (let attempt = 0; attempt < 5; attempt++) {
    await sleep(1200);
    const check = await gitRequest(token, "GET", `/repos/${login}/${UPSTREAM_REPO}`);
    if (check.status === 200) return;
  }
  throw new GitHubActionError("Fork creation timed out, try again in a moment", 504);
}

export interface PushFile {
  path: string;
  content: string;
}

export interface ProposeChangesInput {
  token: string;
  login: string;
  displayName: string;
  files: PushFile[];
  commitMessage: string;
  prTitle: string;
  prBody: string;
}

export interface ProposeChangesResult {
  prUrl: string;
  branch: string;
}

export async function proposeChapterChanges(input: ProposeChangesInput): Promise<ProposeChangesResult> {
  const { token, login, files } = input;
  const fork = `${login}/${UPSTREAM_REPO}`;

  await ensureFork(token, login);

  const upstreamRef = await gitCall<{ object: { sha: string } }>(
    token,
    "GET",
    `/repos/${UPSTREAM_OWNER}/${UPSTREAM_REPO}/git/ref/heads/main`
  );
  const baseSha = upstreamRef.object.sha;

  const treeEntries: { path: string; mode: string; type: string; sha: string }[] = [];
  for (const file of files) {
    const blob = await gitCall<{ sha: string }>(token, "POST", `/repos/${fork}/git/blobs`, {
      content: file.content,
      encoding: "utf-8",
    });
    treeEntries.push({ path: file.path, mode: "100644", type: "blob", sha: blob.sha });
  }

  const tree = await gitCall<{ sha: string }>(token, "POST", `/repos/${fork}/git/trees`, {
    base_tree: baseSha,
    tree: treeEntries,
  });

  const commit = await gitCall<{ sha: string }>(token, "POST", `/repos/${fork}/git/commits`, {
    message: input.commitMessage,
    tree: tree.sha,
    parents: [baseSha],
    author: {
      name: input.displayName || login,
      email: `${login}@users.noreply.github.com`,
    },
  });

  const branch = `edit/${login}/${Date.now()}`;
  await gitCall(token, "POST", `/repos/${fork}/git/refs`, {
    ref: `refs/heads/${branch}`,
    sha: commit.sha,
  });

  const pr = await gitCall<{ html_url: string }>(token, "POST", `/repos/${UPSTREAM_OWNER}/${UPSTREAM_REPO}/pulls`, {
    title: input.prTitle,
    head: `${login}:${branch}`,
    base: "main",
    body: input.prBody,
  });

  return { prUrl: pr.html_url, branch };
}
