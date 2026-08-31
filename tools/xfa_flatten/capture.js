const puppeteer = require('puppeteer');
(async()=>{
 const [,, f, out, scaleArg] = process.argv;
 const scale = scaleArg || '1.3333333';  // 96/72 -> output PDF at true point size (A4/Letter)
 const browser = await puppeteer.launch({
   executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
   headless: true, args: ['--no-sandbox','--disable-gpu']
 });
 const page = await browser.newPage();
 page.on('console', m => console.log('PAGE:', m.text()));
 page.on('pageerror', e => console.log('PAGEERR:', String(e)));
 const url = 'http://localhost:8799/render.html?f='+encodeURIComponent(f)+'&scale='+scale;
 await page.goto(url, { waitUntil:'load', timeout:60000 });
 await page.waitForFunction('window.__done===true', { timeout:60000 });
 const err = await page.evaluate('window.__err||null');
 if (err) { console.error('RENDER ERROR:\n'+err); await browser.close(); process.exit(1); }
 const sizes = await page.evaluate('window.__sizes||[]');
 if (!sizes.length) { console.error('NO PAGES RENDERED'); await browser.close(); process.exit(1); }
 if (new Set(sizes.map(s=>s.w+'x'+s.h)).size > 1) {
   console.error('NON-UNIFORM PAGE SIZES: '+JSON.stringify(sizes)); await browser.close(); process.exit(1); }
 console.log('SIZES:', JSON.stringify(sizes));
 if (sizes.length){
   const wpx = sizes[0].w, hpx = sizes[0].h;
   await page.pdf({ path: out, printBackground:true,
     width: (wpx/96)+'in', height: (hpx/96)+'in',
     margin:{top:'0',bottom:'0',left:'0',right:'0'} });
   console.log('WROTE', out, (wpx/96*72).toFixed(1)+'x'+(hpx/96*72).toFixed(1)+'pt', 'pages='+sizes.length);
 } else {
   console.error('NO PAGES RENDERED');
 }
 await browser.close();
})();
