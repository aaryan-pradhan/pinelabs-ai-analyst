"""A pixel-art pine forest at dusk for the page header, drawn in layers so CSS can animate fog between them.

Everything is drawn at 200x60 and scaled 4x with image-rendering: pixelated. Gradients use 4x4 Bayer dithering
over a six-colour palette, the way hand-made pixel art does, instead of smooth blends.
"""
import base64
import io
import math
import random

from PIL import Image

W, H = 200, 60
NAVY, DEEP, TEAL, CYAN, LILAC, PAPER, PINK = (
    "#0f2b40", "#1a4763", "#1f6f97", "#8fd0de", "#c3b4dc", "#ece4f4", "#d9577f")
BAYER = ((0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))
MOON = (40, 15)


def rgb(hex_):
    return tuple(int(hex_[i:i + 2], 16) for i in (1, 3, 5)) + (255,)


def dither(x, y, v, ramp):
    """Pick a colour from ramp for v in [0, 1], ordered-dithered between neighbouring steps."""
    i = v * (len(ramp) - 1) + BAYER[y % 4][x % 4] / 16 - .5
    return ramp[min(len(ramp) - 1, max(0, round(i)))]


def layer():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def sky():
    img, px, ramp = layer(), None, [rgb(c) for c in (NAVY, DEEP, TEAL, CYAN, LILAC)]
    px = img.load()
    for y in range(H):
        for x in range(W):
            glow = max(0, 1 - math.dist((x, y), MOON) / 105) ** 1.4
            px[x, y] = dither(x, y, min(1, glow + .22 * y / H), ramp)
    rng = random.Random(7)
    for _ in range(36):  # stars only where the sky is dark
        x, y = rng.randrange(W), rng.randrange(32)
        if px[x, y] == rgb(NAVY):
            px[x, y] = rgb(LILAC if rng.random() < .6 else PAPER)
    for y in range(H):  # the moon, lit from the upper left
        for x in range(W):
            d = math.dist((x, y), MOON)
            if d <= 6.5:
                px[x, y] = rgb(LILAC if math.dist((x, y), (MOON[0] + 3, MOON[1] + 2)) < 4.2 else PAPER)
    return img


