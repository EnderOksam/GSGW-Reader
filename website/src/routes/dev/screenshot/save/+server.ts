import { dev } from "$app/environment";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import type { RequestHandler } from "./$types";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "..", "..", "..", "..", "..", "..");
const MAX_IMAGE_BYTES = 2 * 1024 * 1024;
const SLUG_PATTERN = /^[A-Za-z0-9_-]{1,64}$/;

function isWebp(buf: Buffer) {
  return (
    buf.length >= 12 &&
    buf.subarray(0, 4).toString("ascii") === "RIFF" &&
    buf.subarray(8, 12).toString("ascii") === "WEBP"
  );
}

export const POST: RequestHandler = async ({ request }) => {
  if (!dev) {
    return new Response("Not available in production", { status: 404 });
  }

  let payload: unknown;
  try {
    payload = await request.json();
  } catch {
    return new Response("Invalid JSON", { status: 400 });
  }

  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    return new Response("Invalid payload", { status: 400 });
  }

  const { slug, image } = payload as Record<string, unknown>;
  if (typeof slug !== "string" || !SLUG_PATTERN.test(slug)) {
    return new Response("Invalid slug", { status: 400 });
  }
  if (typeof image !== "string" || image.length === 0) {
    return new Response("Missing image", { status: 400 });
  }

  const buf = Buffer.from(image, "base64");
  if (buf.length === 0) {
    return new Response("Invalid image", { status: 400 });
  }
  if (buf.length > MAX_IMAGE_BYTES) {
    return new Response("Image is too large", { status: 413 });
  }
  if (!isWebp(buf)) {
    return new Response("Image must be WebP", { status: 400 });
  }

  try {
    const thumbsDir = path.resolve(REPO_ROOT, "chapters", "manwha", "thumbnails");
    fs.mkdirSync(thumbsDir, { recursive: true });
    fs.writeFileSync(path.join(thumbsDir, `${slug}.webp`), buf);

    const staticThumbsDir = path.resolve(
      REPO_ROOT,
      "website",
      "static",
      "chapters",
      "manwha",
      "thumbnails",
    );
    fs.mkdirSync(staticThumbsDir, { recursive: true });
    fs.writeFileSync(path.join(staticThumbsDir, `${slug}.webp`), buf);

    return new Response(JSON.stringify({ success: true }), {
      headers: { "Content-Type": "application/json" },
    });
  } catch (e) {
    return new Response(e instanceof Error ? e.message : String(e), {
      status: 500,
    });
  }
};
