"""Static SVG figures for the slides, docs and product site, computed from batch records.

Two themes: light for slides and docs (series in the zone blue and orange) and dark
for the site (series in a deep cyan and a periwinkle from the logo's family). Each
pair passes the colour-vision checks on its surface; text stays in ink colours,
every mark carries a tooltip, and two-series charts have a legend.
"""
import math
from collections import namedtuple
from html import escape

from loopwright.batch import p50_p95

Theme = namedtuple("Theme", "surface ink ink2 muted grid a b")
THEMES = {
    "light": Theme("#FFFFFF", "#18202B", "#4B5664", "#6B7480", "#E3E7E5", "#2A78D6", "#EB6834"),
    "dark": Theme("#000000", "#FFFFFF", "#C9D1DA", "#9AA5B1", "#26303C", "#0AA5C8", "#6A7DFF"),
}
FONT = "system-ui, 'Segoe UI', sans-serif"
BUCKETS = ("0", "1", "2", "3+")
SOLVED = ("valid", "invalid")


def extra_hub_counts(rows, key):
    """Feasible plans by how many hubs `key` uses above the lower bound: 0, 1, 2, 3+."""
    counts = dict.fromkeys(BUCKETS, 0)
    for r in rows:
        if r["status"] in SOLVED and r.get(key) is not None:
            extra = r[key] - r["hub_lower_bound"]
            counts[BUCKETS[min(extra, 3)]] += 1
    return counts


def _nice(top, ticks):
    """The smallest axis maximum at or above top whose `ticks` equal steps are round numbers."""
    if top <= 0:
        return ticks
    raw = top / ticks
    power = 10 ** math.floor(math.log10(raw))
    return ticks * next(m * power for m in (1, 2, 2.5, 4, 5, 10) if m * power >= raw)


def _count(n, noun):
    return f"{n:,} {noun}{'' if n == 1 else 's'}"


def _compact(v):
    return f"{v / 1000:g}K" if v >= 1000 else f"{v:g}"


def _column(x, base, top, w, r=4):
    """A column with a rounded data end and a square foot on the baseline."""
    r = min(r, (base - top) / 2, w / 2)
    if r <= 0:
        return f"M{x:.1f},{base:.1f} L{x + w:.1f},{base:.1f} Z"
    return (f"M{x:.1f},{base:.1f} L{x:.1f},{top + r:.1f} Q{x:.1f},{top:.1f} {x + r:.1f},{top:.1f} "
            f"L{x + w - r:.1f},{top:.1f} Q{x + w:.1f},{top:.1f} {x + w:.1f},{top + r:.1f} L{x + w:.1f},{base:.1f} Z")


def _frame(width, height, title, subtitle, c):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" font-family="{FONT}" role="img" '
            f'aria-label="{escape(title)}">',
            f'<rect width="{width}" height="{height}" fill="{c.surface}"/>',
            f'<text x="24" y="32" font-size="18" font-weight="600" fill="{c.ink}">{escape(title)}</text>',
            f'<text x="24" y="54" font-size="13" fill="{c.ink2}">{escape(subtitle)}</text>']