def pine(px, cx, base, h, dark, body, light, rim, rng):
    """A fir of height h standing at (cx, base), drawn as stacked branch shelves like a hand-pixelled tree:
    each shelf droops at its tips, catches moonlight on its upper left and is in shadow underneath."""
    def put(x, y, c):
        if 0 <= x < W and 0 <= y < H:
            px[x, y] = c
    trunk_top = base - h + 2
    tiers = max(3, h // 5)
    for y in range(trunk_top, base):  # trunk first, so shelves overlap it
        put(cx, y, dark)
    put(cx, base - h, body)
    put(cx, base - h + 1, body)
    for k in range(tiers):  # top shelf first; each lower shelf is wider and drawn over the one above's skirt
        f = (k + 1) / tiers
        ty = base - h + 2 + round(k * (h - 4) / tiers)
        r = max(1, round(h * .33 * f ** .9 + rng.choice((-.5, 0, .5))))
        t = max(2, round(2 + 2.2 * f))
        for dx in range(-r, r + 1):
            a = abs(dx) / r
            top = ty + round(r * .35 * a * a)  # tips droop
            bot = top + max(1, round(t * (1 - .45 * a))) + rng.choice((0, 0, 1))  # ragged needle edge
            for y in range(top, bot + 1):
                if y == bot or (y == bot - 1 and dx > 0):
                    c = dark
                elif y == top and dx <= 0 or (y == top + 1 and dx < -r * .4 and (dx + y) % 2):
                    c = light
                else:
                    c = body
                put(cx + dx, y, c)
            if rim and dx == -r and rng.random() < .8:
                put(cx + dx, top, rim)


def trees(seed, base, heights, step, dark, body, light, rim=None, ground=None):
    img, rng = layer(), random.Random(seed)
    px = img.load()
    x = rng.randrange(step // 2)
    while x < W + 4:
        b = base + rng.choice((-1, 0, 0, 1))
        pine(px, x, b, rng.randint(*heights), rgb(dark), rgb(body), rgb(light), rim and rgb(rim), rng)
        x += rng.randint(step - 3, step + 3)
    if ground:  # rolling ground under the row, dithered into the colour above
        for x in range(W):
            top = ground + round(1.2 * math.sin(x / 11 + seed))
            for y in range(top, H):
                px[x, y] = rgb(dark)
    return img


def near():
    img, rng = layer(), random.Random(3)
    px = img.load()
    for cx, h in ((6, 58), (21, 38), (176, 46), (191, 60)):  # big firs framing the scene
        pine(px, cx, 57, h, rgb(NAVY), rgb(NAVY), rgb(DEEP), rgb(LILAC), rng)
    for x in range(W):  # ground with grass tufts
        top = 55 + round(.8 * math.sin(x / 9) + .6 * math.sin(x / 4.3))
        for y in range(top, H):
            px[x, y] = rgb(NAVY)
        if rng.random() < .35:
            px[x, top - 1] = rgb(DEEP if rng.random() < .7 else TEAL)
    for x, y in ((62, 54), (66, 55), (138, 54)):  # three little toadstools
        px[x, y], px[x, y - 1] = rgb(PAPER), rgb(PAPER)
        for dx in (-1, 0, 1):
            px[x + dx, y - 2] = rgb(PINK)
        px[x, y - 3] = rgb(PINK)
        px[x - 1, y - 2] = rgb(PAPER)  # a spot on the cap
    return img


def fog(seed, top, depth, colour):
    """A lumpy strip of mist that wraps around horizontally, so it can drift forever.
    Solid in the middle, checkered then sparse towards its edges."""
    img = layer()
    px = img.load()
    for x in range(W):
        wave = math.sin(2 * math.pi * 3 * x / W + seed) * .6 + math.sin(2 * math.pi * 7 * x / W + 2 * seed) * .4
        mid, half = top + depth / 2 + wave * 1.5, depth / 2 * (.75 + .35 * wave)
        for y in range(top - 3, top + depth + 3):
            v = 1 - abs(y - mid) / half
            if v > .55 or v > .3 and (x + y) % 2 or v > .08 and x % 4 == (y * 2) % 4 and y % 2:
                px[x % W, y] = rgb(colour)
    return img


def uri(img):
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def icon():
    """A 16px pine for the browser tab."""
    img = layer()
    pine(img.load(), 8, 16, 16, rgb(NAVY), rgb(DEEP), rgb(TEAL), None, random.Random(1))
    return img.crop((0, 0, 16, 16)).resize((64, 64), Image.NEAREST)


FIREFLIES = ((22, 70, 0, PINK), (34, 82, 1.7, CYAN), (47, 64, 3.1, PINK), (63, 76, .8, CYAN),
             (71, 58, 2.4, PINK), (80, 85, 4.0, CYAN), (90, 68, 1.2, PINK), (12, 60, 3.6, CYAN))
TWINKLES = ((52, 10, 0), (66, 22, 1.3), (78, 8, 2.1), (88, 30, .6), (95, 16, 2.8))


def html():
    layers = {"sky": sky(), "far": trees(11, 46, (9, 16), 7, DEEP, DEEP, TEAL, ground=45),
              "fog1": fog(1, 41, 7, CYAN), "mid": trees(5, 53, (18, 32), 13, NAVY, DEEP, TEAL, ground=52),
              "fog2": fog(4, 50, 4, LILAC), "near": near()}
    css = "".join(f".scene .{k} {{background-image: url({uri(v)})}}\n" for k, v in layers.items())
    flies = "".join(f'<i class="ff" style="left:{x}%;top:{y}%;animation-delay:-{d}s;background:{c}"></i>'
                    for x, y, d, c in FIREFLIES)
    stars = "".join(f'<i class="tw" style="left:{x}%;top:{y}%;animation-delay:-{d}s"></i>' for x, y, d in TWINKLES)
    return (f"<style>{css}</style><div class=\"scene\" aria-hidden=\"true\">"
            + "".join(f'<i class="l {k}"></i>' for k in layers) + stars + '<i class="shoot"></i>' + flies + "</div>")


if __name__ == "__main__":
    out = html()
    assert out.count("data:image/png;base64,") == 6 and out == html()  # six layers, drawn the same every run
    icon()
    print(len(out), "bytes")
