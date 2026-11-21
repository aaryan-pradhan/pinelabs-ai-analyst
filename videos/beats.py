"""Project beats for the demo video: the mix-vs-rate mosaic (chapter 2) and the answer pipeline (chapter 9)."""
from pathlib import Path

from manim import *
import theme as th
from beats import beat
from beats.core import listed

# The app's look, not 3Blue1Brown's: the opening card's paper and ink, Source Code Pro, the app's blue rise and
# orange fall, its garden greens and pinks.
FONTS = Path(__file__).parent / "fonts"
_tex = TexTemplate(tex_compiler="xelatex", output_format=".xdv")
_tex.add_to_preamble(r"\usepackage{xcolor}\usepackage{ragged2e}\usepackage{fontspec}"
                     r"\setmainfont{SourceCodePro}[Path=%s/, Extension=.otf, UprightFont=*-Regular, BoldFont=*-Semibold]"
                     % FONTS.as_posix() + r"\hyphenpenalty=10000\exhyphenpenalty=10000")   # whole words, as in the app
th.look(BG=ManimColor("#e9e4d4"), INK=ManimColor("#1d3a33"), DIM=ManimColor("#6f7f76"), GRID=ManimColor("#b9b09a"),
        HL=ManimColor("#e8572e"), NUM=ManimColor("#1d3a33"), DIM_OPACITY=.5, TEX=_tex,
        PALETTE={"blue": "#2b6cb0", "gold": "#b7791f", "green": "#3c6a56", "teal": "#3c6a56", "pink": "#b9657d",
                 "red": "#e8572e", "orange": "#e8572e", "grey": "#6f7f76", "white": "#1d3a33"},
        SERIES=["blue", "gold", "green", "pink", "red", "grey"])


def _nums(s):
    return [float(x) for x in listed(s, ",")]


def pulse(m, c):
    """Light a shape's outline and let it go, without growing it past its place (Indicate scales it)."""
    return m.animate(rate_func=there_and_back).set_stroke(c, width=7)


