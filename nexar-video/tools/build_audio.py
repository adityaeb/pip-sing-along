"""Bangun audio video Lyans: narasi (suara manusia via Edge TTS jika jaringan mengizinkan), musik lo-fi, SFX.
Output: ../audio.wav dan ../timeline.js

Pilih suara: VOICE=id-ID-ArdiNeural (pria, default) atau id-ID-GadisNeural (wanita).
Kalau Edge TTS tidak bisa diakses, narasi dikosongkan dan durasi diperkirakan dari panjang teks
(video tetap bisa dirender; render ulang setelah suara tersedia).
"""
import sys, os, json, wave, io, subprocess, asyncio, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from script import S
OUT = os.path.join(os.path.dirname(__file__), "..")
SR = 44100; FPS = 30
VOICE = os.environ.get("VOICE", "id-ID-ArdiNeural"); RATE = os.environ.get("RATE", "+6%")

def decode_mp3(b):
    p = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", "pipe:0", "-f", "f32le", "-ac", "1", "-ar", str(SR), "pipe:1"], input=b, capture_output=True, check=True)
    return np.frombuffer(p.stdout, np.float32).copy()

def trim(x, th=0.006):
    idx = np.where(np.abs(x) > th)[0]
    return x[max(0, idx[0] - 400):idx[-1] + 1200] if len(idx) else x

ENGINE = "none"
try:
    import edge_tts, ssl
    import edge_tts.communicate as _cm
    PROXY = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    for ca in ("/root/.ccr/ca-bundle.crt",):  # proxy CA (cloud environment), jika ada
        if os.path.exists(ca): _cm._SSL_CTX = ssl.create_default_context(cafile=ca)
    async def _tts(text):
        c = edge_tts.Communicate(text, VOICE, rate=RATE, proxy=PROXY); buf = b""
        async for ch in c.stream():
            if ch["type"] == "audio": buf += ch["data"]
        return buf
    asyncio.run(asyncio.wait_for(_tts("tes"), 15)); ENGINE = "edge"
except Exception as e:
    print("Edge TTS tidak tersedia:", type(e).__name__, "-> tanpa narasi (durasi diperkirakan)")

CACHE = os.path.join(os.path.dirname(__file__), ".tts_cache"); os.makedirs(CACHE, exist_ok=True)
def speak(text):
    import hashlib
    fn = os.path.join(CACHE, hashlib.md5((VOICE + RATE + text).encode()).hexdigest() + ".mp3")
    if os.path.exists(fn): return trim(decode_mp3(open(fn, "rb").read()))
    if ENGINE == "edge":
        b = asyncio.run(_tts(text)); open(fn, "wb").write(b)
        return trim(decode_mp3(b))
    return None

# ---------- narasi + timeline ----------
LEAD = {"hook": 1.2}; GAP = 0.12; TAIL = 0.45
scenes, clips, t = [], [], 0.0
for name, segs in S:
    start = t; t += LEAD.get(name, 0.3); out = []
    for cap, say, expr in segs:
        a = speak(say)
        d = len(a) / SR if a is not None else len(say) / 14.5 + 0.2
        words = cap.split(); w = np.array([max(len(x.strip("*,.!:&")), 2) + 1.5 for x in words], float)
        wt = (np.concatenate([[0], np.cumsum(w)[:-1]]) / w.sum() * d + t).round(3).tolist()
        out.append({"t": round(t, 3), "d": round(d, 3), "cap": cap, "words": words, "wt": wt, "ex": expr})
        if a is not None: clips.append((t, a))
        t += d + GAP
    t += TAIL - GAP
    scenes.append({"name": name, "s": round(start, 3), "d": round(t - start, 3), "segs": out})
TOTAL = t + 1.0
N = int(TOTAL * SR) + SR
voice = np.zeros(N, np.float32)
for st, a in clips:
    i = int(st * SR); voice[i:i + len(a)] += a
if clips:
    voice = voice / (np.abs(voice).max() + 1e-9) * 0.95

# ---------- musik (lihat tools/music.py) ----------
from music import make_music
rng = np.random.default_rng(11)
drop = scenes[0]["segs"][0]["t"]
BPM = 100
def env(n, a=0.005, r=0.3):
    x = np.arange(n) / SR; return np.minimum(1, x / a) * np.exp(-x / r)
def add(sig, at, buf):
    i = int(at * SR); j = min(N, i + len(sig))
    if 0 <= i < N: buf[i:j] += sig[:j - i]
