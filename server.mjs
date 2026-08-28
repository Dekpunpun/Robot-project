/* ---------------------------------------------------------------------------
 * Dev server — static files + same-origin proxy to the local LLM.
 *
 *   node server.mjs            → http://localhost:5173
 *   node server.mjs 8080       → custom port
 *   LLM_URL=... node server.mjs
 *
 * The proxy exists because LM Studio sends no CORS headers, so a browser page
 * cannot call it cross-origin. Serving the game and the API from one origin
 * sidesteps that entirely — no LM Studio settings to change.
 * ------------------------------------------------------------------------- */

import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const PORT = Number(process.argv[2] || process.env.PORT || 5173);
const UPSTREAM = (process.env.LLM_URL || "http://localhost:1234").replace(/\/+$/, "");

const TYPES = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon",
  ".woff2": "font/woff2",
};

/* Local models are slow — a cornered turn can take a couple of minutes. */
const PROXY_TIMEOUT_MS = 10 * 60 * 1000;

function proxy(req, res) {
  const target = `${UPSTREAM}${req.url}`;
  const chunks = [];

  req.on("data", (c) => chunks.push(c));
  req.on("end", async () => {
    const body = Buffer.concat(chunks);
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), PROXY_TIMEOUT_MS);

    try {
      const upstream = await fetch(target, {
        method: req.method,
        headers: {
          "Content-Type": req.headers["content-type"] || "application/json",
          ...(req.headers.authorization ? { Authorization: req.headers.authorization } : {}),
        },
        body: ["GET", "HEAD"].includes(req.method) ? undefined : body,
        signal: controller.signal,
      });

      const text = await upstream.text();
      res.writeHead(upstream.status, {
        "Content-Type": upstream.headers.get("content-type") || "application/json",
      });
      res.end(text);
    } catch (err) {
      const dead = err.name === "AbortError";
      res.writeHead(dead ? 504 : 502, { "Content-Type": "application/json" });
      res.end(
        JSON.stringify({
          error: dead
            ? `The model did not respond within ${PROXY_TIMEOUT_MS / 60000} minutes.`
            : `Cannot reach the LLM at ${UPSTREAM} — is LM Studio's server running? (${err.message})`,
        })
      );
    } finally {
      clearTimeout(timer);
    }
  });
}

function serveStatic(req, res) {
  const urlPath = decodeURIComponent(new URL(req.url, "http://x").pathname);
  const rel = urlPath === "/" ? "index.html" : urlPath.replace(/^\/+/, "");
  const file = path.join(ROOT, rel);

  /* Never serve outside the project directory. */
  if (!file.startsWith(ROOT)) {
    res.writeHead(403).end("Forbidden");
    return;
  }

  fs.readFile(file, (err, data) => {
    if (err) {
      res.writeHead(404, { "Content-Type": "text/plain" }).end("Not found");
      return;
    }
    res.writeHead(200, {
      "Content-Type": TYPES[path.extname(file)] || "application/octet-stream",
      "Cache-Control": "no-cache",
    });
    res.end(data);
  });
}

http
  .createServer((req, res) => {
    if (req.url.startsWith("/v1/")) proxy(req, res);
    else serveStatic(req, res);
  })
  .listen(PORT, () => {
    console.log(`\n  The Last Exhibit — http://localhost:${PORT}`);
    console.log(`  Proxying /v1/* → ${UPSTREAM}/v1/*\n`);
  });
