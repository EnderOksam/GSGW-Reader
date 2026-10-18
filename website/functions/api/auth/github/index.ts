import type { Env } from "../../../_lib/db";
import { authorizeUrl } from "../../../_lib/github";
import { isSecure, redirect } from "../../../_lib/http";
import { makeOAuthState, setOAuthState } from "../../../_lib/session";

export const onRequestGet = async (context: any): Promise<Response> => {
  const env = context.env as Env;
  const url = new URL(context.request.url);
  if (!env.GITHUB_CLIENT_ID) return redirect("/?auth_error=config");
  const state = makeOAuthState();
  const rawReturnTo = url.searchParams.get("returnTo") || "/";
  const returnTo = rawReturnTo.startsWith("/") && !rawReturnTo.startsWith("//") ? rawReturnTo : "/";
  const redirectUri = `${url.origin}/api/auth/github/callback`;
  const secure = isSecure(context.request);
  return redirect(authorizeUrl(env, redirectUri, state), {
    "Set-Cookie": setOAuthState(state, returnTo, secure),
  });
};
