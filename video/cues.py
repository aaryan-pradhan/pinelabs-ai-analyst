"""The cue sheet: what happens on screen, keyed to the word in the voice that names it.

A cue is (when, action, *args). `when` is a phrase (its first word's start), (phrase, seconds
offset), or seconds into the chapter's trimmed voice. Edit here to act on timed notes.
"""
import json
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).parent
LEAD, TAIL, END_HOLD = 0.4, 0.7, 2.5  # silence kept before and after each chapter's words; hold on the last frame
APP = "[data-testid=stTextInput] input"
ROLE = "[data-testid=stSidebar] [data-testid=stSelectbox] >> nth=0"


def option(text):
    return f'[role=option]:has-text("{text}")'


HEADLINE = {"zoom": 1.7}
CUES = {
    0: [(("its monday", -0.1), "js", "on('monday')"),  # each card line appears on the words that say it
        ("you run payments", "js", "on('you')"),
        ("your dashboard says", "js", "on('dash')"),
        ("fell four points", "js", "on('fell')"),
        ("your ceo", "js", "on('ceo')"),
        ("pine labs asked", "js", "on('goal')"),
        (("pine labs asked", 1.0), "js", "on('g')"),
        ("here is", "split")],  # the card ends; the app's opening page begins
    1: [("so we ask", "ask", "Why did success rate drop in week 6?", "week 6"),
        ("the headline", "cam", {"a": "SUCCESS RATE FELL 4.0", "n": 2, **HEADLINE}),
        ("then the evidence", "cam", {"a": "FACTS CLICK A FACT", "n": 6, "zoom": 1.6}),
        ("every number", "click", "summary:has-text('Success rate Week 5')"),
        ("cites its table", "cam", {"a": "SUCCESS RATE WEEK 5 92.66%", "b": "SELECT", "zoom": 1.6}),
        ("the hypotheses", "cam", {"a": "HYPOTHESES WRITTEN", "n": 5, "zoom": 1.6}),
        ("the recommendations", "cam", {"a": "RECOMMENDATIONS WRITTEN", "n": 6, "zoom": 1.6}),
        ("here is the exact", "cam", {"sel": "details[open] pre", "zoom": 1.8}),
        ("look at the chart", "cam", {"a": "EXHIBIT A: WHY IT MOVED", "n": 10, "zoom": 1.5}),
        ("mixed effect", "cam", {"a": "MIX EFFECT -3.99", "zoom": 2.0, "pad": 80})],
    3: [(-0.5, "cam", {"full": True, "top": True, "dur": 10}),
        ("we ask", "ask", "Which bank got worse on cards in wk7?", "week 7"),
        ("the answer is different", "cam", {"a": "COASTAL BANK GOT WORSE", "n": 2, **HEADLINE}),
        ("the drop is inside", "cam", {"a": "HOW THE BANK EXPLAINS", "n": 11, "zoom": 1.5}),
        ("coaster bank", "cam", {"a": "COASTAL BANK RATE EFFECT", "zoom": 2.0, "pad": 80}),
        ("the recommendations", "cam", {"a": "RECOMMENDATIONS WRITTEN", "n": 5, "zoom": 1.6})],
    4: [("your ceo", "ask", "How's success rate lately?", "lately"),
        ("that vague", "cam", {"a": "COMPARING THE LATEST", "b": "WINDOW:", **HEADLINE}),
        ("states its", "cam", {"a": "WINDOW:", "zoom": 2.0, "pad": 120}),
        ("change it right", "click", "[data-testid=stPopoverButton]:has-text('Window')"),
        ("and the answer", "key", "Escape"),
        (("and the answer", 0.2), "cam", {"a": "COMPARING THE LATEST", "n": 2, **HEADLINE}),
        ("coastal bank is back", "cam", {"a": "COASTAL BANK RECOVERING", "zoom": 2.0, "pad": 100})],
    5: [("next finance asks", "ask", "Do settlements match transactions in wk5?", "money match"),
        ("the analyst checks", "cam", {"a": "ELECTRONICS SETTLEMENTS IN WEEK 5", "n": 1, **HEADLINE}),
        ("category by category", "cam", {"a": "EXHIBIT A: BY CATEGORY", "n": 9, "zoom": 1.6}),
        ("electronics merchants", "cam", {"a": "ELECTRONICS -3.00%", "zoom": 2.0, "pad": 90})],
    6: [("now a different", "clear"),
        ("logs in", "click", ROLE),
        ("merchant manager", "click", option("Merchant manager")),
        ("for grocery", "cam", {"a": "SIGNED IN AS", "b": "CATEGORY", "zoom": 1.8, "pad": 40}),
        ("the garden turns", "cam", {"full": True, "dur": 1600}),
        (("they ask for the settlements", -2.0), "ask", "Show me settlements", "settlements"),
        ("i refuse with", "cam", {"a": "REJECTED", "b": "SELECT * FROM SETTLEMENTS", "zoom": 1.6}),
        (("they ask for electronics", -1.5), "ask", "What is the success rate for electronics?", "electronics"),
        ("refuse again", "cam", {"a": "REJECTED", "n": 3, **HEADLINE}),
        ("checked on the sql", "cam", {"a": "SQL VALIDATOR ENFORCES", "zoom": 2.0, "pad": 60})],
    7: [(0.0, "cam", {"full": True, "dur": 900}),
        (("then someone", 0.6), "click", ROLE),
        (("then someone", 1.3), "click", option("Analyst")),
        (("delete the failed", -1.2), "ask", "Delete the failed transactions", "transactions"),
        ("the analyst refuses", "cam", {"a": "REJECTED", "b": "DELETE FROM", "zoom": 1.6})],
    # Its answer holds a table, which sizes itself when drawn: ask zoomed out or it draws too wide.
    8: [("last question", "ask", "How many duplicate transactions are there?", "messy", {"full": True, "top": True}),
        ("this data has", "cam", {"a": "THERE ARE 2,252 DUPLICATES", "zoom": 2.0, "pad": 90}),
        ("and it is tested", "cam", {"full": True, "top": True, "dur": 900}),
        (("and it is tested", 0.5), "click", "[data-testid=stSidebar] button:has-text('Run eval')"),
        ("10 questions", "cam", {"sel": "[data-testid=stExpander]", "zoom": 1.6}),
        ("10 out of 10", "cam", {"sel": "[data-testid=stExpander] summary", "zoom": 2.0, "pad": 60})],
}
MANIM = {2, 9}  # chapters drawn as animations, not recorded
LEADS = {"cam": 0.3, "ask": 0.15, "click": 0.6}  # start this early so the action lands on its word


