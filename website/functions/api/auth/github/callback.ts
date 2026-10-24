import type { Env } from "../../../_lib/db";
import { first, run } from "../../../_lib/db";
import { avatarUrl, displayName, exchangeCode, fetchUser } from "../../../_lib/github";
import { isSecure, redirectWithCookies } from "../../../_lib/http";
import { clearOAuthState, createSessionCookie, readOAuthState } from "../../../_lib/session";

export const onRequestGet = async (context: any): Promise<Response> => {
  const env = context.env as Env;
  const url = new URL(context.request.url);
  const secure = isSecure(context.request);
  const code = url.searchParams.get("code");
  const state = url.searchParams.get("state");
  const stored = readOAuthState(context.request);

  const fail = (reason: string) =>
    redirectWithCookies(`/?auth_error=${reason}`, [clearOAuthState(secure)]);

  if (!code || !state || !stored || stored.state !== state) return fail("state");
  if (!env.GITHUB_CLIENT_ID || !env.GITHUB_CLIENT_SECRET) return fail("config");

  let sessionCookie: string;
  try {
    const redirectUri = `${url.origin}/api/auth/github/callback`;
    const { accessToken, scopes } = await exchangeCode(env, code, redirectUri);
    const ghUser = await fetchUser(accessToken);

    await run(
      env,
      `INSERT INTO users (provider, provider_user_id, login, display_name, avatar_url, is_legacy, access_token, token_scopes)
       VALUES ('github', ?, ?, ?, ?, 0, ?, ?)
       ON CONFLICT (provider, provider_user_id)
       DO UPDATE SET login = excluded.login, display_name = excluded.display_name, avatar_url = excluded.avatar_url,
         access_token = excluded.access_token, token_scopes = excluded.token_scopes`,
      [String(ghUser.id), ghUser.login, displayName(ghUser), avatarUrl(ghUser), accessToken, scopes]
    );

    const row = await first<{ id: number }>(
      env,
      "SELECT id FROM users WHERE provider = 'github' AND provider_user_id = ?",
      [String(ghUser.id)]
    );
    if (!row) return fail("user");
    sessionCookie = await createSessionCookie(env.SESSION_SECRET, row.id, secure);
  } catch {
    return fail("oauth");
  }

  const returnTo =
    stored.returnTo.startsWith("/") && !stored.returnTo.startsWith("//") ? stored.returnTo : "/";
  return redirectWithCookies(returnTo, [sessionCookie, clearOAuthState(secure)]);
};
