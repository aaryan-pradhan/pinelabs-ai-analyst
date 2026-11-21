"""Midpoint (symmetric) mix-vs-rate decomposition of a Success rate change.

With s = a Segment's share of Attempts and r = its Success rate:
  Mix effect  = sum (s1 - s0)(r0 + r1)/2
  Rate effect = sum (r1 - r0)(s0 + s1)/2
They sum exactly to the total change, sum s1*r1 - sum s0*r0.
"""


def decompose(base, current):
    """base, current: {segment: (attempts, success_rate)}."""
    n0 = sum(a for a, _ in base.values())
    n1 = sum(a for a, _ in current.values())
    segments = []
    for seg in sorted(base.keys() | current.keys()):
        # A Segment absent from one period has share 0 there; its rate then drops out.
        a0, r0 = base.get(seg, (0, 0.0))
        a1, r1 = current.get(seg, (0, 0.0))
        s0, s1 = a0 / n0, a1 / n1
        segments.append({
            "segment": seg, "share_before": s0, "share_after": s1,
            "rate_before": r0, "rate_after": r1,
            "mix": (s1 - s0) * (r0 + r1) / 2,
            "rate": (r1 - r0) * (s0 + s1) / 2,
        })
    return {
        "total": sum(s["share_after"] * s["rate_after"] - s["share_before"] * s["rate_before"]
                     for s in segments),
        "mix": sum(s["mix"] for s in segments),
        "rate": sum(s["rate"] for s in segments),
        "segments": segments,
    }
