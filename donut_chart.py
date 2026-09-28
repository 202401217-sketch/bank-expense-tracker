"""
"Where it went" donut card.

Builds the spending-by-category chart as a self-contained HTML/SVG
card (dark background, rounded segments with gaps, legend on the
right) and shows it in Streamlit.
"""

import math
from html import escape


# Colours for the biggest categories, in order. Anything after
# these is shown in a muted grey, like small slices usually are.
PALETTE = [
    "#CBA650",  # gold
    "#44A06A",  # green
    "#C9714E",  # terracotta
    "#6796B8",  # blue
    "#C5708D",  # pink
    "#3F9A8E",  # teal
    "#E9A15C",  # orange
    "#9B87C4",  # lavender
    "#B3B14E",  # olive
    "#C85F5F",  # red
    "#D8D2C0",  # cream
    "#4F7A8A",  # slate
]
MUTED = "#6A665E"

SIZE = 560          # SVG canvas
CENTER = SIZE / 2
OUTER = 272         # outer radius
INNER = 172         # inner radius
GAP = 13          # space between slices, in px (includes the rounded edge)
CORNER = 5          # rounded corners


def indian_rupees(amount):
    """₹12,34,567 style grouping."""

    amount = int(round(amount))
    sign = "-" if amount < 0 else ""
    digits = str(abs(amount))

    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        digits = ",".join(groups) + "," + tail

    return f"{sign}₹{digits}"


def _point(radius, angle):
    # angle 0 = 12 o'clock, clockwise
    return (
        CENTER + radius * math.sin(angle),
        CENTER - radius * math.cos(angle),
    )


def _slice_path(start, end):
    """Ring segment with a constant-width gap on both sides."""

    def edge(radius):
        shift = math.asin(min(1, (GAP / 2) / radius))
        a, b = start + shift, end - shift
        if b <= a:  # slice thinner than the gap: collapse to a line
            a = b = (start + end) / 2
        return a, b

    o1, o2 = edge(OUTER - CORNER / 2)
    i1, i2 = edge(INNER + CORNER / 2)

    R, r = OUTER - CORNER / 2, INNER + CORNER / 2
    large_o = 1 if (o2 - o1) > math.pi else 0
    large_i = 1 if (i2 - i1) > math.pi else 0

    x1, y1 = _point(R, o1)
    x2, y2 = _point(R, o2)
    x3, y3 = _point(r, i2)
    x4, y4 = _point(r, i1)

    return (
        f"M{x1:.2f},{y1:.2f} "
        f"A{R},{R} 0 {large_o} 1 {x2:.2f},{y2:.2f} "
        f"L{x3:.2f},{y3:.2f} "
        f"A{r},{r} 0 {large_i} 0 {x4:.2f},{y4:.2f} Z"
    )


def donut_html(by_category, title, subtitle=""):
    """by_category: DataFrame with Category and Amount (positive), largest first."""

    data = by_category.sort_values("Amount", ascending=False)
    total = float(data["Amount"].sum())

    slices, rows = [], []
    angle = 0.0

    for i, (name, amount) in enumerate(zip(data["Category"], data["Amount"])):

        colour = PALETTE[i] if i < len(PALETTE) else MUTED
        share = amount / total if total else 0
        sweep = share * 2 * math.pi

        if len(data) == 1:
            # A single category: draw a full ring.
            mid = (OUTER + INNER) / 2
            slices.append(
                f'<circle cx="{CENTER}" cy="{CENTER}" r="{mid}" fill="none" '
                f'stroke="{colour}" stroke-width="{OUTER - INNER}"><title>'
                f'{escape(str(name))}: {indian_rupees(amount)}</title></circle>'
            )
        else:
            slices.append(
                f'<path d="{_slice_path(angle, angle + sweep)}" fill="{colour}" '
                f'stroke="{colour}" stroke-width="{CORNER}" stroke-linejoin="round">'
                f'<title>{escape(str(name))}: {indian_rupees(amount)} '
                f'({share * 100:.1f}%)</title></path>'
            )

        angle += sweep

        rows.append(
            f'<li><span class="dot" style="background:{colour}"></span>'
            f'<span class="name">{escape(str(name))}</span>'
            f'<span class="pct">{share * 100:.1f}%</span>'
            f'<span class="amt">{indian_rupees(amount)}</span></li>'
        )

    return f"""<!doctype html>
<html><head><meta charset="utf-8">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Playfair+Display:wght@500;600&display=swap" rel="stylesheet">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ background: transparent; }}
  body {{ font-family: Inter, system-ui, -apple-system, "Segoe UI", sans-serif; color: #EDEAE3; }}
  .card {{
    background: #1A1A1A; border: 1px solid #2E2E2E; border-radius: 28px;
    padding: 44px 56px; display: flex; flex-wrap: wrap; gap: 40px 64px;
    align-items: center;
  }}
  .chart {{ flex: 1 1 300px; max-width: 520px; position: relative; margin: 0 auto; }}
  .chart svg {{ width: 100%; height: auto; display: block; }}
  .centre {{
    position: absolute; inset: 0; display: flex; flex-direction: column;
    align-items: center; justify-content: center; pointer-events: none;
  }}
  .centre small {{ font-size: 13px; letter-spacing: .28em; color: #A39E92; font-weight: 500; }}
  .centre strong {{ font-family: "Playfair Display", Georgia, serif; font-weight: 600;
    font-size: clamp(28px, 5.5vw, 40px); margin-top: 10px; color: #F5F2EA; }}
  .legend {{ flex: 1 1 340px; min-width: 0; }}
  .eyebrow {{ font-size: 13px; letter-spacing: .24em; color: #CBA650; font-weight: 600; }}
  h2 {{ font-family: "Playfair Display", Georgia, serif; font-weight: 600;
    font-size: clamp(26px, 4vw, 40px); margin: 14px 0 8px; color: #F5F2EA; }}
  .sub {{ color: #8F8A80; font-size: 15px; margin-bottom: 26px; }}
  ul {{ list-style: none; }}
  li {{ display: grid; grid-template-columns: 14px 1fr 70px 100px; gap: 18px;
    align-items: center; padding: 9px 0; font-size: 17px; }}
  .dot {{ width: 13px; height: 13px; border-radius: 50%; }}
  .name {{ font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
  .pct {{ color: #8F8A80; text-align: right; font-variant-numeric: tabular-nums; }}
  .amt {{ font-weight: 600; text-align: right; font-variant-numeric: tabular-nums; }}
  @media (max-width: 560px) {{
    .card {{ padding: 28px 20px; }}
    li {{ grid-template-columns: 12px 1fr 56px 80px; gap: 12px; font-size: 15px; }}
  }}
</style></head>
<body>
  <div class="card">
    <div class="chart">
      <svg viewBox="0 0 {SIZE} {SIZE}" role="img" aria-label="Spending by category">
        {''.join(slices)}
      </svg>
      <div class="centre"><small>SPENT</small><strong>{indian_rupees(total)}</strong></div>
    </div>
    <div class="legend">
      <div class="eyebrow">WHERE IT WENT</div>
      <h2>{escape(title)}</h2>
      <div class="sub">{escape(subtitle)}</div>
      <ul>{''.join(rows)}</ul>
    </div>
  </div>
</body></html>"""


def show_donut(by_category, title, subtitle=""):
    """Render the card in Streamlit."""

    import streamlit.components.v1 as components

    height = max(640, 300 + 40 * len(by_category))

    components.html(
        donut_html(by_category, title, subtitle),
        height=height,
        scrolling=True,
    )
