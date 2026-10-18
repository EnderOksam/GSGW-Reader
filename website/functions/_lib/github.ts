import type { Env } from "./db";

const AUTHORIZE = "https://github.com/login/oauth/authorize";
const TOKEN = "https://github.com/login/oauth/access_token";
const API = "https://api.github.com";

const USER_AGENT = "GSGW-Reader";

export function authorizeUrl(env: Env, redirectUri: string, state: string): string {
  const params = new URLSearchParams({
    client_id: env.GITHUB_CLIENT_ID,
    redirect_uri: redirectUri,
    scope: "read:user",
    state,
  });
  return `${AUTHORIZE}?${params.toString()}`;
}

export async function exchangeCode(env: Env, code: string, redirectUri: string): Promise<string> {
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
  const data = (await res.json()) as { access_token?: string; error?: string };
  if (!data.access_token) {
    throw new Error(`GitHub token exchange returned no access_token: ${data.error ?? ""}`);
  }
  return data.access_token;
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
