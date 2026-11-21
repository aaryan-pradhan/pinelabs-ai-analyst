"""A pixel-art lantern garden that fills the window behind the document (D36).

Pillow draws each layer at 320x180 with Bayer dithering, once per palette; CSS scales it with image-rendering:
pixelated. The Analyst sees it by day, a Merchant manager by night. It reacts to the app: lanterns pulse while a
question runs, koi jump at an answer, rain falls on a rejection, and clicks shed petals.
"""
import base64
import io
import json
import math
import random

import streamlit as st
from PIL import Image

W, H, WATER = 320, 180, 112
BAYER = ((0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))
DAY = dict(sky=["#7fa395", "#a3c1b0", "#c4d9c6", "#e0ebdc", "#f3f5ea"], orb=("#fffbe8", "#f5edcc"),
           far=("#8fb3a0", "#a9c6b4"), far2=("#739c89", "#8fb3a0"), fir=("#2a4d40", "#3c6a56", "#5f8f74", "#cfe3cf"),
           cherry=["#8e4a62", "#b9657d", "#e39aac", "#f2c4cf", "#fff0f3"], trunk=("#4a3326", "#6b4a34"),
           wood=("#3a2516", "#5a3a24", "#8a5c38"), stone=("#5d6b66", "#87958e", "#b4c0b8"), light="#efe7cf",
           grass=["#26453a", "#3c6a56", "#5f8f74", "#8fb38a"], water=["#3f6f73", "#5f9196", "#8fbfbd", "#cfe6e0"],
           koi=("#e8572e", "#f7f0e6"), night=False)
NIGHT = dict(sky=["#0f1f1c", "#16302b", "#1f4038", "#2e5a4c", "#4f7a66"], orb=("#f6efd8", "#c9d6c0"),
             far=("#1f3d35", "#2a4d43"), far2=("#183229", "#1f3d35"), fir=("#0c1a16", "#132823", "#1f4038", "#5f8a76"),
             cherry=["#4a2836", "#6e3d4e", "#9c5a6e", "#c9849a", "#e3b3c0"], trunk=("#1e140e", "#2e1f15"),
             wood=("#1a100a", "#2e1d12", "#4a2f1c"), stone=("#26302d", "#38443f", "#52605a"), light="#ffd27a",
             grass=["#0c1a16", "#132823", "#1d362f", "#2a4d43"], water=["#0f2228", "#173640", "#2f5d66", "#5f8f94"],
             koi=("#c9502c", "#e6dccb"), night=True)
LANTERNS = ((64, 98), (256, 98))  # light box centre of the two stone lanterns, in scene pixels


def rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)) + (255,)


class C:
    def __init__(s, w=W, h=H):
        s.w, s.h, s.img = w, h, Image.new("RGBA", (w, h), (0, 0, 0, 0))
        s.px = s.img.load()

    def put(s, x, y, c):
        x, y = round(x), round(y)
        if 0 <= x < s.w and 0 <= y < s.h:
            s.px[x, y] = rgb(c) if isinstance(c, str) else c


def ramp(x, y, v, cols):
    i = max(0, min(1, v)) * (len(cols) - 1) + BAYER[y % 4][x % 4] / 16 - .5
    return cols[min(len(cols) - 1, max(0, round(i)))]


