"""Instant-read schematic: four-panel story of two ways to read one forecast.

Layout is fixed to a 2 x 2 grid inside a 1180 x 720 canvas so nothing can clip.
Arrows are explicit polygons (robust). The risk quantity is drawn as a
horizontal probability bar, which reads at a glance. The probability value in
panel 4 is the real fitted P(exceedance | m = 13 m/s) from the 2021-2023 fit.
"""
from pathlib import Path

import drawsvg as dw
import pandas as pd

from calibration import BinnedCalibrator

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper_figures" / "output"

W, H = 1180, 720
MARGIN, GAP = 50, 40
PW = (W - 2 * MARGIN - GAP) // 2          # 520
PH = 250
ROW_Y = [78, 78 + PH + 34]

F = "Helvetica, Arial, sans-serif"
INK = "#1e293b"
BLUE = "#1d4ed8"
SLATE = "#52606d"
AMBER = "#b45309"
RED = "#c53030"
GREEN = "#2f855a"
PURPLE = "#6b46c1"
SOFT = "#f8fafc"
LINE = "#94a3b8"

frame = pd.read_csv(ROOT / "outputs" / "epochs_multi2.csv",
                    usecols=["split", "block_max_L12", "L12_thr12.0"])
fit = frame[frame["split"] == "FIT"]
model = BinnedCalibrator().fit(fit["block_max_L12"].to_numpy(float),
                               fit["L12_thr12.0"].to_numpy(float))
P13 = float(model.predict([13.0])[0])

d = dw.Drawing(W, H)


def arrow(x1, y1, x2, y2, color, width=2.4):
    d.append(dw.Line(x1, y1, x2, y2, stroke=color, stroke_width=width))
    import math
    ang = math.atan2(y2 - y1, x2 - x1)
    size = 11
    p1 = (x2, y2)
    p2 = (x2 - size * math.cos(ang - 0.38), y2 - size * math.sin(ang - 0.38))
    p3 = (x2 - size * math.cos(ang + 0.38), y2 - size * math.sin(ang + 0.38))
    d.append(dw.Lines(p1[0], p1[1], p2[0], p2[1], p3[0], p3[1], close=True, fill=color))


def panel(x, y, title, color):
    d.append(dw.Rectangle(x, y, PW, PH, rx=12, fill=SOFT, stroke=LINE, stroke_width=1.2))
    d.append(dw.Text(title, 14.5, x + 22, y + 30, fill=color, font_family=F, font_weight="bold"))


def caption(x, y, text, color=INK):
    d.append(dw.Text(text, 11.5, x + 22, y + PH - 18, fill=color, font_family=F))


def card(cx, cy, value, color):
    d.append(dw.Rectangle(cx - 58, cy - 40, 116, 80, rx=9, fill="white",
                          stroke=color, stroke_width=2.2))
    for i, dy in enumerate((-24, -14, -4)):
        d.append(dw.Line(cx - 40, cy + dy, cx - 16, cy + dy, stroke=color,
                         stroke_width=1.6, stroke_opacity=0.55))
        d.append(dw.Line(cx + 16, cy + dy, cx + 40, cy + dy, stroke=color,
                         stroke_width=1.6, stroke_opacity=0.55))
    d.append(dw.Text(value, 16, cx, cy + 26, center=True, fill=color,
                     font_family=F, font_weight="bold"))


def crane(cx, cy, s, color, idle=False):
    d.append(dw.Line(cx, cy + 34 * s, cx, cy - 34 * s, stroke=color, stroke_width=3.0 * s))
    d.append(dw.Line(cx - 6 * s, cy + 34 * s, cx + 6 * s, cy + 34 * s, stroke=color, stroke_width=3.0 * s))
    d.append(dw.Line(cx, cy - 34 * s, cx + 30 * s, cy - 38 * s, stroke=color, stroke_width=3.0 * s))
    d.append(dw.Line(cx, cy - 26 * s, cx - 14 * s, cy - 36 * s, stroke=color, stroke_width=1.6 * s))
    d.append(dw.Line(cx + 20 * s, cy - 38 * s, cx + 20 * s, cy - 10 * s, stroke=color, stroke_width=1.5 * s))
    d.append(dw.Rectangle(cx + 15 * s, cy - 10 * s, 10 * s, 12 * s, fill="none",
                          stroke=color, stroke_width=1.5 * s))
    if idle:
        d.append(dw.Text("zz", 11 * s, cx + 30 * s, cy - 6 * s, fill=SLATE,
                         font_family=F, font_style="italic"))


def gust(cx, cy, s, color):
    for dy in (-22, 0, 22):
        arrow(cx - 26 * s, cy + dy - 6 * s, cx + 10 * s, cy + dy + 8 * s, color, width=2.6 * s)


