import { chromium } from 'playwright';

const url = process.argv[2] || 'http://localhost:5000';
const label = process.argv[3] || '';

const browser = await chromium.launch();
const page = await browser.newPage();
await page.goto(url);
await page.waitForTimeout(1000);

const filename = label ? `screenshot-${label}.png` : 'screenshot.png';
await page.screenshot({ path: filename, fullPage: false });

console.log(`Screenshot saved: ${filename}`);
await browser.close();