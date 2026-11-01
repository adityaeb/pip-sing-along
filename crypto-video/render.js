// Render index.html frame-by-frame + mux audio.wav -> binance.mp4 (1080x1920, 30fps)
// Usage: node render.js [out.mp4]   (run tools/build_audio.py first)
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
const out = process.argv[2] || path.join(__dirname, 'binance.mp4');
(async () => {
  const browser = await chromium.launch({ args: ['--allow-file-access-from-files'] });
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  await page.goto('file://' + path.join(__dirname, 'index.html'));
  await page.waitForFunction(() => window.READY && window.BOSSREADY);
  await page.evaluate(() => document.fonts.ready);
  await page.evaluate(() => Promise.all([...document.images].map(i => i.decode())));
  const { total, fps } = await page.evaluate(() => ({ total: TL.total, fps: TL.fps }));
  await page.evaluate(() => document.getAnimations().forEach(a => a.pause()));
  const ff = spawn('ffmpeg', ['-y', '-f', 'image2pipe', '-framerate', String(fps), '-i', '-',
    '-i', path.join(__dirname, 'audio.wav'), '-map', '0:v', '-map', '1:a',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '20', '-preset', 'medium',
    '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-ar', '44100', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', out],
    { stdio: ['pipe', 'ignore', 'inherit'] });
  const n = Math.round(total * fps), from = +(process.env.FROM || 0) * fps;
  for (let i = from; i < n; i++) {
    const t = i / fps;
    await page.evaluate(t => { document.getAnimations().forEach(a => { a.currentTime = t * 1000; }); window.render(t); }, t);
    const buf = await page.screenshot({ type: 'jpeg', quality: 90 });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 300 === 0) console.log(`frame ${i}/${n}`);
  }
  ff.stdin.end();
  await new Promise(r => ff.on('close', r));
  await browser.close();
  console.log('done', out);
})();
