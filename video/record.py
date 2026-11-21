"""Record the app chapters in one browser session, paced by the cue sheet.

Writes rec/<shot>/<n>.jpg screencast frames and rec/log.json: each frame's time, and for each
segment when it began and when each cue actually started, so render.py can pin cues to words.
Run with the local app up: see URL.
"""
import asyncio
import base64
import json
import random
import shutil
import time
from pathlib import Path

from playwright.async_api import async_playwright

import cues

HERE = Path(__file__).parent
URL = "http://localhost:8611"
OUT = HERE / "rec"
PRE = 1.0  # idle seconds around each segment, so cuts and dissolves have frames to spare
CAM_JS = (HERE / "cam.js").read_text()


class Shot:
    """A page under a CDP screencast; frames are saved as they arrive."""

    def __init__(self, page, name):
        self.page, self.name, self.frames = page, name, []
        (OUT / name).mkdir(parents=True)

    async def start(self):
        self.cdp = await self.page.context.new_cdp_session(self.page)
        self.cdp.on("Page.screencastFrame", self.frame)
        await self.cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 90, "everyNthFrame": 1})

    def frame(self, ev):
        now = time.time()
        n = len(self.frames)
        (OUT / self.name / f"{n:06d}.jpg").write_bytes(base64.b64decode(ev["data"]))
        self.frames.append([now, ev["metadata"].get("timestamp")])
        asyncio.ensure_future(self.cdp.send("Page.screencastFrameAck", {"sessionId": ev["sessionId"]}))

    async def stop(self):
        await self.cdp.send("Page.stopScreencast")


async def settle(page):
    while await page.evaluate("__cam.busy()"):
        await asyncio.sleep(0.03)


async def cam(page, spec, wait=8.0):
    """Start a camera glide (it runs on in the page); wait for its target to exist first."""
    t = time.time()
    while (pt := await page.evaluate("s => __cam.cam(s)", spec)) is False or (pt is None):
        if time.time() - t > wait:
            raise RuntimeError(f"camera target not found: {spec}")
        await asyncio.sleep(0.1)
    return pt


async def glide_click(page, x, y, dur=550):
    await page.evaluate("([x, y, d]) => __cam.glide(x, y, d)", [x, y, dur])
    await page.mouse.move(x, y)
    await page.evaluate("__cam.press()")
    await page.mouse.click(x, y)


async def click(page, sel):
    await settle(page)
    loc = page.locator(sel).first
    await loc.wait_for(state="visible", timeout=8000)
    b = await loc.bounding_box()
    await glide_click(page, b["x"] + b["width"] / 2, b["y"] + b["height"] / 2)


async def ask(page, text, dur, view=None):
    """Glide to the question box, type `text` so it ends `dur` seconds from now, press Enter."""
    t0 = time.time()
    view = view or {"sel": "[data-testid=stTextInput]", "zoom": 1.5, "dur": 800}
    pt = await cam(page, {**view, "focus": cues.APP})
    await page.evaluate("([x, y, d]) => __cam.glide(x, y, d)", [pt["x"], pt["y"], view.get("dur", 800)])
    await asyncio.sleep(view.get("dur", 800) / 1000)
    await page.mouse.click(pt["x"], pt["y"])
    await page.keyboard.press("ControlOrMeta+a")
    left = dur - (time.time() - t0) - 0.25
    per = max(0.04, min(0.11, left / max(1, len(text))))
    for ch in text:
        await page.keyboard.type(ch)
        await asyncio.sleep(per * random.uniform(0.55, 1.45))
    await asyncio.sleep(0.25)
    await page.keyboard.press("Backspace" if not text else "Enter")
    if not text:
        await page.keyboard.press("Enter")


async def run(page, action, args):
    if action == "cam":
        await cam(page, args[0])
    elif action == "ask":
        await ask(page, *args)
    elif action == "clear":  # empty the question box with the whole page in view
        await ask(page, "", 0, {"full": True, "top": True, "dur": 800})
    elif action == "click":
        await click(page, args[0])
    elif action == "key":
        await page.keyboard.press(args[0])
    elif action == "js":
        await page.evaluate(args[0])
    else:
        raise ValueError(action)


async def segment(page, name, dur, todo, log):
    """Play `todo` [(t, action, args)] against a clock that reads 0 when the segment begins."""
    T = time.time() + PRE
    seg = {"name": name, "T": T, "dur": dur, "acts": []}
    for t, action, args in todo:
        await asyncio.sleep(max(0.0, T + t - time.time()))
        seg["acts"].append([t, round(time.time() - T, 3), action])
        await run(page, action, args)
    await asyncio.sleep(max(0.0, T + dur + PRE - time.time()))
    late = [(a[0], a[1], a[2]) for a in seg["acts"] if a[1] - a[0] > 0.1]
    print(f"{name}: {dur:.1f}s, {len(todo)} cues" + (f", late: {late}" if late else ""))
    log["segments"].append(seg)


async def main():
    shutil.rmtree(OUT, ignore_errors=True)
    tl = {ch["c"]: ch for ch in cues.timeline()}
    log = {"segments": []}
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
        card, app = await ctx.new_page(), await ctx.new_page()
        await card.goto((HERE / "card.html").as_uri(), wait_until="networkidle")
        await card.evaluate(CAM_JS)
        await app.goto(URL)
        await app.wait_for_selector(".ln")
        await app.locator(cues.APP).fill("")
        await app.locator(cues.APP).press("Enter")
        await app.wait_for_timeout(3000)
        await app.evaluate(CAM_JS)

        ch0 = tl[0]
        split = next(t for t, a, _ in ch0["cues"] if a == "split")
        shot = Shot(card, "card")
        await card.bring_to_front()
        await shot.start()
        await segment(card, "card", split, [q for q in ch0["cues"] if q[1] != "split"], log)
        await shot.stop()
        log["card"] = shot.frames

        shot = Shot(app, "app")
        await app.bring_to_front()
        await shot.start()
        await segment(app, "ch0", ch0["dur"] - split, [], log)
        for c in sorted(tl):
            if c and c not in cues.MANIM:
                await segment(app, f"ch{c}", tl[c]["dur"], tl[c]["cues"], log)
        await shot.stop()
        log["app"] = shot.frames
        await browser.close()
    log["split"] = split
    (OUT / "log.json").write_text(json.dumps(log))
    for name in ("card", "app"):
        f = log[name]
        print(f"{name}: {len(f)} frames, {len(f) / (f[-1][0] - f[0][0]):.1f} fps,"
              f" clock offset {f[0][0] - (f[0][1] or f[0][0]):+.3f}s")


if __name__ == "__main__":
    asyncio.run(main())
