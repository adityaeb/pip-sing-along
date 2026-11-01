"""Musik latar: pop/lo-fi ceria & bersih (C mayor, 100 bpm). Piano hangat, pad lembut, sub bass, drum ringan, reverb.
make_music(total, drop, sr) -> np.ndarray (n, 2) float32, puncak ~0.9
"""
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve

def make_music(total, drop, sr=44100, seed=5, mood='happy'):
    rng = np.random.default_rng(seed)
    N = int(total * sr) + sr
    L = np.zeros(N); R = np.zeros(N)            # dry
    RV = np.zeros(N)                             # reverb send (mono)
    BPM = 100 if mood == 'happy' else 92; beat = 60 / BPM; bar = beat * 4
    note = lambda m: 440 * 2 ** ((m - 69) / 12)
    lp = lambda x, f, o=2: sosfilt(butter(o, f, 'low', fs=sr, output='sos'), x)
    hp = lambda x, f, o=2: sosfilt(butter(o, f, 'high', fs=sr, output='sos'), x)
    bp = lambda x, a, b: sosfilt(butter(2, [a, b], 'band', fs=sr, output='sos'), x)

    def put(sig, at, gl=1.0, gr=1.0, send=0.0):
        i = int(at * sr)
        if i >= N or i < 0: return
        j = min(N, i + len(sig)); s = sig[:j - i]
        L[i:j] += s * gl; R[i:j] += s * gr; RV[i:j] += s * send

    # chords: C  G/B  Am  F   (2 bars each -> 8 bars loop)
    CH = [(36, [60, 64, 67, 72]), (35, [59, 62, 67, 71]), (33, [57, 60, 64, 69]), (29, [57, 60, 65, 69])]
    if mood == 'dark':  # Am  F  Dm  E  (tegang)
        CH = [(33, [57, 60, 64, 69]), (29, [57, 60, 65, 69]), (38, [57, 62, 65, 69]), (40, [56, 59, 64, 68])]
    def chord_at(t): return CH[int(t // (bar * 2)) % 4]

    def piano(m, dur, vel):
        n = int(dur * sr); t = np.arange(n) / sr; f = note(m); s = np.zeros(n)
        for k in range(1, 7):
            s += np.sin(2 * np.pi * f * k * (1 + 0.0004 * k * k) * t) / k ** 1.6 * np.exp(-t * (0.9 + 0.7 * k))
        s *= np.minimum(1, t / 0.004) * np.minimum(1, (dur - t) / 0.08)
        return s * vel

    end = total - 1.0
    nbars = int(total / bar) + 1
    for b in range(nbars):
        t0 = b * bar
        if t0 > end: break
        root, ch = chord_at(t0 + 0.01)
        groove = t0 + bar > drop
        # piano comp: 1, 2.5(&), 4  (syncopated pop)
        for pos, vel in ((0, .9), (1.5, .7), (3, .75)) if groove else ((0, .8), (2, .6)):
            at = t0 + pos * beat
            for i, m in enumerate(ch):
                put(piano(m, 1.6, vel * 0.11), at + i * 0.006, 0.9 - i * 0.12, 0.6 + i * 0.12, 0.35)
        # warm pad (slow attack), stereo detune
        n = int(bar * sr); t = np.arange(n) / sr; padL = np.zeros(n); padR = np.zeros(n)
        for m in ch:
            for d, side in ((-0.07, 0), (0.07, 1)):
                f = note(m) * 2 ** (d / 12); saw = 2 * ((t * f + rng.random()) % 1) - 1
                (padL if side == 0 else padR)[:] += saw
        a = np.minimum(1, t / 0.6) * np.minimum(1, (bar - t) / 0.4)
        put(lp(padL, 900) * a * 0.022, t0, 1, 0, 0.2); put(lp(padR, 900) * a * 0.022, t0, 0, 1, 0.2)
        if not groove: continue
        # sub bass: root on 1, & of 2, 3 ; octave pop on 4&
        for pos, mm, ln in ((0, 0, 1.3), (1.5, 0, .4), (2, 0, 1.0), (3.5, 12, .45)):
            n = int(ln * beat * sr); t = np.arange(n) / sr; f = note(root + mm)
            s = (np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t)) * np.minimum(1, t / 0.008) * np.minimum(1, (ln * beat - t) / 0.03)
            put(s * 0.26, t0 + pos * beat)
        for q in range(4):
            at = t0 + q * beat
            # kick (soft)
            n = int(0.35 * sr); t = np.arange(n) / sr
            k = np.sin(2 * np.pi * (50 * t + 60 * 0.03 * (1 - np.exp(-t / 0.03)))) * np.exp(-t / 0.16)
            put(k * (0.55 if q in (0, 2) else 0.32), at)
            # clap on 2 & 4
            if q in (1, 3):
                n = int(0.3 * sr); t = np.arange(n) / sr; nz = rng.standard_normal(n)
                env = np.exp(-t / 0.05) + 0.6 * np.exp(-np.maximum(0, t - 0.012) / 0.05) * (t > 0.012)
                put(bp(nz, 900, 3500) * env * 0.16, at, 0.9, 1, 0.5)
            # shaker 8ths
            for e in range(2):
                n = int(0.08 * sr); t = np.arange(n) / sr
                sh = hp(rng.standard_normal(n), 6000) * np.minimum(1, t / 0.01) * np.exp(-t / 0.025)
                put(sh * (0.016 if e else 0.01), at + e * beat / 2 + 0.01, 0.7, 1.0)
    # bell melody (soft, only in some loops) — C major pentatonic hook
    MEL = [(76, 0, 1), (79, 1, .5), (81, 1.5, .5), (79, 2, 1), (76, 3, 1),
           (74, 4, 1), (79, 5, 1), (74, 6, .5), (76, 6.5, .5), (74, 7, 1),
           (72, 8, 1), (76, 9, .5), (79, 9.5, .5), (81, 10, 1.5), (79, 11.5, .5),
           (81, 12, 1), (79, 13, 1), (76, 14, 1), (74, 15, 1)]
    loop = bar * 8
    for li in range(int(total / loop) + 1):
        base = li * loop
        if mood == 'happy' and (base < drop - 0.1 or li % 2 == 1):
            for m, st, ln in MEL:
                for rep in (0, 1):  # each 16-beat phrase covers 4 bars; play twice per 8-bar loop
                    at = base + (st + rep * 16) * beat
                    if at > end: continue
                    n = int(1.2 * sr); t = np.arange(n) / sr; f = note(m)
                    s = (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t / 0.12)) * np.exp(-t / 0.45) * np.minimum(1, t / 0.003)
                    put(s * 0.05, at, 0.75, 1.0, 0.6)
    # reverb (synthetic plate IR, stereo)
    ir_n = int(2.0 * sr); t = np.arange(ir_n) / sr
    irL = lp(rng.standard_normal(ir_n), 5000) * np.exp(-t / 0.45); irR = lp(rng.standard_normal(ir_n), 5000) * np.exp(-t / 0.45)
    irL /= np.sqrt((irL ** 2).sum()); irR /= np.sqrt((irR ** 2).sum())
    send = hp(RV, 250)
    L += fftconvolve(send, irL)[:N] * 0.9; R += fftconvolve(send, irR)[:N] * 0.9
    out = np.stack([L, R], 1)[:int(total * sr)]
    # fades + gentle master saturation
    tt = np.arange(len(out)) / sr
    fade = np.clip(np.minimum(tt / 1.0, (total - tt) / 2.5), 0, 1)[:, None]
    out = np.tanh(out / np.abs(out).max() * 1.3) / np.tanh(1.3) * fade
    return (out * 0.9).astype(np.float32)
