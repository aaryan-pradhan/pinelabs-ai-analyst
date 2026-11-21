"""Cut rec/ (from record.py) and voice/ into out/first_cut.mp4 with captions.

The voice sets the clock. Each output frame at time g is looked up in the recording through
a piecewise-linear map that sends each cue's planned time to the moment it really started, so
an action that ran late is caught up by speeding up the span before it.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import numpy as np
from playwright.sync_api import sync_playwright

import cues
from record import PRE

HERE = Path(__file__).parent
REC, OUT = HERE / "rec", HERE / "out"
FPS, XF = 30, 0.6  # output frame rate; dissolve length, centred on its boundary
FIXES = {"Coaster bank": "Coastal Bank", "mixed effect": "Mix effect",
         "makeshift": "mix shift", "Certainons of": "Settlements are", "alaness": "Analyst",
         "duplicated rules": "duplicate rows", "no answers": "known answers", "buzz": "pass",
         "becomes equal": "becomes SQL", "no tables": "known tables", "DuctDB": "DuckDB",
         "end list": "AI analyst", "so team never": "so it can never", "in the first week 6": "in week 6",
         "coastal bank": "Coastal Bank", "2252": "2,252", r"(\d) \.(\d)": r"\1.\2", r"(\d) %": r"\1%"}


def placeholder(c, dur, path):
    html = f"""<body style="margin:0;width:1920px;height:1080px;display:grid;place-items:center;background:#e9e4d4;
      font:600 44px 'Source Code Pro',monospace;color:#1d3a33;text-align:center">
      <div>CHAPTER {c} · MANIM ANIMATION<br><span style="font-weight:400;font-size:30px">placeholder, {dur:.1f}s</span></div>"""
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1920, "height": 1080})
        pg.set_content(html)
        pg.screenshot(path=str(path), type="jpeg", quality=92)
        b.close()


def source(log):
    """g (seconds into the video) -> frame file, plus the late-cue report."""
    tl = cues.timeline()
    segs = {s["name"]: s for s in log["segments"]}
    shots = {name: np.array([f[0] for f in log[name]]) for name in ("card", "app")}
    report, maps = [], {}
    for s in log["segments"]:
        p = [-PRE] + [a[0] for a in s["acts"]] + [s["dur"] + PRE]
        a = [-PRE] + [a[1] for a in s["acts"]]
        a = list(np.maximum.accumulate(a))
        a.append(max(s["dur"] + PRE, a[-1] + 0.5))
        maps[s["name"]] = (p, a)
        for (pt, at, action) in s["acts"]:
            if abs(at - pt) > 0.1:
                report.append(f"{s['name']} {action} at {pt:.2f}s ran {at - pt:+.2f}s")
    holds = {c: OUT / f"ch{c}.jpg" for c in cues.MANIM}
    for c in cues.MANIM:
        placeholder(c, tl[c]["dur"], holds[c])
    split = log["split"]

    def at(g):
        ch = next(ch for ch in reversed(tl) if g >= ch["start"]) if g >= 0 else tl[0]
        local = g - ch["start"]
        if ch["c"] in cues.MANIM:
            return holds[ch["c"]]
        if ch["c"] == 0:
            name, shot, local = ("card", "card", local) if local < split else ("ch0", "app", local - split)
        else:
            name, shot = f"ch{ch['c']}", "app"
        wall = segs[name]["T"] + np.interp(local, *maps[name])
        i = max(0, int(np.searchsorted(shots[shot], wall, side="right")) - 1)
        return REC / shot / f"{i:06d}.jpg"
    return at, report


def audio(tl):
    args, chain = [], []
    for ch in tl:
        c, (a, b) = ch["c"], ch["trim"]
        args += ["-i", str(HERE / "voice" / f"ch{c}.wav")]
        f = (f"[{c}:a]atrim={a:.3f}:{b:.3f},asetpts=PTS-STARTPTS,highpass=f=80,afftdn=nf=-25,"
             + ("adeclip," if c == 2 else "") + "loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000,"
             + f"apad,atrim=end_sample={round(ch['dur'] * 48000)}[a{c}]")  # sample-exact, so chapters never drift
        chain.append(f)
    chain.append("".join(f"[a{ch['c']}]" for ch in tl) + f"concat=n={len(tl)}:v=0:a=1[out]")
    wav = OUT / "voice.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args, "-filter_complex", ";".join(chain), "-map", "[out]", str(wav)],
                   check=True)
    return wav


def captions(tl):
    out, n = [], 0
    stamp = lambda s: f"{int(s // 3600):02d}:{int(s % 3600 // 60):02d}:{int(s % 60):02d},{int(s * 1000 % 1000):03d}"
    for ch in tl:
        ws = json.loads((HERE / "words" / f"ch{ch['c']}.json").read_text())
        chunk = []
        for i, w in enumerate(ws):
            chunk.append(w)
            glued = i + 1 < len(ws) and ws[i + 1][0][:1] in ".%,"  # "77" ".8%" is one number
            if (w[0][-1:] in ".?!" or len(chunk) >= 9) and not glued or i == len(ws) - 1:
                text = " ".join(x[0] for x in chunk)
                for k, v in FIXES.items():
                    text = re.sub(k if "\\" in k else re.escape(k), v, text, flags=re.I)
                g0 = ch["start"] + chunk[0][1] - ch["trim"][0]
                g1 = ch["start"] + chunk[-1][2] - ch["trim"][0]
                n += 1
                out.append(f"{n}\n{stamp(g0)} --> {stamp(g1)}\n{text}\n")
                chunk = []
    srt = OUT / "first_cut.srt"
    srt.write_text("\n".join(out))
    return srt


def main():
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir()
    log = json.loads((REC / "log.json").read_text())
    tl = cues.timeline()
    at, report = source(log)
    total = sum(ch["dur"] for ch in tl)
    # Hard joins inside the app recording; dissolves where the picture changes source.
    edges = [log["split"]] + [tl[c]["start"] for c in sorted(cues.MANIM)] + [tl[c]["start"] + tl[c]["dur"] for c in sorted(cues.MANIM) if c < 9]
    edges = sorted(edges)
    bounds = [0.0] + edges + [total]
    parts = []
    for k in range(len(bounds) - 1):
        a = bounds[k] - (XF / 2 if k else 0)
        b = bounds[k + 1] + (XF / 2 if k < len(bounds) - 2 else 0)
        d = OUT / f"s{k}"
        d.mkdir()
        for i in range(round((b - a) * FPS)):
            (d / f"{i:06d}.jpg").symlink_to(at(a + i / FPS).resolve())
        parts.append((d, b - a))
    wav, srt = audio(tl), captions(tl)
    args, chain, acc, last = [], [], 0.0, "0:v"
    for k, (d, length) in enumerate(parts):
        args += ["-framerate", str(FPS), "-i", str(d / "%06d.jpg")]
        if k:
            acc += parts[k - 1][1] - (XF if k > 1 else 0)
            chain.append(f"[{last}][{k}:v]xfade=transition=fade:duration={XF}:offset={acc - XF:.3f}[v{k}]")
            last = f"v{k}"
    mp4 = OUT / "first_cut.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args, "-i", str(wav), "-i", str(srt),
                    "-filter_complex", ";".join(chain), "-map", f"[{last}]", "-map", f"{len(parts)}:a",
                    "-map", f"{len(parts) + 1}:s", "-c:v", "libx264", "-crf", "18", "-preset", "medium",
                    "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-c:s", "mov_text",
                    "-t", f"{total:.3f}", str(mp4)], check=True)
    # The cue list in video time, for giving notes against the cut.
    lines = []
    for ch in tl:
        lines.append(f"{ch['start'] // 60:.0f}:{ch['start'] % 60:05.2f}  chapter {ch['c']}")
        for t, action, args in ch["cues"]:
            g = ch["start"] + t
            lines.append(f"  {g // 60:.0f}:{g % 60:05.2f}  {action} {str(args[0] if args else "")[:70]}")
    (OUT / "cues.txt").write_text("\n".join(lines) + "\n")
    print(f"{mp4}: {total:.1f}s")
    print("\n".join(report) or "every cue on time")


if __name__ == "__main__":
    main()