@beat("mosaic")
def mosaic(lec, names, before, after, rates, lo=70, avg="", mix="", rate="", titles="Week 5|Week 6"):
    """Mosaic bars: each bar's width is its share of traffic, its height its success rate (y from lo to 100%).
    names="UPI,cards,..." (TeX text), before/after = shares in % (two weeks), rates = success rates in %, held fixed.
    avg="92.7,88.7" the two averages; mix and rate are the two effects in points. Steps: average line, each bar
    named, width and height braced, widths morph to the second week with the heights pinned, the bars that grew
    marked, the average falls, the gap braced as the mix effect, the rate effect shown as almost zero.
    Example: mosaic names="UPI,cards,wallets,net banking" before="61.3,28.5,4.1,6.1" after="43.9,19.8,15.9,20.4" rates="95.5,91.5,79.9,78.2" avg="92.7,88.7" mix="-3.99" rate="-0.03"
    """
    ns, b, a, r = listed(names, ","), _nums(before), _nums(after), _nums(rates)
    av = _nums(avg) if avg else [sum(x * y for x, y in zip(b, r)) / 100, sum(x * y for x, y in zip(a, r)) / 100]
    tt = str(titles).split("|")
    W, H = 6.0, 5.0
    ax = Axes(x_range=[0, 100, 25], y_range=[lo, 100, 10], x_length=W, y_length=H, tips=False,
              axis_config={"color": th.DIM, "stroke_width": 2, "include_ticks": True})
    yl = VGroup(*[lec.text(f"{v}%", 1.5, size=th.LABEL_SIZE, color=th.DIM).next_to(ax.c2p(0, v), LEFT, buff=.15)
                  for v in range(lo, 101, 10)])
    ylab = lec.text("success rate", 2.6, size=th.LABEL_SIZE, color=th.DIM).rotate(PI / 2).next_to(yl, LEFT, buff=.15)
    xlab = lec.text("share of traffic", 3.5, size=th.LABEL_SIZE, color=th.DIM).next_to(ax, DOWN, buff=.25)
    cols = [th.color(c) for c in th.SERIES[:len(ns)]]

    def bars(shares):
        out, x = VGroup(), 0.0
        for s, h, c in zip(shares, r, cols):
            p0, p1 = ax.c2p(x, lo), ax.c2p(x + s, h)
            out.add(Rectangle(width=max(p1[0] - p0[0], 1e-3), height=p1[1] - p0[1])
                    .set_fill(c, .25).set_stroke(c, 2.5).move_to((p0 + p1) / 2))
            x += s
        return out

    b0, b1 = bars(b), bars(a)
    n0 = VGroup(*[VGroup(Square(.22).set_fill(c, .25).set_stroke(c, 2.5),
                         lec.text(n, 2.6, size=th.LABEL_SIZE, color=c)).arrange(RIGHT, buff=.12)
                  for n, c in zip(ns, cols)]).arrange_in_grid(cols=2, buff=(.5, .12), col_alignments="ll")
    n0.next_to(ax, UP, buff=.3).align_to(ax, LEFT)
    title = lec.text(tt[0], 3, size=th.TEXT_SIZE).next_to(n0, UP, buff=.3).align_to(ax, LEFT)
    title1 = lec.text(tt[1], 3, size=th.TEXT_SIZE).move_to(title)

    def avg_line(v, k):
        ln = DashedLine(ax.c2p(0, v), ax.c2p(100, v), color=th.HL, stroke_width=3)
        tag = lec.text(f"average {v:.1f}%", 3, size=th.LABEL_SIZE, color=th.HL)
        return ln, tag.next_to(ln, UP if k == 0 else DOWN, buff=.08).align_to(ln, LEFT).shift(RIGHT * .15)

    l0, t0 = avg_line(av[0], 0)
    l1, t1 = avg_line(av[1], 1)
    pins = VGroup(*[Line(ax.c2p(0, h), ax.c2p(100, h), color=c, stroke_width=1.5, stroke_opacity=.5)
                    for h, c in zip(r, cols)])
    room = VGroup(Rectangle(width=3.4, height=.1).next_to(ax, RIGHT, buff=0),     # the effects' brace
                  Rectangle(width=.1, height=.42 * len(ns) + .2).next_to(ax, DOWN, buff=0)).set_opacity(0)   # the share changes
    lec.fit(VGroup(ax, yl, ylab, xlab, b0, b1, n0, title, title1, l0, t0, l1, t1, pins, room))

    lec.play(Create(ax), FadeIn(yl), FadeIn(ylab), FadeIn(xlab), Write(title))
    lec.play(LaggedStart(*[GrowFromEdge(x, DOWN) for x in b0], lag_ratio=.15), run_time=1.2)
    yield                                                         # nothing broke: the average to beat
    lec.play(Create(l0), FadeIn(t0))
    yield                                                         # each bar is a payment method
    lec.play(LaggedStart(*[AnimationGroup(FadeIn(n0[i], shift=UP * .1), pulse(b0[i], cols[i]))
                           for i in range(len(ns))], lag_ratio=.3), run_time=1.4)
    yield                                                         # width = share, height = rate
    br_w = Brace(b0[0], DOWN, color=cols[0], buff=.05)
    tw = lec.text(f"{b[0]:.0f}% of traffic", 3, size=th.LABEL_SIZE, color=cols[0]).next_to(br_w, DOWN, buff=.05)
    br_h = Brace(b0[0], RIGHT, color=cols[0], buff=.05)
    th_ = VGroup(*[lec.text(s, 2, size=th.LABEL_SIZE, align=r"\centering") for s in (f"{r[0]:.1f}%", "succeed")]) \
        .arrange(DOWN, buff=.1).move_to(b0[0])                   # inside its bar, on two lines so it fits
    assert th_.width < b0[0].width - .2 and th_.height < b0[0].height - .2, "the rate label must fit inside its bar"
    lec.play(GrowFromCenter(br_w), FadeIn(tw), FadeOut(xlab))
    lec.play(GrowFromCenter(br_h), FadeIn(th_), run_time=.8)
    yield                                                         # week 5 to week 6: heights pinned
    lec.play(FadeOut(br_w, tw, br_h, th_), Create(pins), FadeIn(xlab), run_time=.6)
    lec.play(Transform(b0, b1), Transform(title, title1), run_time=1.5)
    yield                                                         # only the widths moved
    grew = [i for i in range(len(ns)) if a[i] > b[i] + 3]
    tags = VGroup(*[lec.text(f"{b[i]:.0f}% → {a[i]:.0f}%", 2.4, size=th.LABEL_SIZE, color=cols[i])
                    .next_to(b0[i], DOWN, buff=.12 + .42 * i) for i in range(len(ns))])   # a row each
    for tg in tags:                                               # never past the chart's ends
        tg.shift(RIGHT * max(0, ax.get_left()[0] - tg.get_left()[0]) + LEFT * max(0, tg.get_right()[0] - ax.get_right()[0]))
    lec.play(LaggedStart(*[FadeIn(t) for t in tags], lag_ratio=.2), FadeOut(pins, xlab), run_time=.7)
    yield                                                         # traffic moved to the low bars
    lec.play(*[pulse(b0[i], th.HL) for i in grew],
             *[b0[i].animate.set_fill(opacity=.08).set_stroke(opacity=.4) for i in range(len(ns)) if i not in grew])
    yield                                                         # that alone pulls the average down
    l0_ghost = DashedLine(ax.c2p(0, av[0]), ax.c2p(100, av[0]), color=th.DIM, stroke_width=2)
    lec.play(FadeOut(tags), FadeIn(xlab), *[b0[i].animate.set_fill(opacity=.25) for i in range(len(ns))], FadeIn(l0_ghost),
             Transform(l0, l1), Transform(t0, t1), run_time=1.5)
    yield                                                         # the mix effect
    gap = Brace(Line(ax.c2p(100, av[1]), ax.c2p(100, av[0])), RIGHT, color=th.HL, buff=.1)
    mt = lec.text(f"mix {float(mix):+.2f}".replace("-", "−") if mix else "mix", 3, size=th.LABEL_SIZE, color=th.HL)
    lec.play(GrowFromCenter(gap), FadeIn(mt.next_to(gap, RIGHT, buff=.08)))
    yield                                                         # the rate effect: the heights never moved
    rt = lec.text(f"rate {float(rate):+.2f}".replace("-", "−") if rate else "rate ≈ 0", 3, color=th.DIM,
                size=th.LABEL_SIZE).next_to(mt, DOWN, buff=.2).align_to(mt, LEFT)
    lec.play(FadeIn(rt), *[pulse(p, th.DIM) for p in b0])


