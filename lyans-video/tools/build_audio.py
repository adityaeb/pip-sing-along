"""Build narration (offline espeak-ng), synth music + SFX, mix with ducking -> audio.wav, timeline.js"""
import sys, os, json, wave, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import tts
from script import S
OUT = os.path.join(os.path.dirname(__file__), "..")
SR = 44100; FPS = 30
def resample(x, sr_in):
    n = int(len(x) * SR / sr_in); return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
def trim(x, th=0.01):
    idx = np.where(np.abs(x) > th)[0]; return x[idx[0]:idx[-1] + 1] if len(idx) else x

# ---------- narration ----------
LEAD = {"hook": 1.6}; GAP = 0.18; TAIL = 0.7
scenes, voice_clips, t = [], [], 0.0
for name, segs in S:
    start = t; t += LEAD.get(name, 0.45); seg_out = []
    for cap, say in segs:
        a = resample(trim(tts.say(say, "id+m3", rate=168, pitch=50, rng=70)), tts.SR)
        d = len(a) / SR; words = cap.split(); w = np.array([max(len(x), 2) for x in words], float)
        wt = (np.concatenate([[0], np.cumsum(w)[:-1]]) / w.sum() * d + t).round(3).tolist()
        seg_out.append({"t": round(t, 3), "d": round(d, 3), "cap": cap, "words": words, "wt": wt})
        voice_clips.append((t, a)); t += d + GAP
    t += TAIL - GAP
    scenes.append({"name": name, "s": round(start, 3), "d": round(t - start, 3), "segs": seg_out})
TOTAL = t + 0.8
N = int(TOTAL * SR) + SR
voice = np.zeros(N, np.float32)
for st, a in voice_clips:
    i = int(st * SR); voice[i:i + len(a)] += a
# voice FX: light compression + "AI" chorus/doubling + small room
v = voice / (np.abs(voice).max() + 1e-9)
v = np.tanh(v * 1.6) / np.tanh(1.6)
dbl = np.zeros_like(v); dl = int(0.011 * SR); dbl[dl:] = v[:-dl]
v = 0.85 * v + 0.3 * dbl
rev = np.zeros_like(v)
for dt, g in [(0.043, .22), (0.071, .16), (0.113, .11), (0.167, .07)]:
    k = int(dt * SR); rev[k:] += v[:-k] * g
voice = v + rev

# ---------- music (A minor, 112 bpm) ----------
BPM = 112; beat = 60 / BPM; bar = beat * 4
tt = np.arange(N) / SR
def note(m): return 440 * 2 ** ((m - 69) / 12)
def env(n, a=0.005, r=0.3):
    x = np.arange(n) / SR; return np.minimum(1, x / a) * np.exp(-x / r)
music = np.zeros(N, np.float32); rng = np.random.default_rng(7)
prog = [(57, [57, 60, 64]), (53, [53, 57, 60]), (48, [55, 60, 64]), (55, [55, 59, 62])]  # Am F C G
def add(sig, at):
    i = int(at * SR); j = min(N, i + len(sig))
    if i < N: music[i:j] += sig[:j - i]
