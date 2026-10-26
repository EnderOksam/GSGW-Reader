export interface Env {
  DB: D1Database;
  DISCORD_CLIENT_ID: string;
  DISCORD_CLIENT_SECRET: string;
  GITHUB_CLIENT_ID: string;
  GITHUB_CLIENT_SECRET: string;
  SESSION_SECRET: string;
}

export async function first<T = any>(env: Env, sql: string, params: unknown[] = []): Promise<T | null> {
  return (await env.DB.prepare(sql).bind(...params).first()) as T | null;
}

export async function all<T = any>(env: Env, sql: string, params: unknown[] = []): Promise<T[]> {
  const result = await env.DB.prepare(sql).bind(...params).all();
  return (result.results ?? []) as T[];
}

export async function run(env: Env, sql: string, params: unknown[] = []): Promise<D1Result> {
  return await env.DB.prepare(sql).bind(...params).run();
}

export interface UserRow {
  id: number;
  provider: string;
  provider_user_id: string;
  login: string;
  display_name: string | null;
  avatar_url: string | null;
  is_legacy: number;
  token_scopes?: string | null;
}

export interface CommentRow {
  id: number;
  chapter: string;
  user_id: number;
  parent_id: number | null;
  body: string;
  is_legacy: number;
  created_at: string;
  updated_at: string | null;
  edited: number;
  login: string;
  display_name: string | null;
  avatar_url: string | null;
  provider: string;
  user_is_legacy: number;
}

export interface ReactionRow {
  comment_id: number;
  emoji: string;
  user_id: number;
}
