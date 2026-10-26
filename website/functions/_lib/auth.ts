import { ADMIN_DISCORD_IDS } from "./admins";
import type { Env, UserRow } from "./db";
import { first } from "./db";
import { hasRepoScope } from "./scopes";
import { readSession } from "./session";

export function isAdmin(user: UserRow | null): boolean {
  return !!user && user.provider === "discord" && ADMIN_DISCORD_IDS.includes(user.provider_user_id);
}

export async function currentUser(context: any): Promise<UserRow | null> {
  const env = context.env as Env;
  if (!env.SESSION_SECRET) return null;
  const session = await readSession(context.request, env.SESSION_SECRET);
  if (!session) return null;
  const user = await first<UserRow>(
    env,
    "SELECT id, provider, provider_user_id, login, display_name, avatar_url, is_legacy, token_scopes FROM users WHERE id = ?",
    [session.uid]
  );
  return user ?? null;
}

export function publicUser(user: UserRow | null) {
  if (!user) return null;
  return {
    id: user.id,
    login: user.login,
    displayName: user.display_name || user.login,
    avatarUrl: user.avatar_url,
    provider: user.provider,
    isLegacy: user.is_legacy === 1,
    isAdmin: isAdmin(user),
    canPush: user.provider === "github" && hasRepoScope(user.token_scopes),
  };
}
