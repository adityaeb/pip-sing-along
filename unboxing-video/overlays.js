// Render teks overlay (PNG transparan 1080x1920) untuk video unboxing
const { chromium } = require('playwright'); const path = require('path');
const ANTON = 'data:font/woff2;base64,' + require('fs').readFileSync(path.join(__dirname, '..', 'lyans-video', 'assets', 'fonts', 'anton.woff2')).toString('base64');
const O = [
 ['hook',   `<div class="big" style="top:1080px">UNBOXING<br><span>TIME</span> 📦</div><div class="tag" style="top:1420px">#RycoEyewear</div>`],
 ['datang', `<div class="pill" style="top:1380px">Paketnya datang! 📦</div>`],
 ['buka',   `<div class="pill" style="top:1380px">Siapa yang buka duluan? 🤭</div>`],
 ['pelan',  `<div class="pill" style="top:1380px">Buka pelan-pelan… 🤏</div>`],
 ['baru',   `<div class="pill y" style="top:1380px">✨ Kacamata baru! 😎</div>`],
 ['gaya',   `<div class="pill" style="top:1380px">Gaya dulu dong ✨</div>`],
 ['review', `<div class="pill" style="top:1380px">Review dari si kecil 💛</div>`],
 ['end',    `<div class="big" style="top:640px;font-size:120px">MAKASIH<br><span>UDAH NONTON</span> 💛</div><div class="tag" style="top:960px">#RycoEyewear</div>`],
];
(async () => {
  const b = await chromium.launch({ args: ['--allow-file-access-from-files'] }); const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  for (const [n, html] of O) {
    await p.setContent(`<html><head><style>
      @font-face{font-family:Anton;src:url(${ANTON})}
      html,body{margin:0;width:1080px;height:1920px;background:transparent;font-family:Inter,"Noto Color Emoji",sans-serif}
      .big{position:absolute;left:0;right:0;text-align:center;font-family:Anton;font-size:170px;line-height:1;color:#fff;letter-spacing:2px;text-shadow:0 8px 30px rgba(0,0,0,.45)}
      .big span{color:#facc15}
      .tag{position:absolute;left:0;right:0;text-align:center}.tag{font:800 40px Inter;color:#111}
      .tag{width:max-content;margin:0 auto;background:#facc15;padding:10px 26px;border-radius:40px;box-shadow:0 8px 24px rgba(0,0,0,.3)}
      .pill{position:absolute;left:50%;transform:translateX(-50%);white-space:nowrap;font-size:54px;font-weight:800;color:#111;background:rgba(255,255,255,.94);padding:20px 40px;border-radius:60px;box-shadow:0 10px 30px rgba(0,0,0,.25);border-left:14px solid #facc15}
      .pill.y{background:#facc15}
    </style></head><body>${html}</body></html>`);
    await p.evaluate(() => document.fonts.ready);
    await p.screenshot({ path: path.join(__dirname, 'work', `ov_${n}.png`), omitBackground: true });
  }
  await b.close(); console.log('ok');
})();