def extra_hubs_chart(rows, width=720, height=420, theme="light"):
    c = THEMES[theme]
    exact, greedy = extra_hub_counts(rows, "hubs"), extra_hub_counts(rows, "hubs_greedy")
    n = sum(exact.values())
    left, right, top, bottom = 64, 24, 96, 56
    plot_w, plot_h = width - left - right, height - top - bottom
    base, ymax = top + plot_h, _nice(max(list(exact.values()) + list(greedy.values())), 4)
    y = lambda v: base - plot_h * v / ymax
    parts = _frame(width, height, "Hubs above the lower bound, per plan",
                   f"{n:,} feasible plans, exact minimum against the greedy baseline", c)
    for k in range(5):
        v = ymax * k / 4
        parts.append(f'<line x1="{left}" x2="{width - right}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="{c.grid}" stroke-width="1"/>')
        parts.append(f'<text x="{left - 8}" y="{y(v) + 4:.1f}" font-size="12" fill="{c.muted}" text-anchor="end">{_compact(v)}</text>')
    for i, (label, colour) in enumerate((("Exact", c.a), ("Greedy", c.b))):
        lx = 24 + i * 110
        parts.append(f'<rect x="{lx}" y="68" width="12" height="12" rx="2" fill="{colour}"/>')
        parts.append(f'<text x="{lx + 18}" y="78" font-size="13" fill="{c.ink}">{label}</text>')
    band, w, gap = plot_w / len(BUCKETS), 44, 2  # wide enough for two five-digit labels side by side
    for b, bucket in enumerate(BUCKETS):
        cx = left + band * (b + 0.5)
        for s, (label, counts, colour) in enumerate((("Exact", exact, c.a), ("Greedy", greedy, c.b))):
            x = cx - w - gap / 2 + s * (w + gap)
            v = counts[bucket]
            parts.append(f'<path class="bar" d="{_column(x, base, y(v), w)}" fill="{colour}">'
                         f'<title>{label}: {_count(v, "plan")} with {bucket} hub{"" if bucket == "1" else "s"} above the bound'
                         f'</title></path>')
            if bucket == "0":  # label the bucket the story is about, not every column
                parts.append(f'<text x="{x + w / 2:.1f}" y="{y(v) - 6:.1f}" font-size="12" fill="{c.ink}" '
                             f'text-anchor="middle">{v:,}</text>')
        parts.append(f'<text x="{cx:.1f}" y="{base + 20}" font-size="13" fill="{c.ink2}" text-anchor="middle">{bucket}</text>')
    parts.append(f'<line x1="{left}" x2="{width - right}" y1="{base}" y2="{base}" stroke="{c.muted}" stroke-width="1"/>')
    parts.append(f'<text x="{left + plot_w / 2:.1f}" y="{height - 14}" font-size="12" fill="{c.muted}" '
                 f'text-anchor="middle">hubs above the lower bound</text>')
    return "\n".join(parts + ["</svg>"]) + "\n"


def runtime_chart(times, width=720, height=380, label="single process", theme="light"):
    c = THEMES[theme]
    t = sorted(times)
    n = len(t)
    p50, p95 = p50_p95(t)
    left, right, top, bottom = 64, 32, 76, 56
    plot_w, plot_h = width - left - right, height - top - bottom
    # The axis stops just above the 99th percentile, so one slow plan can't squash the curve.
    base, xmax = top + plot_h, _nice(t[math.ceil(0.99 * n) - 1], 5)
    x = lambda v: left + plot_w * v / xmax
    y = lambda share: base - plot_h * share
    parts = _frame(width, height, "Solve time per plan",
                   f"Share of {n:,} plans solved within each time, {label}", c)
    for k in range(5):
        parts.append(f'<line x1="{left}" x2="{width - right}" y1="{y(k / 4):.1f}" y2="{y(k / 4):.1f}" stroke="{c.grid}" stroke-width="1"/>')
        parts.append(f'<text x="{left - 8}" y="{y(k / 4) + 4:.1f}" font-size="12" fill="{c.muted}" text-anchor="end">{k * 25}%</text>')
    for k in range(6):
        v = xmax * k / 5
        parts.append(f'<text x="{x(v):.1f}" y="{base + 20}" font-size="12" fill="{c.muted}" text-anchor="middle">{v:g} s</text>')
    step = max(1, n // 400)
    shown = [v for v in t if v <= xmax]
    pts = [(x(v), y((i + 1) / n)) for i, v in enumerate(shown) if i % step == 0 or i == len(shown) - 1]
    parts.append(f'<polyline class="cdf" points="{" ".join(f"{a:.1f},{b:.1f}" for a, b in pts)}" fill="none" '
                 f'stroke="{c.a}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>')
    for name, v in (("p50", p50), ("p95", p95)):
        share = (t.index(v) + 1) / n
        cx, cy = x(v), y(share)
        parts.append(f'<circle class="marker" cx="{cx:.1f}" cy="{cy:.1f}" r="4" fill="{c.a}" stroke="{c.surface}" '
                     f'stroke-width="2"><title>{name}: {v:.2f} s ({share:.0%} of plans)</title></circle>')
        # Below and to the right of the marker: a rising curve never passes there.
        parts.append(f'<text x="{cx + 10:.1f}" y="{cy + 18:.1f}" font-size="13" fill="{c.ink}">{name} {v:.2f} s</text>')
    if t[-1] > xmax:
        parts.append(f'<text x="{width - right}" y="{top - 8}" font-size="12" fill="{c.muted}" '
                     f'text-anchor="end">slowest plan: {t[-1]:.1f} s</text>')
    parts.append(f'<line x1="{left}" x2="{width - right}" y1="{base}" y2="{base}" stroke="{c.muted}" stroke-width="1"/>')
    return "\n".join(parts + ["</svg>"]) + "\n"
