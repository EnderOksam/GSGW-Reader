import { currentUser } from "../../../_lib/auth";
import type { Env } from "../../../_lib/db";
import { first } from "../../../_lib/db";
import { GitHubActionError, proposeChapterChanges, UPSTREAM_OWNER, UPSTREAM_REPO } from "../../../_lib/github";
import { error, json, readJson } from "../../../_lib/http";

const MAX_FILES = 30;
const MAX_CONTENT_BYTES = 500_000;
const FILENAME_RE = /^\d{4}\.md$/;

const ALLOWED_DIRS: Record<string, Record<string, string>> = {
  gsgw: { fantl: "fantl", MTL: "MTL", unformattedtl: "unformattedtl" },
  debut: { debutplaintxt: "DebutPlainTxt", debutformatted: "DebutFormatted" },
};

interface PushPayloadFile {
  name?: string;
  content?: string;
}

export const onRequestPost = async (context: any): Promise<Response> => {
  const env = context.env as Env;
  const user = await currentUser(context);
  if (!user) return error("Sign in required", 401);
  if (user.provider !== "github") return error("Sign in with GitHub to push changes", 403);

  const tokenRow = await first<{ access_token: string | null; token_scopes: string | null }>(
    env,
    "SELECT access_token, token_scopes FROM users WHERE id = ?",
    [user.id]
  );
  const token = tokenRow?.access_token;
  if (!token) return error("Sign out, then sign in with GitHub again to grant push access.", 403);
  const scopes = (tokenRow?.token_scopes ?? "").split(",").map((s) => s.trim()).filter(Boolean);
  if (scopes.length > 0 && !scopes.includes("repo")) {
    return error("Your GitHub sign-in is missing repository access. Sign out, then sign in with GitHub again.", 403);
  }

  const payload = await readJson<{
    book?: string;
    translation?: string;
    title?: string;
    files?: PushPayloadFile[];
  }>(context.request);
  if (!payload) return error("Invalid JSON");

  const book = payload.book || "";
  const translation = payload.translation || "";
  const dirs = ALLOWED_DIRS[book];
  const dir = dirs?.[translation];
  if (!dir) return error("Invalid book or translation");

  const files = payload.files;
  if (!Array.isArray(files) || files.length === 0) return error("No files to push");
  if (files.length > MAX_FILES) return error(`Too many files (max ${MAX_FILES})`);

  const seen = new Set<string>();
  const cleanFiles: { path: string; content: string }[] = [];
  for (const file of files) {
    const name = file?.name ?? "";
    const content = file?.content;
    if (!FILENAME_RE.test(name)) return error(`Invalid filename: ${name}`);
    if (seen.has(name)) return error(`Duplicate file: ${name}`);
    if (typeof content !== "string" || content.length === 0) return error(`Empty content for ${name}`);
    if (content.length > MAX_CONTENT_BYTES) return error(`${name} is too large`);
    seen.add(name);
    cleanFiles.push({ path: `chapters/${book}/${dir}/${name}`, content });
  }

  const title = (payload.title || "").trim().slice(0, 200);
  const prTitle = title || `Update ${cleanFiles.length} chapter${cleanFiles.length === 1 ? "" : "s"}`;
  const fileList = cleanFiles.map((f) => `- \`${f.path}\``).join("\n");
  const prBody = [
    `Edited via the ${UPSTREAM_OWNER}/${UPSTREAM_REPO} web editor by @${user.login}.`,
    "",
    "Chapters changed:",
    fileList,
    "",
    "---",
    "*This PR was opened automatically. Review the changes before merging.*",
  ].join("\n");

  try {
    const result = await proposeChapterChanges({
      token,
      login: user.login,
      displayName: user.display_name || user.login,
      files: cleanFiles,
      commitMessage: `${prTitle}\n\nEdited via web editor by ${user.login}`,
      prTitle,
      prBody,
    });
    return json({ prUrl: result.prUrl, branch: result.branch });
  } catch (e) {
    if (e instanceof GitHubActionError) {
      if (e.status === 401 || e.status === 403) {
        return error("GitHub permission missing or expired. Sign out, then sign in with GitHub again.", 403);
      }
      return error(`GitHub: ${e.message}`, 502);
    }
    return error("Push failed, try again", 500);
  }
};
