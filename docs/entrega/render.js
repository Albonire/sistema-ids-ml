// Render an HTML file to PDF with the Chromium bundled for Playwright.
// Usage: node render.js input.html output.pdf "footer text"
const { chromium } = require('playwright');

(async () => {
  const [input, output, footer] = process.argv.slice(2);
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto('file://' + input, { waitUntil: 'load' });
  await page.evaluate(() => document.fonts.ready);
  await page.pdf({
    path: output,
    format: 'A4',
    printBackground: true,
    outline: true,
    tagged: true,
    displayHeaderFooter: true,
    headerTemplate: '<span></span>',
    footerTemplate:
      '<div style="font-family:Inter,sans-serif;font-size:7.5px;color:#5b6070;width:100%;padding:0 17mm;display:flex;justify-content:space-between">' +
      '<span>' + (footer || '') + '</span><span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>',
    margin: { top: '18mm', bottom: '20mm', left: '17mm', right: '17mm' },
  });
  await browser.close();
})();
