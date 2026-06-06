import { dev } from "$app/environment";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "..", "..", "..", "..", "..", "..");

export async function POST({ request }) {
  if (!dev) {
    return new Response("Not available in production", { status: 404 });
  }

  try {
    const { tl, slug, image: base64 } = await request.json();
    if (!tl || !slug || !base64) {
      return new Response("Missing tl, slug, or image", { status: 400 });
    }

    const buf = Buffer.from(base64, "base64");

    const thumbsDir = path.resolve(REPO_ROOT, "chapters", "manwha", tl, "thumbs");
    fs.mkdirSync(thumbsDir, { recursive: true });
    fs.writeFileSync(path.join(thumbsDir, `${slug}.webp`), buf);

    const staticThumbsDir = path.resolve(REPO_ROOT, "website", "static", "chapters", "manwha", tl, "thumbs");
    fs.mkdirSync(staticThumbsDir, { recursive: true });
    fs.writeFileSync(path.join(staticThumbsDir, `${slug}.webp`), buf);

    return new Response(JSON.stringify({ success: true }), {
      headers: { "Content-Type": "application/json" },
    });
  } catch (e) {
    return new Response(String(e), { status: 500 });
  }
}