intro = scenes[0]["segs"][1]["t"]  # beat drops when "Kenalin, aku LYANS"
outro_s = scenes[-1]["s"]
nb = int(TOTAL / beat) + 1
for b in range(nb):
    at = b * beat; ci = int(at // (bar * 2)) % 4; root, ch = prog[ci]
    full = intro <= at < TOTAL - 1.5
    if full:  # kick
        n = int(0.35 * SR); x = np.arange(n) / SR
        add(np.sin(2 * np.pi * (45 * x + 90 * 0.04 * (1 - np.exp(-x / 0.04)))) * np.exp(-x / 0.18) * 0.9, at)
        if b % 2 == 1:  # clap
            n = int(0.2 * SR); cl = rng.standard_normal(n); cl = np.convolve(np.diff(np.concatenate([[0], cl])), np.ones(4) / 4, 'same'); add(cl * env(n, 0.001, 0.06) * 0.22, at)
    for h in range(2):  # hats
        if full or b % 2 == 1:
            n = int(0.05 * SR); hn = rng.standard_normal(n); hn = np.diff(np.concatenate([[0], hn]))
            add(hn * env(n, 0.001, 0.012) * (0.07 if h else 0.04), at + h * beat / 2)
    if full:  # bass (saw, 8ths)
        for h in range(2):
            n = int(beat / 2 * SR * 0.9); x = np.arange(n) / SR; f = note(root - 12)
            saw = 2 * ((x * f) % 1) - 1; s = np.convolve(saw, np.ones(12) / 12, 'same')
            add(s * env(n, 0.003, 0.15) * 0.32, at + h * beat / 2)
    # arp pluck 16ths
    for q in range(4):
        m = (ch + [ch[0] + 12])[(b * 4 + q) % 4] + 12
        n = int(0.25 * SR); x = np.arange(n) / SR
        tri = 2 * np.abs(2 * ((x * note(m)) % 1) - 1) - 1
        add(tri * env(n, 0.002, 0.09) * (0.11 if full else 0.08), at + q * beat / 4)
# pad
for c in range(int(TOTAL / (bar * 2)) + 1):
    root, ch = prog[c % 4]; n = int(bar * 2 * SR); x = np.arange(n) / SR; pad = np.zeros(n)
    for m in ch:
        for det in (-0.08, 0.08):
            pad += 2 * ((x * note(m) * 2 ** (det / 12)) % 1) - 1
    pad = np.convolve(pad, np.ones(40) / 40, 'same')
    a = np.minimum(1, x / 0.4) * np.minimum(1, (bar * 2 - x) / 0.4)
    add(pad * a * 0.035, c * bar * 2)
# SFX: whoosh at each scene change, pop at each segment
sfx = np.zeros(N, np.float32)
for sc in scenes[1:]:
    n = int(0.6 * SR); x = np.arange(n) / SR; nz = rng.standard_normal(n)
    k = np.linspace(2, 60, n).astype(int); w = np.array([nz[max(0, i - kk):i + 1].mean() for i, kk in enumerate(k)])
    i = int((sc["s"] - 0.3) * SR); sfx[i:i + n] += w * np.sin(np.pi * x / 0.6) ** 2 * 0.9
for sc in scenes:
    for sg in sc["segs"]:
        n = int(0.12 * SR); x = np.arange(n) / SR
        p = np.sin(2 * np.pi * (600 + 900 * np.exp(-x / 0.02)) * x) * np.exp(-x / 0.03) * 0.18
        i = int(sg["t"] * SR); sfx[i:i + n] += p
# riser into drop
n = int(intro * SR); x = np.arange(n) / SR
sfx[:n] += rng.standard_normal(n) * (x / x[-1]) ** 3 * 0.06
# ducking
venv = np.convolve(np.abs(voice), np.ones(2205) / 2205, 'same'); venv = np.minimum(1, venv / (venv.max() * 0.25))
duck = 1 - 0.55 * np.convolve(venv, np.ones(4410) / 4410, 'same')
fade = np.minimum(1, (TOTAL - tt) / 1.5).clip(0, 1)
mix = (music * 0.55 * duck + sfx * 0.5) * fade + voice * 0.62
mix = mix[:int(TOTAL * SR)]; mix = mix / np.abs(mix).max() * 0.95
st = np.stack([mix, mix], 1)
with wave.open(os.path.join(OUT, "audio.wav"), "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((st * 32767).astype("<i2").tobytes())
# per-frame voice level (for mouth/visualizer) + beat
nf = int(TOTAL * FPS); lv = []
vraw = np.abs(voice)
for f in range(nf):
    seg = vraw[int(f / FPS * SR):int((f + 1) / FPS * SR)]; lv.append(float(np.sqrt((seg ** 2).mean())) if len(seg) else 0)
lv = np.array(lv); lv = np.clip(lv / np.percentile(lv[lv > 0.01], 90), 0, 1).round(3).tolist()
tl = {"total": round(TOTAL, 3), "fps": FPS, "bpm": BPM, "drop": round(intro, 3), "scenes": scenes, "level": lv}
open(os.path.join(OUT, "timeline.js"), "w").write("window.TL=" + json.dumps(tl, ensure_ascii=False) + ";")
print("total", round(TOTAL, 2)); [print(s["name"], s["s"], s["d"]) for s in scenes]