def prob_bar(cx, cy, p, color, width=170, height=26, pstar=0.20):
    d.append(dw.Rectangle(cx - width / 2, cy - height / 2, width, height, rx=6,
                          fill="white", stroke=SLATE, stroke_width=1.4))
    d.append(dw.Rectangle(cx - width / 2, cy - height / 2, width * p, height, rx=6,
                          fill=color))
    xs = cx - width / 2 + width * pstar
    d.append(dw.Line(xs, cy - height / 2 - 6, xs, cy + height / 2 + 6,
                     stroke=INK, stroke_width=1.6, stroke_dasharray="4 3"))
    d.append(dw.Text("C/L", 10, xs + 6, cy - height / 2 - 10, fill=INK, font_family=F))
    d.append(dw.Text(f"P(exceedance) = {p:.2f}", 12.5, cx, cy + height / 2 + 20,
                     center=True, fill=color, font_family=F, font_weight="bold"))


def label(cx, cy, text, color=INK, size=11.5, bold=False):
    d.append(dw.Text(text, size, cx, cy, center=True, fill=color, font_family=F,
                     font_weight="bold" if bold else "normal"))


# ---------------- Panel 1 ----------------
x, y = MARGIN, ROW_Y[0]
panel(x, y, "1  TODAY: the forecast says light wind", BLUE)
card(x + 120, y + 118, "9 m/s", BLUE)
arrow(x + 186, y + 118, x + 252, y + 118, SLATE)
crane(x + 320, y + 118, 1.0, BLUE)
label(x + 320, y + 186, "work starts", BLUE, 13, True)
caption(x, y, "raw rule: 9 < 12  ->  go.  Looks safe.", INK)

# ---------------- Panel 2 ----------------
x = MARGIN + PW + GAP
panel(x, y, "2  BUT the window really hits 14 m/s", RED)
card(x + 120, y + 118, "9 m/s", BLUE)
gust(x + 268, y + 118, 1.0, RED)
label(x + 268, y + 186, "actual 14 m/s", RED, 13, True)
crane(x + 400, y + 118, 0.95, SLATE)
d.append(dw.Circle(x + 430, y + 74, 13, fill=RED))
label(x + 430, y + 79, "!", "white", 16, True)
caption(x, y, "the lift is interrupted mid-window: unsafe, rework, delay.", RED)

# ---------------- Panel 3 ----------------
x, y = MARGIN, ROW_Y[1]
panel(x, y, "3  OR the forecast says strong wind", AMBER)
card(x + 120, y + 118, "13 m/s", AMBER)
arrow(x + 186, y + 118, x + 252, y + 118, SLATE)
crane(x + 320, y + 118, 1.0, SLATE, idle=True)
label(x + 320, y + 186, "stopped all day", AMBER, 13, True)
caption(x, y, "the window stayed calm: a wasted day, no safety gain.", AMBER)

# ---------------- Panel 4 ----------------
x = MARGIN + PW + GAP
panel(x, y, "4  THIS PAPER: convert it to an event probability first", GREEN)
card(x + 96, y + 112, "13 m/s", AMBER)
arrow(x + 158, y + 112, x + 196, y + 112, GREEN)
prob_bar(x + 300, y + 112, P13, GREEN, width=170, pstar=0.60)
arrow(x + 392, y + 112, x + 428, y + 112, GREEN)
crane(x + 462, y + 108, 0.75, GREEN)
label(x + 300, y + 178, "cost-loss ratio C/L = 0.60  (site choice)", PURPLE, 10.5)
label(x + 300, y + 196, "fitted on 2021-2023 data only", SLATE, 10)
label(x + 462, y + 178, "decide by risk", GREEN, 11.5, True)
caption(x, y, "the same forecast becomes a calibrated risk the site can set.", GREEN)

# ---------------- Takeaway banner ----------------
by = ROW_Y[1] + PH + 22
d.append(dw.Rectangle(MARGIN, by, W - 2 * MARGIN, 40, rx=9, fill="#eef7f0",
                      stroke=GREEN, stroke_width=1.4))
label(W / 2, by + 26,
      "Two ways to read one forecast:  compare values (1-3)   vs   estimate the event probability (4).",
      GREEN, 14, True)
d.save_svg(OUT / "fig1_forecast_decision_mechanism.svg")

import cairosvg
cairosvg.svg2pdf(url=str(OUT / "fig1_forecast_decision_mechanism.svg"),
                 write_to=str(OUT / "fig1_forecast_decision_mechanism.pdf"))
cairosvg.svg2png(url=str(OUT / "fig1_forecast_decision_mechanism.svg"),
                 write_to=str(OUT / "fig1_forecast_decision_mechanism.png"), scale=2.0)
print(f"schematic written; P(exceedance | 13 m/s) = {P13:.3f}")
