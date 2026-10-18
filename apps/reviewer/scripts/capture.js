#!/usr/bin/env node
/**
 * Offline deterministic screenshot capture tool for House AI Plan Reviewer.
 * Uses @playwright/test headless Chromium with strict loopback-only network isolation.
 *
 * Usage:
 *   node scripts/capture.js --bundle <path/to/bundle.json> --out <output.png> [--tab <tab>] [--json]
 */

import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";
import { chromium } from "@playwright/test";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REVIEWER_ROOT = path.resolve(__dirname, "..");
const DIST_DIR = path.resolve(REVIEWER_ROOT, "dist");

function parseArgs(args) {
  const options = {
    bundle: null,
    url: null,
    out: path.resolve(process.cwd(), "reviewer_capture.png"),
    viewport: "1280x800",
    tab: "plan",
    selector: null,
    json: false,
    port: 0, // ephemeral
  };

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg === "--bundle" && i + 1 < args.length) {
      options.bundle = path.resolve(process.cwd(), args[++i]);
    } else if (arg === "--url" && i + 1 < args.length) {
      options.url = args[++i];
    } else if (arg === "--out" && i + 1 < args.length) {
      options.out = path.resolve(process.cwd(), args[++i]);
    } else if (arg === "--viewport" && i + 1 < args.length) {
      options.viewport = args[++i];
    } else if (arg === "--tab" && i + 1 < args.length) {
      options.tab = args[++i];
    } else if (arg === "--selector" && i + 1 < args.length) {
      options.selector = args[++i];
    } else if (arg === "--json") {
      options.json = true;
    }
  }

  return options;
}

function startStaticServer(bundlePath) {
  return new Promise((resolve, reject) => {
    const server = http.createServer((req, res) => {
      // Loopback only
      const parsedUrl = new URL(req.url, "http://127.0.0.1");
      const pathname = decodeURIComponent(parsedUrl.pathname);

      // Handle custom bundle serving
      if (bundlePath && pathname === "/api/current-bundle.json") {
        if (!fs.existsSync(bundlePath)) {
          res.writeHead(404, { "Content-Type": "text/plain" });
          res.end("Bundle file not found");
          return;
        }
        res.writeHead(200, { "Content-Type": "application/json" });
        fs.createReadStream(bundlePath).pipe(res);
        return;
      }

      // Serve static files from dist or public
      let filePath = path.join(DIST_DIR, pathname === "/" ? "index.html" : pathname);
      if (!fs.existsSync(filePath)) {
        // Fallback for SPA routing to index.html
        filePath = path.join(DIST_DIR, "index.html");
      }

      if (!fs.existsSync(filePath)) {
        res.writeHead(404, { "Content-Type": "text/plain" });
        res.end("File not found in dist. Run `pnpm build` first.");
        return;
      }

      const ext = path.extname(filePath).toLowerCase();
      const mimeTypes = {
        ".html": "text/html",
        ".js": "application/javascript",
        ".css": "text/css",
        ".json": "application/json",
        ".svg": "image/svg+xml",
        ".png": "image/png",
      };
      const contentType = mimeTypes[ext] || "application/octet-stream";

      res.writeHead(200, { "Content-Type": contentType });
      fs.createReadStream(filePath).pipe(res);
    });

    server.listen(0, "127.0.0.1", () => {
      const port = server.address().port;
      resolve({ server, port });
    });
    server.on("error", reject);
  });
}

async function main() {
  const options = parseArgs(process.argv.slice(2));

  // Ensure dist exists; if not, suggest build
  if (!options.url && !fs.existsSync(path.join(DIST_DIR, "index.html"))) {
    console.error("Error: apps/reviewer/dist/index.html not found. Please run `pnpm build` first.");
    process.exit(1);
  }

  const [wStr, hStr] = options.viewport.split("x");
  const width = parseInt(wStr, 10) || 1280;
  const height = parseInt(hStr, 10) || 800;

  let serverInstance = null;
  let targetUrl = options.url;

  if (!targetUrl) {
    const { server, port } = await startStaticServer(options.bundle);
    serverInstance = server;
    if (options.bundle) {
      targetUrl = `http://127.0.0.1:${port}/?bundle=/api/current-bundle.json`;
    } else {
      targetUrl = `http://127.0.0.1:${port}/`;
    }
  }

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width, height },
    deviceScaleFactor: 1,
  });

  // Strict offline loopback security rule: block any non-loopback network request
  await context.route("**/*", (route) => {
    const reqUrl = route.request().url();
    if (reqUrl.startsWith("http://127.0.0.1") || reqUrl.startsWith("http://localhost")) {
      route.continue();
    } else {
      route.abort("internetdisconnected");
    }
  });

  const page = await context.newPage();

  try {
    await page.goto(targetUrl, { waitUntil: "networkidle", timeout: 15000 });

    // Wait for plan canvas or error
    await page.waitForSelector('[data-testid="plan-canvas"], [data-testid="gate-banner"]', {
      timeout: 10000,
    });

    // If a tab switch was requested, click the tab
    if (options.tab && options.tab !== "plan") {
      const tabBtn = page.locator(`[data-testid="tab-${options.tab}"]`);
      if (await tabBtn.count() > 0) {
        await tabBtn.click();
        await page.waitForTimeout(300); // settle UI
      }
    }

    // Wait for web fonts ready
    await page.evaluate(() => document.fonts.ready);

    // Ensure output directory exists
    const outDir = path.dirname(options.out);
    fs.mkdirSync(outDir, { recursive: true });

    let screenshotBuffer;
    if (options.selector) {
      const element = page.locator(options.selector);
      screenshotBuffer = await element.screenshot();
    } else {
      screenshotBuffer = await page.screenshot({ fullPage: false });
    }

    fs.writeFileSync(options.out, screenshotBuffer);

    // Compute SHA-256 hash
    const sha256 = crypto.createHash("sha256").update(screenshotBuffer).digest("hex");

    const result = {
      path: options.out,
      sha256,
      size_bytes: screenshotBuffer.length,
      viewport: { width, height },
      url: targetUrl,
      bundle: options.bundle,
      tab: options.tab,
      selector: options.selector,
      timestamp: new Date().toISOString(),
    };

    if (options.json) {
      console.log(JSON.stringify(result, null, 2));
    } else {
      console.log(`Saved screenshot to ${options.out} (SHA-256: ${sha256})`);
    }
  } finally {
    await browser.close();
    if (serverInstance) {
      serverInstance.close();
    }
  }
}

main().catch((err) => {
  console.error("Capture failed:", err.message);
  process.exit(1);
});