def tokens(s):
    return [t for t in (re.sub(r"[^a-z0-9]", "", w.lower()) for w in s.split()) if t]


def words(c):
    """[(token, start, end)] for chapter c, dropping tokens that are only punctuation."""
    out = []
    for w, a, b in json.loads((HERE / "words" / f"ch{c}.json").read_text()):
        out += [(t, a, b) for t in tokens(w)]
    return out


def seconds(c, phrase, after=0.0, end=False):
    ws, ph = words(c), tokens(phrase)
    for i in range(len(ws) - len(ph) + 1):
        if ws[i][1] >= after and [w for w, *_ in ws[i:i + len(ph)]] == ph:
            return ws[i + len(ph) - 1][2] if end else ws[i][1]
    raise KeyError(f"ch{c}: {phrase!r} not in the voice")


def wav_seconds(c):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                          str(HERE / "voice" / f"ch{c}.wav")], capture_output=True, text=True, check=True).stdout
    return float(out)


def timeline():
    """Each chapter's trimmed voice, its place in the video, and its cues in its own seconds.

    Returns [{c, trim: (a, b), start, dur, cues: [(t, action, args)]}]; t counts from the
    chapter's trimmed start, and an action's lead is already taken off.
    """
    out, start = [], 0.0
    for c in range(10):
        ws = words(c)
        a = max(0.0, ws[0][1] - LEAD)
        b = min(wav_seconds(c), ws[-1][2] + TAIL)
        dur = b - a + (END_HOLD if c == 9 else 0)
        resolved = []
        for when, action, *args in CUES.get(c, []):
            phrase, off = when if isinstance(when, tuple) else (when, 0.0)
            t = off if isinstance(phrase, (int, float)) else seconds(c, phrase) - a + off
            if action == "ask":  # type until the spoken question ends
                text, until, *view = args
                args = [text, seconds(c, until, after=t + a, end=True) - a - t, *view]
            resolved.append((round(t - LEADS.get(action, 0.0), 3), action, args))
        out.append({"c": c, "trim": (a, b), "start": start, "dur": dur, "cues": sorted(resolved, key=lambda r: r[0])})
        start += dur
    return out


if __name__ == "__main__":
    for ch in timeline():
        print(f"ch{ch['c']}  {ch['start']:6.2f}s  +{ch['dur']:5.2f}s")
        for t, action, args in ch["cues"]:
            print(f"      {t:6.2f}  {action:6} {str(args)[:80]}")
