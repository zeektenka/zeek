// Render Midnight Circuit frame-by-frame with headless Chromium.
//   node tools/render.mjs --out frames [--fps 30] [--workers 4] [--from 0] [--to 60] [--times 1,5.5,40]
// Needs `npm install` (local three) and Playwright on NODE_PATH.
import { createRequire } from 'node:module';
import { readFile, mkdir } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

const args = Object.fromEntries(process.argv.slice(2).reduce((a, v, i, all) => (v.startsWith('--') ? [...a, [v.slice(2), all[i + 1]]] : a), []));
const fps = +(args.fps ?? 30), out = path.resolve(args.out ?? 'frames'), workers = +(args.workers ?? 4);
const from = +(args.from ?? 0), to = +(args.to ?? 60);
const jobs = args.times
  ? args.times.split(',').map((t, i) => ({ t: +t, file: `still_${String(i).padStart(2, '0')}_${t}.jpg` }))
  : Array.from({ length: Math.round((to - from) * fps) }, (_, k) => {
      const n = Math.round(from * fps) + k;
      return { t: n / fps, file: `f${String(n).padStart(5, '0')}.jpg` };
    }).filter((j) => args.resume === undefined || !existsSync(path.join(out, j.file)));
await mkdir(out, { recursive: true });

const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css' };
async function worker(id, list) {
  const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--font-render-hinting=none'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1 });
  page.on('pageerror', (e) => console.error(`[w${id}] pageerror`, e.message));
  page.on('console', (m) => { if (m.type() === 'error') console.error(`[w${id}]`, m.text()); });
  await page.route('**/*', async (route) => {
    const url = new URL(route.request().url());
    let file;
    if (url.hostname === 'cdn.jsdelivr.net') file = path.join(ROOT, 'node_modules', url.pathname.replace(/^\/npm\/three@[^/]+/, 'three'));
    else if (url.hostname === 'film.local') file = path.join(ROOT, url.pathname);
    if (!file || !existsSync(file)) return route.fulfill({ status: 404, body: '' });
    route.fulfill({ status: 200, contentType: MIME[path.extname(file)] ?? 'application/octet-stream', body: await readFile(file) });
  });
  await page.goto('http://film.local/index.html?capture');
  await page.waitForFunction(() => window.filmReady === true, null, { timeout: 120000 });
  const t0 = Date.now();
  for (let i = 0; i < list.length; i++) {
    const j = list[i];
    await page.evaluate((t) => window.renderFrame(t), j.t);
    await page.screenshot({ path: path.join(out, j.file), type: 'jpeg', quality: 93 });
    if (i % 25 === 0) console.log(`[w${id}] ${i + 1}/${list.length} t=${j.t.toFixed(2)} ${((Date.now() - t0) / (i + 1)).toFixed(0)}ms/frame`);
  }
  await browser.close();
}
// contiguous chunks keep each worker's caches warm
const chunk = Math.ceil(jobs.length / workers);
await Promise.all(Array.from({ length: workers }, (_, w) => worker(w, jobs.slice(w * chunk, (w + 1) * chunk))).filter(Boolean));
console.log(`done: ${jobs.length} frames -> ${out}`);