def pine(cv, cx, base, h, tones, rng):
    dark, body, light, rim = tones
    tiers = max(3, h // 5)
    for y in range(base - h + 2, base):
        cv.put(cx, y, dark)
    cv.put(cx, base - h, body)
    cv.put(cx, base - h + 1, body)
    for k in range(tiers):
        f = (k + 1) / tiers
        ty = base - h + 2 + round(k * (h - 4) / tiers)
        r = max(1, round(h * .33 * f ** .9 + rng.choice((-.5, 0, .5))))
        t = max(2, round(2 + 2.2 * f))
        for dx in range(-r, r + 1):
            a = abs(dx) / r
            top = ty + round(r * .35 * a * a)
            bot = top + max(1, round(t * (1 - .45 * a))) + rng.choice((0, 0, 1))
            for y in range(top, bot + 1):
                c = dark if y == bot or (y == bot - 1 and dx > 0) else \
                    light if y == top and dx <= 0 or (y == top + 1 and dx < -r * .4 and (dx + y) % 2) else body
                cv.put(cx + dx, y, c)
            if dx == -r and rng.random() < .6:
                cv.put(cx + dx, top, rim)


def limb(cv, pts, w0, w1, P):
    """A branch through pts, tapering from w0 to w1 px, dark on its shaded right side."""
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        n = max(1, round(math.dist((x0, y0), (x1, y1))))
        for i in range(n + 1):
            t = i / n
            x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            w = w0 + (w1 - w0) * (pts.index((x0, y0)) + t) / (len(pts) - 1)
            for dx in range(-round(w / 2), round(w / 2) + 1):
                cv.put(x + dx, y, P["trunk"][0] if dx >= w / 2 - .5 else P["trunk"][1])


def clusters(cv, blobs, P, rng, shade=0):
    """Blossom puffs, each lit from the upper left with a darker rim underneath; flowers poke out of the edges."""
    pink = P["cherry"]
    for kx, ky, r in sorted(blobs, key=lambda b: b[1]):
        for y in range(round(ky - r - 2), round(ky + r + 2)):
            for x in range(round(kx - r - 2), round(kx + r + 2)):
                dx, dy = (x - kx) / r, (y - ky) / (r * .8)
                d = math.hypot(dx, dy) - .12 * math.sin(math.atan2(dy, dx) * 6 + kx)
                if d < 1:
                    v = .7 - .45 * dy - .3 * dx - (.35 if d > .78 and dy > .15 else 0) + shade
                    cv.put(x, y, ramp(x, y, v, pink))
                elif d < 1.22 and rng.random() < .22:
                    cv.put(x, y, pink[-1] if dy < 0 else pink[-2])


def sakura(cv, bx, by, side, P, rng):
    """A cherry tree leaning out over the pond: gnarled trunk, forked limbs, two layers of blossom so limbs show through."""
    top = (bx + side * 10, by - 44)
    limb(cv, [(bx, by), (bx + side * 2, by - 16), (bx + side * 6, by - 32), top], 5, 2.5, P)
    ends = [(top[0] + side * dx, top[1] + dy) for dx, dy in ((-16, -10), (2, -18), (16, -8), (26, 2), (-24, 2))]
    blobs = []
    for ex, ey in ends:
        blobs += [(ex + rng.uniform(-6, 6), ey + rng.uniform(-4, 4), rng.uniform(6, 9)) for _ in range(3)]
    blobs += [(top[0] + rng.uniform(-24, 24), top[1] + rng.uniform(-12, 6), rng.uniform(5, 8)) for _ in range(10)]
    clusters(cv, [(x + side * 2, y - 3, r) for x, y, r in blobs], P, rng, shade=-.4)  # back layer, in shade
    for ex, ey in ends:
        mx, my = (top[0] + ex) / 2 + rng.uniform(-3, 3), (top[1] + ey) / 2 + rng.uniform(-3, 1)
        limb(cv, [top, (mx, my), (ex, ey)], 2.5, 1, P)
    clusters(cv, [b for i, b in enumerate(blobs) if i % 3], P, rng, shade=-.3 if P["night"] else 0)
    for _ in range(40):  # petals already falling, thinning out toward the ground
        x, y = top[0] + rng.uniform(-30, 30), top[1] + 12 + abs(rng.gauss(0, 14))
        if rng.random() < .7:
            cv.put(x, y, P["cherry"][rng.choice((2, 3, 4))])


def bough(cv, x0, y0, side, P, rng):
    """A blossoming branch reaching in from a top corner, framing the scene."""
    pts = [(x0, y0), (x0 + side * 18, y0 + 6), (x0 + side * 38, y0 + 9), (x0 + side * 54, y0 + 14)]
    limb(cv, pts, 3, 1, P)
    blobs = [(x + rng.uniform(-4, 4), y + rng.uniform(-3, 5), rng.uniform(4, 7)) for x, y in pts[1:] for _ in range(3)]
    clusters(cv, blobs, P, rng, shade=-.3 if P["night"] else 0)


def layers(P):
    rng = random.Random(9)
    sky = C()
    orb = (232, 30)
    for y in range(H):
        for x in range(W):
            glow = max(0, 1 - math.dist((x, y), orb) / 150) ** 1.5
            v = (.15 + .75 * y / WATER + glow * .5) if not P["night"] else (.05 + .45 * y / WATER + glow * .6)
            sky.put(x, y, ramp(x, y, v, P["sky"]))
    for y in range(H):
        for x in range(W):
            d = math.dist((x, y), orb)
            if d <= 7:
                crescent = P["night"] and math.dist((x, y), (orb[0] + 3, orb[1] - 2)) < 5.5
                sky.put(x, y, P["orb"][1] if crescent or d > 6 else P["orb"][0])
    if P["night"]:
        for _ in range(60):
            x, y = rng.randrange(W), rng.randrange(60)
            if sky.px[x, y] == rgb(P["sky"][0]):
                sky.put(x, y, P["orb"][1])
    far = C()
    for row, (tones, base, hs, step) in enumerate(((P["far"], 84, (10, 18), 6), (P["far2"], 94, (16, 26), 9))):
        x = rng.randrange(step)
        for xx in range(W):
            for y in range(base - 1 + round(1.5 * math.sin(xx / 9 + row)), WATER + 2):
                far.put(xx, y, tones[0])
        while x < W + 4:
            pine(far, x, base + rng.choice((-1, 0, 1)), rng.randint(*hs), (tones[0], tones[0], tones[1], tones[1]), rng)
            x += rng.randint(step - 2, step + 3)
    mid = C()
    for cx in range(2, W + 6, 9):  # a dense row of dark firs behind the banks, lower behind the bridge
        edge = abs(cx - W / 2) / (W / 2)
        pine(mid, cx + rng.randint(-2, 2), 106 + rng.choice((-1, 0, 1)), round(rng.randint(20, 30) + 22 * edge), P["fir"], rng)
    for x in range(W):  # banks: high at the sides, dipping to the water in the middle
        edge = abs(x - W / 2) / (W / 2)
        top = WATER - round(10 * edge ** 2) - (round(math.sin(x / 3)) if edge > .3 else 0)
        for y in range(top, WATER + 4 if edge < .55 else round(WATER + 30 * (edge - .55) * 3)):
            mid.put(x, y, ramp(x, y, .7 - (y - top) / 14 + .2 * math.sin(x * 1.7), P["grass"]))
    for tx, side in ((40, 1), (282, -1)):  # cherry trees leaning over the pond
        sakura(mid, tx, 108, side, P, rng)
    bridge = C()
    for x in range(100, 221):  # an arched wooden bridge: deck, posts, rail
        u = (x - 160) / 60
        deck = round(WATER - 8 - 16 * (1 - u * u))
        for y in range(deck, deck + 4):
            bridge.put(x, y, P["wood"][2] if y == deck else P["wood"][1] if y < deck + 3 else P["wood"][0])
        rail = deck - 7
        bridge.put(x, rail, P["wood"][2])
        bridge.put(x, rail + 1, P["wood"][1])
        if x % 9 == 1:
            for y in range(rail, deck):
                bridge.put(x, y, P["wood"][1])
                bridge.put(x + 1, y, P["wood"][0])
        if x % 9 == 5:
            bridge.put(x, rail + 4, P["wood"][0])
    for lx, ly in LANTERNS:  # stone lanterns: roof, light box, post, foot
        for dx in range(-5, 6):
            bridge.put(lx + dx, ly - 5, P["stone"][2 if dx < 0 else 1])
            if abs(dx) < 4:
                bridge.put(lx + dx, ly - 6, P["stone"][2])
        bridge.put(lx, ly - 7, P["stone"][1])
        for dy in range(-4, 2):
            for dx in range(-3, 4):
                bridge.put(lx + dx, ly + dy, P["stone"][0] if abs(dx) == 3 else P["light"] if (dx + dy) % 3 else P["stone"][1])
        for dy in range(2, 12):
            for dx in (-1, 0, 1):
                bridge.put(lx + dx, ly + dy, P["stone"][1 if dx < 1 else 0])
        for dx in range(-4, 5):
            bridge.put(lx + dx, ly + 12, P["stone"][0])
    water = C()
    above = Image.alpha_composite(Image.alpha_composite(Image.alpha_composite(sky.img, far.img), mid.img), bridge.img)
    ap = above.load()
    for y in range(WATER, H):  # the mirror image, rippled and tinted toward the water colour
        sy = 2 * WATER - y - 1
        shift = round(math.sin(y * .9) * (1 + (y - WATER) / 30))
        for x in range(W):
            r, g, b, _ = ap[min(W - 1, max(0, x + shift)), max(0, sy)]
            wr, wg, wb, _ = rgb(ramp(x, y, .2 + .25 * (y - WATER) / (H - WATER), P["water"]))
            k = .45 + .2 * (y - WATER) / (H - WATER)
            c = (round(r * (1 - k) + wr * k), round(g * (1 - k) + wg * k), round(b * (1 - k) + wb * k), 255)
            if y % 6 == 0 and (x // 4 + y * 3) % 13 == 0:
                c = rgb(P["water"][3])
            water.put(x, y, c)
    if P["night"]:
        for lx, _ in LANTERNS:  # lantern light trails on the water
            for y in range(WATER + 2, WATER + 30):
                for dx in range(-2, 3):
                    if (y + dx) % 3 and abs(dx) < 3 - (y - WATER) / 15:
                        water.put(lx + dx + round(math.sin(y) * 1.5), y, P["light"])
    near = C()
    nrng = random.Random(3)
    for cx, cy, rx in ((12, 150, 26), (306, 155, 24), (60, 168, 18), (262, 170, 16)):  # rocks
        for x in range(cx - rx, cx + rx):
            for y in range(cy - rx // 2, H):
                if ((x - cx) / rx) ** 2 + ((y - cy) / (rx * .6)) ** 2 < 1:
                    near.put(x, y, ramp(x, y, .8 - (y - cy + rx * .3) / rx - .3 * (x - cx) / rx, list(P["stone"])))
    for x0, side in ((-2, 1), (W + 1, -1)):  # blossom branches overhanging the top corners
        bough(near, x0, 2, side, P, nrng)
    return {"sky": sky, "far": far, "mid": mid, "bridge": bridge, "water": water, "near": near}


def koi(P):
    cv = C(18, 4)  # two 9x4 frames, tail flicks
    rows = (["...oo....", ".ooowoo.o", "..oooooo.", "....o...."], ["...oo....", ".ooowooo.", "..ooooo.o", "....o...."])
    for f, frame in enumerate(rows):
        for y, row in enumerate(frame):
            for x, ch in enumerate(row):
                if ch != ".":
                    cv.put(f * 9 + x, y, P["koi"][0] if ch == "o" else P["koi"][1])
    return cv


def uri(cv):
    b = io.BytesIO()
    cv.img.save(b, "PNG")
    return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()


@st.cache_resource
def assets():
    css = []
    for name, P in (("d", DAY), ("n", NIGHT)):
        for k, cv in layers(P).items():
            css.append(f"#garden .{k} .{name}{{background-image:url({uri(cv)})}}")
        css.append(f"#garden .koi.{name}{{background-image:url({uri(koi(P))})}}")
    return "\n".join(css)


CSS = """
#garden {position: fixed; inset: 0; z-index: 0; overflow: hidden; pointer-events: none; image-rendering: pixelated}
#garden .l, #garden .l i {position: absolute; inset: 0}
#garden .l i {background-size: calc(320 * var(--s)) calc(180 * var(--s)); background-position: var(--ox) var(--oy);
       background-repeat: no-repeat; image-rendering: pixelated}
#garden .l {will-change: transform}
#garden .l i.n {opacity: 0}
html[data-mode=night] #garden .l i.n, html[data-mode=night] #garden .koi.n {opacity: 1}
#garden .far {transform: translate(calc(var(--mx) * 2px), calc(var(--my) * 1px))}
#garden .mid, #garden .bridge {transform: translate(calc(var(--mx) * 5px), calc(var(--my) * 2px))}
#garden .near {transform: translate(calc(var(--mx) * 10px), calc(var(--my) * 4px))}
#garden .glow {position: absolute; width: calc(7 * var(--s)); height: calc(6 * var(--s)); background: #ffd27a; opacity: 0;
       box-shadow: 0 0 calc(10 * var(--s)) calc(4 * var(--s)) rgba(255, 190, 90, .55)}
html[data-mode=night] #garden .glow {opacity: .9; animation: flicker 2.6s ease-in-out infinite alternate}
#garden.thinking .glow {animation: lightup 1.2s ease-in-out infinite !important}
#garden.thinking .glow:nth-of-type(2) {animation-delay: .4s !important}
@keyframes flicker {50% {opacity: .65}}
@keyframes lightup {0% {opacity: 0} 50% {opacity: 1} 100% {opacity: .2}}
#garden .koi {position: absolute; width: calc(9 * var(--s)); height: calc(4 * var(--s)); background-size: calc(18 * var(--s)) 100%;
       animation: flick .5s steps(2) infinite, swim 22s linear infinite}
#garden .koi.n {opacity: 0}
#garden .koi.k2 {animation-duration: .5s, 31s; animation-delay: 0s, -12s}
@keyframes flick {to {background-position: calc(-18 * var(--s)) 0}}
@keyframes swim {0% {transform: translateX(0)} 49% {transform: translateX(calc(110 * var(--s)))}
       50% {transform: translateX(calc(110 * var(--s))) scaleX(-1)} 99% {transform: translateX(0) scaleX(-1)}}
#garden.celebrate .koi.k1 {animation: flick .5s steps(2) infinite, jump 1.6s cubic-bezier(.3, 0, .3, 1)}
@keyframes jump {50% {transform: translate(calc(14 * var(--s)), calc(-22 * var(--s))) rotate(-30deg)}}
#garden.storm {filter: brightness(.65) saturate(.6); transition: filter .6s ease}
#garden .rain {position: absolute; inset: 0; opacity: 0; transition: opacity .4s ease;
       background: repeating-linear-gradient(105deg, transparent 0 22px, rgba(220,235,240,.55) 22px 24px, transparent 24px 47px);
       background-size: 60px 60px}
#garden.storm .rain {opacity: 1; animation: rain .4s linear infinite}
@keyframes rain {to {background-position: -16px 60px}}
.petal {position: fixed; z-index: 99999; width: 6px; height: 6px; pointer-events: none;
       will-change: transform, opacity;
       animation: petal var(--t, 1.4s) cubic-bezier(.2, .6, .4, 1) forwards}
@keyframes petal {to {transform: translate(var(--dx), var(--dy)) rotate(var(--r)); opacity: 0}}
html[data-mode=night] .petal.spark {box-shadow: 0 0 6px 2px rgba(255, 200, 100, .7)}

/* the garden is the room, the document a sheet in it */
.stApp, .stMain, header {background: transparent !important}
.block-container {background: var(--paper); margin: 48px auto 120px;
       box-shadow: 0 0 0 4px var(--label), 0 0 0 8px var(--paper), 0 0 0 12px var(--label), 16px 16px 0 12px rgba(0,0,0,.3);
       position: relative; z-index: 2}
section[data-testid="stSidebar"] {background: color-mix(in srgb, var(--paper) 88%, transparent) !important; z-index: 3}

::view-transition-old(root), ::view-transition-new(root) {animation: none; mix-blend-mode: normal}
@media (prefers-reduced-motion: reduce) {#garden *, .petal {animation: none !important}}
"""

JS = r"""
(() => {
  const cfg = document.getElementById('garden-cfg');
  const root = document.documentElement;
  const next = cfg.dataset.mode;
  if (root.dataset.mode && root.dataset.mode !== next && document.startViewTransition
      && !matchMedia('(prefers-reduced-motion: reduce)').matches) {
    // day and night swap as a circle growing out of the last click, animated on the GPU
    const [x, y] = window.__click || [innerWidth / 2, innerHeight / 2];
    const r = Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y));
    document.startViewTransition(() => { root.dataset.mode = next; }).ready.then(() =>
      root.animate({clipPath: [`circle(0px at ${x}px ${y}px)`, `circle(${r}px at ${x}px ${y}px)`]},
                   {duration: 900, easing: 'cubic-bezier(.65, 0, .35, 1)', pseudoElement: '::view-transition-new(root)'}));
  } else root.dataset.mode = next;
  if (window.__garden) return;
  window.__garden = true;
  const style = document.createElement('style');
  style.textContent = cfg.dataset.css;
  document.head.appendChild(style);
  const g = document.createElement('div');
  g.id = 'garden';
  g.innerHTML = ['sky', 'far', 'mid', 'bridge', 'water', 'near'].map(k => `<div class="l ${k}"><i class="d"></i><i class="n"></i></div>`).join('')
    + '<i class="glow"></i><i class="glow"></i><i class="koi k1 d"></i><i class="koi k1 n"></i><i class="koi k2 d"></i><i class="koi k2 n"></i><i class="rain"></i>';
  document.body.appendChild(g);
  const LANT = %LANTERNS%;
  function place() {  // fit the 320x180 scene like background-size: cover, anchored to the bottom
    const r = g.getBoundingClientRect();
    const s = Math.ceil(Math.max(r.width / 320, r.height / 180) * 2) / 2;
    const ox = Math.round((r.width - 320 * s) / 2), oy = Math.round(r.height - 180 * s);
    g.style.setProperty('--s', s + 'px'); g.style.setProperty('--ox', ox + 'px'); g.style.setProperty('--oy', oy + 'px');
    const at = (x, y) => [ox + x * s, oy + y * s];
    g.querySelectorAll('.glow').forEach((el, i) => { const [x, y] = at(LANT[i][0] - 3, LANT[i][1] - 4); el.style.left = x + 'px'; el.style.top = y + 'px'; });
    g.querySelectorAll('.koi').forEach((el, i) => { const [x, y] = at(i < 2 ? 112 : 150, i < 2 ? 140 : 160); el.style.left = x + 'px'; el.style.top = y + 'px'; });
  }
  new ResizeObserver(place).observe(document.body);
  setInterval(place, 1500);
  place();
  const day = ['#f2c4cf', '#e39aac', '#fbe6ea', '#b9657d'], night = ['#ffd27a', '#f2a33a', '#e3b3c0', '#fff1c4'];
  function burst(x, y, n = 9, spread = 90, fall = 60) {
    const cols = root.dataset.mode === 'night' ? night : day;
    for (let i = 0; i < n; i++) {
      const p = document.createElement('i');
      p.className = 'petal' + (root.dataset.mode === 'night' ? ' spark' : '');
      const a = Math.random() * Math.PI * 2, d = Math.random() * spread;
      p.style.cssText = `left:${x - 3}px;top:${y - 3}px;background:${cols[i % cols.length]};--dx:${Math.cos(a) * d + 20}px;`
        + `--dy:${Math.sin(a) * d * .6 + fall}px;--r:${Math.random() * 360}deg;--t:${1 + Math.random() * .9}s;`
        + `width:${Math.random() < .5 ? 4 : 6}px;height:${Math.random() < .5 ? 4 : 6}px`;
      document.body.appendChild(p);
      setTimeout(() => p.remove(), 2000);
    }
  }
  document.addEventListener('pointerdown', e => { window.__click = [e.clientX, e.clientY]; burst(e.clientX, e.clientY); });
  document.addEventListener('keydown', e => {
    const t = e.target;
    if (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA') { const r = t.getBoundingClientRect(); burst(r.right - 30, r.top + r.height / 2, 2, 30, 30); }
  });
  let tx = 0, ty = 0, cx = 0, cy = 0;  // parallax eases toward the pointer every frame
  document.addEventListener('pointermove', e => { tx = (e.clientX / innerWidth - .5) * 2; ty = (e.clientY / innerHeight - .5) * 2; });
  (function tick() {
    if (Math.abs(tx - cx) + Math.abs(ty - cy) > .002) {
      cx += (tx - cx) * .08; cy += (ty - cy) * .08;
      g.style.setProperty('--mx', cx.toFixed(3)); g.style.setProperty('--my', cy.toFixed(3));
    }
    requestAnimationFrame(tick);
  })();
  setInterval(() => {  // ambient petals (day) or sparks (night) drifting off the trees
    const r = g.getBoundingClientRect();
    if (r.width) burst(r.left + Math.random() * r.width, r.top + Math.random() * r.height * .4, 1, 40, 160);
  }, 700);
  let seen = '';
  setInterval(() => {  // react to the app: spinner, a new answer, a rejection
    g.classList.toggle('thinking', !!document.querySelector('[data-testid="stSpinner"]'));
    const block = document.querySelector('[data-garden]');  // app.py marks an Answer or a Rejected notice
    const head = block ? block.dataset.garden + block.textContent : '';
    if (block && head !== seen) {
      seen = head;
      const cls = block.dataset.garden;
      g.classList.add(cls);
      if (cls === 'celebrate') { const r = g.getBoundingClientRect(); for (let i = 0; i < 6; i++) setTimeout(() => burst(r.left + r.width * (i % 2 ? .85 : .15), r.top + r.height * .3, 12, 140, 120), i * 180); }
      setTimeout(() => g.classList.remove(cls), cls === 'storm' ? 4000 : 1800);
    }
  }, 300);
})();
"""


def icon():
    """A 16px fir for the browser tab, drawn like the garden's."""
    cv = C(16, 16)
    pine(cv, 8, 16, 16, DAY["fir"], random.Random(1))
    return cv.img.resize((64, 64), Image.NEAREST)


def mount(night):
    """Inject the garden; it stays mounted across reruns, follows the role's day or night and reacts on its own."""
    js = JS.replace("%LANTERNS%", json.dumps(LANTERNS))  # base64 below: the sanitiser drops a script containing "<div"
    st.html(f'<div id="garden-cfg" data-mode="{"night" if night else "day"}" '
            f'data-css="{(CSS + assets()).replace(chr(34), "&quot;")}" hidden></div>'
            f'<script>eval(atob("{base64.b64encode(js.encode()).decode()}"))</script>',
            unsafe_allow_javascript=True)
