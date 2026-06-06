import tailwindcss from "@tailwindcss/vite";
import { sveltekit } from "@sveltejs/kit/vite";
import { enhancedImages } from "@sveltejs/enhanced-img";
import { defineConfig } from "vite";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "..");

const MIME: Record<string, string> = {
  ".cbz": "application/zip",
  ".zip": "application/zip",
  ".webp": "image/webp",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
};

export default defineConfig({
  plugins: [
    tailwindcss(),
    enhancedImages(),
    sveltekit(),
    {
      name: "serve-chapters",
      configureServer(server) {
        server.middlewares.use((req, res, next) => {
          const urlStr = req.url || "";
          if (!urlStr.startsWith("/chapters/")) return next();
          const reqPath = decodeURIComponent(urlStr.split("?")[0]);
          let filePath = path.resolve(REPO_ROOT, reqPath.slice(1));

          if (
            !fs.existsSync(filePath) &&
            urlStr.startsWith("/chapters/manwha/")
          ) {
            const filename = path.basename(reqPath);
            const rootPath = path.resolve(
              REPO_ROOT,
              "chapters",
              "manwha",
              filename,
            );
            if (fs.existsSync(rootPath) && fs.statSync(rootPath).isFile()) {
              filePath = rootPath;
            }
          }

          if (
            filePath.startsWith(REPO_ROOT) &&
            fs.existsSync(filePath) &&
            fs.statSync(filePath).isFile()
          ) {
            const ext = path.extname(filePath).toLowerCase();
            res.writeHead(200, {
              "Content-Type": MIME[ext] || "application/octet-stream",
            });
            fs.createReadStream(filePath).pipe(res);
          } else {
            next();
          }
        });
      },
    },
  ],
});