@beat("pipeline")
def pipeline(lec, stages, notes="", cols="", order=""):
    """A top-to-bottom chain of boxes, one per stage, each with an optional side note. stages="Question;Model;..."
    notes="|never writes a number|..." ('|' per stage), cols="white,gold,..." (one hue per stage). order="0,1,n1,2"
    is one step per entry: a stage index brings in its box and arrow, n<i> its note, *<i> lights box i, "all" lights the
    chain; '+' joins several into one step.
    Example: pipeline stages="Your question;Language model;Plan" notes="|never writes a number|fixed metrics" cols="white,gold,blue" order="n0,1+n1,2+n2,*2,all"
    """
    st, nt = listed(stages), str(notes).split("|")
    nt += [""] * (len(st) - len(nt))
    cs = [th.color(c) for c in listed(cols, ",")] or [th.color("blue")] * len(st)
    cs += [cs[-1]] * (len(st) - len(cs))
    bw, bh, gap = 3.2, .62, .3
    boxes, notes_, arrows = VGroup(), VGroup(), VGroup()
    top = 0.0
    for i, (s, n, c) in enumerate(zip(st, nt, cs)):
        label = lec.text(s, bw - .25, size=th.LABEL_SIZE, color=c, align=r"\Centering")
        note = lec.text(n, 4.2, size=th.LABEL_SIZE, color=th.DIM) if n else VMobject()
        h = max(bh, label.height + .2, note.height + .1 if n else 0)   # a long label or note makes its row taller
        box = RoundedRectangle(corner_radius=.1, width=bw, height=h).set_fill(c, .12) \
            .set_stroke(c, 2.5).move_to(UP * (top - h / 2))
        top -= h + gap
        boxes.add(VGroup(box, label.move_to(box)))
        notes_.add(note.next_to(box, RIGHT, buff=.3) if n else note)
        if i:
            arrows.add(Arrow(boxes[i - 1].get_bottom(), box.get_top(), buff=.04, color=th.DIM, stroke_width=3,
                             max_tip_length_to_length_ratio=.35))
    lec.fit(VGroup(boxes, arrows, *[x for x in notes_ if x.has_points() or len(x)]))
    lec.play(FadeIn(boxes[0], shift=DOWN * .1))
    def anim(k):
        if k == "all":
            return LaggedStart(*[pulse(x[0], th.HL) for x in boxes], lag_ratio=.1)
        if k[0] == "n":
            return FadeIn(notes_[int(k[1:])], shift=LEFT * .15)
        if k[0] == "*":
            return pulse(boxes[int(k[1:])][0], th.HL)
        i = int(k)
        return Succession(GrowArrow(arrows[i - 1]), FadeIn(boxes[i], shift=DOWN * .1))
    for k in listed(order, ","):
        yield
        lec.play(LaggedStart(*[anim(x) for x in k.split("+")], lag_ratio=.5), run_time=1.2)
