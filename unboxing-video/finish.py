"""Tahap akhir: teks overlay + musik (ducking di bawah suara anak) + SFX -> unboxing.mp4"""
import os, sys, json, subprocess, wave, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); W = os.path.join(HERE, 'work')
sys.path.insert(0, os.path.join(HERE, '..', 'crypto-video', 'tools'))
from music import make_music
TL = json.load(open(os.path.join(W, 'timeline.json'))); S = dict(zip(TL['names'], TL['starts'])); TOTAL = TL['total']
# (overlay, mulai, selesai)
OV = [('hook', 0.12, 1.3), ('datang', S['datang'] + .3, S['datang'] + 3.2), ('buka', S['buka1'] + .4, S['buka1'] + 3.2),
      ('pelan', S['buka3'] + .3, S['buka3'] + 3.0), ('baru', S['slow'] + .1, S['pakai2'] + 1.2), ('gaya', S['gaya'] + .4, S['gaya'] + 3.0),
      ('review', S['cerita'] + .4, S['cerita'] + 3.0), ('end', S['end'] + .25, TOTAL)]
SR = 48000
# ---- audio ----
p = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', os.path.join(W, 'base.mp4'), '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True, check=True)
orig = np.frombuffer(p.stdout, np.float32).copy(); N = len(orig)
mus = make_music(TOTAL + 1, 0.0, SR, mood='happy')[:N].mean(1)
mus = np.pad(mus, (0, max(0, N - len(mus))))[:N]
env = np.convolve(np.abs(orig), np.ones(2400) / 2400, 'same'); env = np.minimum(1, env / (np.percentile(env, 95) * .5 + 1e-6))
duck = 1 - 0.7 * np.convolve(env, np.ones(9600) / 9600, 'same')
rng = np.random.default_rng(3); sfx = np.zeros(N, np.float32)
def put(sig, at, g=1.0):
    i = int(at * SR); j = min(N, i + len(sig))
    if 0 <= i < N: sfx[i:j] += sig[:j - i] * g
def whoosh(at):
    n = int(.45 * SR); x = np.arange(n) / SR; nz = rng.standard_normal(n); lp = np.convolve(nz, np.ones(24) / 24, 'same')
    put(lp * np.sin(np.pi * x / .45) ** 2 * 1.6, at - .2, 0.5)
def pop(at):
    n = int(.08 * SR); x = np.arange(n) / SR; put(np.sin(2 * np.pi * (700 + 900 * np.exp(-x / .012)) * x) * np.exp(-x / .02), at, 0.12)
def sparkle(at):
    for k, f in enumerate([1568, 2093, 2637, 3136, 2637, 3520]):
        n = int(.6 * SR); x = np.arange(n) / SR; put(np.sin(2 * np.pi * f * x) * np.exp(-x / .18), at + k * .06, 0.05)
for n in ('datang', 'buka1', 'pakai1', 'gaya', 'cerita', 'end'): whoosh(S[n] + .1)
for o, a, b in OV: pop(a)
sparkle(S['slow'] + .05)
t = np.arange(N) / SR; fade = np.clip(np.minimum(t / .4, (TOTAL - t) / 2.0), 0, 1)
mix = orig * 1.0 + mus * 0.22 * duck * fade + sfx
mix = mix / np.abs(mix).max() * 0.95
with wave.open(os.path.join(W, 'mix.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mix * 32767).astype('<i2').tobytes())
# ---- video overlays ----
inputs = ['-i', os.path.join(W, 'base.mp4'), '-i', os.path.join(W, 'mix.wav')]; fc = []; last = '[0:v]'
for k, (o, a, b) in enumerate(OV):
    d = b - a; inputs += ['-loop', '1', '-t', f'{d:.3f}', '-i', os.path.join(W, f'ov_{o}.png')]; idx = k + 2
    fc.append(f"[{idx}:v]format=rgba,fade=in:st=0:d=0.25:alpha=1,fade=out:st={max(0, d - .3):.3f}:d=0.3:alpha=1,setpts=PTS+{a:.3f}/TB[o{k}]")
    fc.append(f"{last}[o{k}]overlay=0:'if(lt(t-{a:.3f},0.3),40*(1-(t-{a:.3f})/0.3),0)':eof_action=pass:enable='between(t,{a:.3f},{b:.3f})'[x{k}]"); last = f'[x{k}]'
out = os.path.join(HERE, 'unboxing.mp4')
subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', *inputs, '-filter_complex', ';'.join(fc), '-map', last, '-map', '1:a',
                '-c:v', 'libx264', '-crf', '17', '-preset', 'slow', '-profile:v', 'high', '-pix_fmt', 'yuv420p', '-r', '30',
                '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-ar', '48000', '-ac', '2', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', '-shortest', out], check=True)
print('done', out)
