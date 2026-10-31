# Video Lyans – AI Agent (TikTok 9:16)

`lyans.mp4`: 1080x1920, 30fps, ±110 detik, dengan narasi suara AI (Bahasa Indonesia), musik, dan efek suara.

## Isi
Robot Lyans (beranimasi: kedip, mulut bergerak sesuai suara, melambai), foto Bos Aditya, teks per kata ala TikTok,
agen untuk Laundry, Kos-kosan, FnB, Web3, YouTube, project yang dibangun bareng Claude, dan cara kerja Lyans.

## Edit & render ulang
1. Ubah naskah narasi di `tools/script.py` (caption + teks yang diucapkan).
2. Ubah tampilan/agen di `index.html` (data `BIZ` untuk kartu agen).
3. `pip install espeakng-loader numpy && python3 tools/build_audio.py` → audio.wav + timeline.js
4. `node render.js` → lyans.mp4
