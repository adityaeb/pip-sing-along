# Video Lyans – AI Agent (TikTok 9:16)

`lyans.mp4`: 1080x1920, 30fps. Gaya: karakter pixel-art (Lyans + agen-agen), kantor pixel,
kartu UI (WhatsApp, tagihan, log Web3, Telegram), judul tebal, teks per kata, musik lo-fi, dan SFX.

## Suara narasi (suara manusia)
`tools/build_audio.py` memakai **Edge TTS** (`id-ID-ArdiNeural`, suara pria natural) jika host
`speech.platform.bing.com` bisa diakses. Kalau tidak bisa, video dirender tanpa narasi
(durasi tiap kalimat diperkirakan). Ganti suara: `VOICE=id-ID-GadisNeural` (wanita).

## Edit & render ulang
1. Naskah + ekspresi karakter: `tools/script.py`
2. Tampilan / data agen: `index.html` (`CH` = karakter, `W3` = tim Web3)
3. `pip install edge-tts numpy && python3 tools/build_audio.py` → audio.wav + timeline.js
4. `node render.js` → lyans.mp4