music2 = np.zeros((N, 2), np.float32); m = make_music(TOTAL, drop, SR); music2[:len(m)] = m

# ---------- SFX ----------
sfx = np.zeros(N, np.float32)
def whoosh(at, dur=0.5, g=0.5):
    n = int(dur * SR); x = np.arange(n) / SR; nz = rng.standard_normal(n)
    lp = np.convolve(nz, np.ones(30) / 30, 'same'); hp = nz - lp
    mixw = np.linspace(0, 1, n); add((lp * (1 - mixw) * 4 + hp * mixw * 0.5) * np.sin(np.pi * x / dur) ** 2 * g, at, sfx)
def pop(at, f=900, g=0.16):
    n = int(0.09 * SR); x = np.arange(n) / SR
    add(np.sin(2 * np.pi * (f + 700 * np.exp(-x / 0.015)) * x) * np.exp(-x / 0.025) * g, at, sfx)
def ding(at, g=0.14):
    n = int(0.9 * SR); x = np.arange(n) / SR
    add((np.sin(2 * np.pi * 1318 * x) + 0.6 * np.sin(2 * np.pi * 1760 * x) * (x > 0.09)) * np.exp(-x / 0.3) * g, at, sfx)
def typing(at, dur, g=0.05):
    for k2 in range(int(dur * 11)):
        n = int(0.02 * SR); add(np.diff(np.concatenate([[0], rng.standard_normal(n)])) * env(n, 0.0005, 0.004) * g * (0.6 + 0.4 * rng.random()), at + k2 / 11 + rng.random() * 0.03, sfx)
SC = {s["name"]: s for s in scenes}
for s in scenes[1:]: whoosh(s["s"] - 0.25)
for s in scenes:
    for g in s["segs"]: pop(g["t"])
for nm in ("status", "kas", "gas"):
    for g in SC[nm]["segs"][:2]: ding(g["t"] + 0.6)
for k in range(9): ding(SC["twist"]["segs"][1]["t"] + k * 0.22, 0.09)   # spam notifikasi
typing(SC["comeback"]["segs"][2]["t"] + 0.2, 2.0)

# ---------- mix ----------
if clips:
    venv = np.convolve(np.abs(voice), np.ones(2205) / 2205, 'same'); venv = np.minimum(1, venv / (venv.max() * 0.25))
    duck = 1 - 0.5 * np.convolve(venv, np.ones(6615) / 6615, 'same')
    mus_g = 0.42
else:
    duck = np.ones(N, np.float32); mus_g = 0.75
tt = np.arange(N) / SR
fade = np.clip(np.minimum(tt / 0.3, (TOTAL - tt) / 1.8), 0, 1)
mix = music2 * (mus_g * duck)[:, None] + ((sfx * 0.45) * fade + voice * 0.8)[:, None]
st = mix[:int(TOTAL * SR)]; st = st / np.abs(st).max() * 0.95
with wave.open(os.path.join(OUT, "audio.wav"), "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((st * 32767).astype("<i2").tobytes())

# ---------- level per frame (gerak mulut) ----------
nf = int(TOTAL * FPS) + 1; lv = np.zeros(nf)
if clips:
    for f in range(nf):
        seg = voice[int(f / FPS * SR):int((f + 1) / FPS * SR)]
        lv[f] = np.sqrt((seg ** 2).mean()) if len(seg) else 0
    lv = np.clip(lv / np.percentile(lv[lv > 0.01], 85), 0, 1)
else:  # perkiraan: buka-tutup mulut per suku kata
    for s in scenes:
        for g in s["segs"]:
            for f in range(int(g["t"] * FPS), int((g["t"] + g["d"]) * FPS)):
                lv[f] = 0.5 + 0.5 * np.sin(f / FPS * 2 * np.pi * 5.5) if (f % 23) > 2 else 0
lv = np.clip(lv, 0, 1).round(3).tolist()
tl = {"total": round(TOTAL, 3), "fps": FPS, "bpm": BPM, "drop": round(drop, 3), "voice": ENGINE != "none", "scenes": scenes, "level": lv}
open(os.path.join(OUT, "timeline.js"), "w").write("window.TL=" + json.dumps(tl, ensure_ascii=False) + ";")
print("engine", ENGINE, "total", round(TOTAL, 2))
for s in scenes: print(f'  {s["name"]:10s} {s["s"]:7.2f} {s["d"]:6.2f}')
