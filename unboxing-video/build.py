"""Edit video unboxing (Ryco Eyewear): potong, stabilisasi, HD 1080x1920, color grade, transisi, teks, musik, SFX.
Sumber: work/src/v1..v5.mp4 (tidak di-commit). Output: unboxing.mp4
"""
import os, subprocess, json, sys, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lyans-video', 'tools'))
HERE = os.path.dirname(os.path.abspath(__file__)); W = os.path.join(HERE, 'work'); SRC = os.path.join(W, 'src')
os.makedirs(W, exist_ok=True)
def sh(*a): subprocess.run(a, check=True)
GRADE = "hqdn3d=1.5:1.5:3:3,unsharp=5:5:0.7:5:5:0,eq=contrast=1.06:saturation=1.12:brightness=0.01:gamma=0.98,colorbalance=rs=0.02:gs=0.0:bs=-0.02"
FMT = "scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,crop=1080:1920,setsar=1,fps=30"
# (nama, file, mulai, selesai, opsi)
SEGS = [
 ("hook",  "v3", 1.4, 3.0, {"mute": True, "punch": True}),
 ("datang","v1", 0.0, 4.6, {}),
 ("datang2","v1", 9.2, 12.0, {}),
 ("buka1", "v2", 0.3, 8.3, {}),
 ("buka2", "v2", 14.0, 17.0, {}),
 ("buka3", "v2", 19.5, 27.4, {}),
 ("pakai1","v3", 0.0, 2.8, {}),
 ("slow",  "v3", 2.8, 4.0, {"slow": 2.0, "mute": True}),
 ("pakai2","v3", 4.0, 6.2, {}),
 ("gaya",  "v5", 0.0, 7.6, {}),
 ("cerita","v4", 0.0, 10.6, {}),
]
def seg_file(n): return os.path.join(W, f"s_{n}.mp4")
for name, f, a, b, o in SEGS:
    out = seg_file(name)
    if os.path.exists(out): continue
    src = os.path.join(SRC, f + ".mp4"); trf = os.path.join(W, f"{name}.trf")
    sh("ffmpeg", "-loglevel", "error", "-y", "-ss", str(a), "-to", str(b), "-i", src, "-vf", f"vidstabdetect=shakiness=6:accuracy=12:result={trf}", "-f", "null", "-")
    vf = f"vidstabtransform=input={trf}:smoothing=14:zoom=4:interpol=bicubic,{FMT},{GRADE}"
    if o.get("slow"):
        vf += f",setpts={o['slow']}*PTS,minterpolate=fps=30:mi_mode=blend"
    if o.get("punch"):
        vf += ",zoompan=z='min(1.0+0.0018*on,1.12)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps=30"
    dur = (b - a) * o.get("slow", 1)
    af = "anull" if not o.get("mute") else "volume=0"
    if o.get("slow"): af = "volume=0,atempo=0.5"
    sh("ffmpeg", "-loglevel", "error", "-y", "-ss", str(a), "-to", str(b), "-i", src, "-vf", vf,
       "-af", (f"{af},aresample=48000" if o.get("mute") else f"{af},aresample=48000,highpass=f=90,acompressor=threshold=-24dB:ratio=3:attack=5:release=120,loudnorm=I=-18:TP=-2"),
       "-ac", "2", "-c:v", "libx264", "-crf", "16", "-preset", "fast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-t", f"{dur:.3f}", out)
    print("seg", name, round(dur, 2))
# ---------- endcard ----------
end = os.path.join(W, "s_end.mp4")
if not os.path.exists(end):
    sh("ffmpeg", "-loglevel", "error", "-y", "-sseof", "-0.2", "-i", seg_file("cerita"), "-frames:v", "1", os.path.join(W, "last.png"))
    sh("ffmpeg", "-loglevel", "error", "-y", "-loop", "1", "-i", os.path.join(W, "last.png"), "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
       "-vf", "boxblur=30:2,eq=brightness=-0.18:saturation=0.8,fps=30,format=yuv420p", "-t", "2.6", "-c:v", "libx264", "-crf", "16", "-c:a", "aac", "-shortest", end)
names = [s[0] for s in SEGS] + ["end"]
def dur(p): return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p], capture_output=True, text=True).stdout)
D = [dur(seg_file(n)) for n in names]
# transisi: (index sebelum, jenis, durasi). Cut biasa = None
TR = {0: ("fadewhite", .25), 2: ("smoothleft", .3), 5: ("fade", .3), 8: ("fade", .3), 9: ("smoothleft", .3), 10: ("fade", .5)}
inputs = [x for n in names for x in ("-i", seg_file(n))]
fc = [f"[{i}:v]fps=30,format=yuv420p,settb=AVTB[n{i}]" for i in range(len(names))] + [f"[{i}:a]aresample=48000,asettb=AVTB[m{i}]" for i in range(len(names))]
v = "[n0]"; a = "[m0]"; t = D[0]; starts = [0.0]
for i in range(1, len(names)):
    tr = TR.get(i - 1)
    if tr:
        kind, d = tr; off = t - d
        fc.append(f"{v}[n{i}]xfade=transition={kind}:duration={d}:offset={off:.3f},settb=AVTB[v{i}]")
        fc.append(f"{a}[m{i}]acrossfade=d={d}[a{i}]"); starts.append(off); t = off + D[i]
    else:
        fc.append(f"{v}{a}[n{i}][m{i}]concat=n=2:v=1:a=1[vc{i}][a{i}]"); fc.append(f"[vc{i}]settb=AVTB[v{i}]"); starts.append(t); t += D[i]
    v, a = f"[v{i}]", f"[a{i}]"
TOTAL = t
json.dump({"names": names, "starts": starts, "durs": D, "total": TOTAL}, open(os.path.join(W, "timeline.json"), "w"), indent=1)
base = os.path.join(W, "base.mp4")
sh("ffmpeg", "-loglevel", "error", "-y", *inputs, "-filter_complex", ";".join(fc), "-map", v, "-map", a,
   "-c:v", "libx264", "-crf", "16", "-preset", "fast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", base)
print("base", round(TOTAL, 2)); print(json.dumps(dict(zip(names, [round(s, 2) for s in starts]))))
