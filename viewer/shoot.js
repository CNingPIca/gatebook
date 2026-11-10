// usage: node shoot.js <outdir> <scale> shot1 shot2 ...
// shot spec: name:state:view[:tableDeg][:cup][:noctx][:noprops][:bg]
const { chromium } = require('playwright');
const http = require('http');
const fs = require('fs');
const path = require('path');

const root = __dirname;
const types = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json', '.glb': 'model/gltf-binary' };
const server = http.createServer((req, res) => {
  const p = path.join(root, decodeURIComponent(req.url.split('?')[0]));
  fs.readFile(p, (e, d) => { if (e) { res.writeHead(404); res.end(); return; } res.writeHead(200, { 'Content-Type': types[path.extname(p)] || 'application/octet-stream' }); res.end(d); });
});

(async () => {
  const [outdir, scale, ...shots] = process.argv.slice(2);
  fs.mkdirSync(outdir, { recursive: true });
  await new Promise(r => server.listen(8765, r));
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: Number(scale) });
  page.on('console', m => { if (m.type() === 'error') console.log('console:', m.text()); });
  page.on('pageerror', e => console.log('pageerror:', e.message));
  await page.goto('http://localhost:8765/render.html');
  await page.waitForFunction(() => window.ready === true, null, { timeout: 120000 });
  for (const spec of shots) {
    const [name, state, view, deg = '90', cup = 'cup', ...flags] = spec.split(':');
    await page.evaluate(({ state, view, deg, cup, flags }) => {
      const v = window.viewer;
      v.setContext(!flags.includes('noctx'));
      v.setProps(!flags.includes('noprops'));
      if (flags.includes('cam')) { }
      v.setTableAngle(Number(deg));
      v.setCup(cup === 'cup');
      v.setState(state, false);
      if (view.includes('@')) { const n = view.split('@')[1].split(',').map(Number); v.setCameraRaw(n.slice(0, 3), n.slice(3, 6)); }
      else v.frame(view, true);
      v.renderOnce();
    }, { state, view, deg, cup, flags });
    await page.waitForTimeout(400);
    await page.evaluate(() => window.viewer.renderOnce());
    await page.screenshot({ path: path.join(outdir, name + '.png'), omitBackground: flags.includes('transparent') });
    console.log('shot', name);
  }
  await browser.close();
  server.close();
})();
