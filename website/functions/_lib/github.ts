import type { Env } from "./db";

const AUTHORIZE = "https://github.com/login/oauth/authorize";
const TOKEN = "https://github.com/login/oauth/access_token";
const API = "https://api.github.com";

const USER_AGENT = "GSGW-Reader";

const FORK_READY_TIMEOUT_MS = 60_000;
const FORK_POLL_INTERVAL_MS = 2_500;
const WRITE_RETRY_TIMEOUT_MS = 20_000;

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

export interface GitHubUserResult {
  user: GitHubUser;
  scopes: string[];
}

export async function fetchUser(accessToken: string): Promise<GitHubUserResult> {
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
  const user = (await res.json()) as GitHubUser;
  const scopes = (res.headers.get("x-oauth-scopes") ?? "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  return { user, scopes };
}

export function avatarUrl(user: GitHubUser): string {
  return user.avatar_url || `https://github.com/${user.login}.png`;
}

export function displayName(user: GitHubUser): string {
  return user.name || user.login;
}

export class GitHubActionError extends Error {
  status: number;
  stage?: string;
  constructor(message: string, status: number, stage?: string) {
    super(message);
    this.status = status;
    this.stage = stage;
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
  ok: number[] = [200, 201, 202],
  stage?: string
): Promise<T> {
  const res = await gitRequest(token, method, path, body);
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new GitHubActionError(extractMessage(detail), res.status, stage);
  }
  return (await res.json()) as T;
}

async function gitCallWithRetry<T>(
  token: string,
  method: string,
  path: string,
  body: unknown,
  stage: string,
  deadline: number
): Promise<T> {
  for (;;) {
    try {
      return await gitCall<T>(token, method, path, body, undefined, stage);
    } catch (e) {
      if (
        e instanceof GitHubActionError &&
        (e.status === 404 || e.status === 409 || e.status === 422) &&
        Date.now() < deadline
      ) {
        await sleep(FORK_POLL_INTERVAL_MS);
        continue;
      }
      throw e;
    }
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForForkReady(token: string, login: string): Promise<void> {
  const deadline = Date.now() + FORK_READY_TIMEOUT_MS;
  for (;;) {
    const res = await gitRequest(token, "GET", `/repos/${login}/${UPSTREAM_REPO}/git/ref/heads/main`);
    if (res.ok) return;
    if (res.status !== 404) {
      const detail = await res.text().catch(() => "");
      throw new GitHubActionError(extractMessage(detail), res.status, "fork");
    }
    if (Date.now() >= deadline) {
      throw new GitHubActionError("Fork is not ready yet", 504, "fork");
    }
    await sleep(FORK_POLL_INTERVAL_MS);
  }
}

export async function ensureFork(token: string, login: string): Promise<void> {
  const existing = await gitRequest(token, "GET", `/repos/${login}/${UPSTREAM_REPO}`);
  if (existing.status === 200) {
    await waitForForkReady(token, login);
    return;
  }
  if (existing.status !== 404) {
    const detail = await existing.text().catch(() => "");
    throw new GitHubActionError(extractMessage(detail), existing.status, "fork");
  }

  await gitCall(token, "POST", `/repos/${UPSTREAM_OWNER}/${UPSTREAM_REPO}/forks`, {}, undefined, "fork");

  const deadline = Date.now() + FORK_READY_TIMEOUT_MS;
  for (;;) {
    const check = await gitRequest(token, "GET", `/repos/${login}/${UPSTREAM_REPO}`);
    if (check.status === 200) {
      await waitForForkReady(token, login);
      return;
    }
    if (Date.now() >= deadline) {
      throw new GitHubActionError("Fork creation timed out", 504, "fork");
    }
    await sleep(FORK_POLL_INTERVAL_MS);
  }
}

async function forkStatus(token: string, login: string): Promise<{ ahead: number; behind: number } | null> {
  const res = await gitRequest(
    token,
    "GET",
    `/repos/${UPSTREAM_OWNER}/${UPSTREAM_REPO}/compare/main...${login}:main`
  );
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    console.warn("[push] fork status unavailable", res.status, extractMessage(detail));
    return null;
  }
  try {
    const data = (await res.json()) as { ahead_by?: number; behind_by?: number };
    return { ahead: data.ahead_by ?? 0, behind: data.behind_by ?? 0 };
  } catch {
    return null;
  }
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

export async function hasPushAccess(token: string): Promise<boolean> {
  const res = await gitRequest(token, "GET", `/repos/${UPSTREAM_OWNER}/${UPSTREAM_REPO}`);
  if (!res.ok) return false;
  try {
    const data = (await res.json()) as { permissions?: { push?: boolean } };
    return data.permissions?.push === true;
  } catch {
    return false;
  }
}

async function writeBranch(
  input: ProposeChangesInput,
  repo: string,
  headOwner: string | null,
  needsFork: boolean
): Promise<ProposeChangesResult> {
  const { token, login, files } = input;

  if (needsFork) await ensureFork(token, login);

  const upstreamRef = await gitCall<{ object: { sha: string } }>(
    token,
    "GET",
    `/repos/${UPSTREAM_OWNER}/${UPSTREAM_REPO}/git/ref/heads/main`,
    undefined,
    undefined,
    "upstream ref"
  );
  let baseSha = upstreamRef.object.sha;

  if (needsFork) {
    const status = await forkStatus(token, login);
    if (!status || status.behind > 0) {
      const forkRef = await gitCall<{ object: { sha: string } }>(
        token,
        "GET",
        `/repos/${login}/${UPSTREAM_REPO}/git/ref/heads/main`,
        undefined,
        undefined,
        "fork ref"
      );
      baseSha = forkRef.object.sha;
    }
    console.log("[push] base selection", {
      base: !status || status.behind > 0 ? "fork" : "upstream",
      behind: status?.behind ?? null,
      ahead: status?.ahead ?? null,
    });
  }

  const writeDeadline = Date.now() + WRITE_RETRY_TIMEOUT_MS;

  const baseCommit = await gitCall<{ tree: { sha: string } }>(
    token,
    "GET",
    `/repos/${repo}/git/commits/${baseSha}`,
    undefined,
    undefined,
    "base commit"
  );
  const baseTreeSha = baseCommit.tree.sha;

  const treeEntries: { path: string; mode: string; type: string; sha: string }[] = [];
  for (const file of files) {
    const blob = await gitCallWithRetry<{ sha: string }>(
      token,
      "POST",
      `/repos/${repo}/git/blobs`,
      { content: file.content, encoding: "utf-8" },
      "blob",
      writeDeadline
    );
    treeEntries.push({ path: file.path, mode: "100644", type: "blob", sha: blob.sha });
  }

  const tree = await gitCallWithRetry<{ sha: string }>(
    token,
    "POST",
    `/repos/${repo}/git/trees`,
    { base_tree: baseTreeSha, tree: treeEntries },
    "tree",
    writeDeadline
  );

  const commit = await gitCallWithRetry<{ sha: string }>(
    token,
    "POST",
    `/repos/${repo}/git/commits`,
    {
      message: input.commitMessage,
      tree: tree.sha,
      parents: [baseSha],
      author: {
        name: input.displayName || login,
        email: `${login}@users.noreply.github.com`,
      },
    },
    "commit",
    writeDeadline
  );

  const branch = `edit/${login}/${Date.now()}`;
  await gitCallWithRetry(
    token,
    "POST",
    `/repos/${repo}/git/refs`,
    { ref: `refs/heads/${branch}`, sha: commit.sha },
    "ref",
    writeDeadline
  );

  const head = headOwner ? `${headOwner}:${branch}` : branch;
  const pr = await gitCall<{ html_url: string }>(
    token,
    "POST",
    `/repos/${UPSTREAM_OWNER}/${UPSTREAM_REPO}/pulls`,
    {
      title: input.prTitle,
      head,
      base: "main",
      body: input.prBody,
    },
    undefined,
    "pull"
  );

  return { prUrl: pr.html_url, branch };
}

export async function proposeChapterChanges(input: ProposeChangesInput): Promise<ProposeChangesResult> {
  const direct = await hasPushAccess(input.token).catch(() => false);
  if (direct) {
    try {
      return await writeBranch(input, `${UPSTREAM_OWNER}/${UPSTREAM_REPO}`, null, false);
    } catch (e) {
      if (!(e instanceof GitHubActionError) || (e.status !== 403 && e.status !== 404)) throw e;
      console.error("[push] direct push failed, falling back to fork", {
        status: e.status,
        stage: e.stage,
        message: e.message,
      });
    }
  }
  return writeBranch(input, `${input.login}/${UPSTREAM_REPO}`, input.login, true);
}
