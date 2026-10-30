// Screenshot every page at 390px and 1280px in light and dark mode, opened from disk (file://).
// Reports console errors, page errors and horizontal overflow.
//   node docs/checks/screenshots.js [out_dir]
const path = require("path");
const fs = require("fs");
const { chromium } = require("playwright");

const DOCS = path.resolve(__dirname, "..");
const OUT = path.resolve(process.argv[2] || path.join(DOCS, "checks", "screenshots"));
const PAGES = ["index", "toronto", "sources", "pipeline", "hamilton", "ideas", "glossary", "about"];
const WIDTHS = [390, 1280];
const SCHEMES = ["light", "dark"];

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch();
  let problems = 0;
  for (const scheme of SCHEMES) {
    for (const width of WIDTHS) {
      const ctx = await browser.newContext({ viewport: { width, height: 900 }, colorScheme: scheme });
      for (const name of PAGES) {
        const page = await ctx.newPage();
        const errors = [];
        page.on("console", (m) => { if (m.type() === "error" || m.type() === "warning") errors.push(m.text()); });
        page.on("pageerror", (e) => errors.push(String(e)));
        await page.goto("file://" + path.join(DOCS, name + ".html"));
        await page.waitForTimeout(150);
        const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
        await page.screenshot({ path: path.join(OUT, `${name}-${width}-${scheme}.png`), fullPage: true });
        if (errors.length || overflow > 0) {
          problems++;
          console.log(`FAIL ${name} ${width} ${scheme}: overflow=${overflow}px errors=${JSON.stringify(errors)}`);
        }
        await page.close();
      }
      await ctx.close();
    }
  }
  await browser.close();
  console.log(problems ? `${problems} page/size/scheme combinations had problems` : `OK: ${PAGES.length * WIDTHS.length * SCHEMES.length} renders, no console errors, no horizontal overflow`);
  process.exit(problems ? 1 : 0);
})();
