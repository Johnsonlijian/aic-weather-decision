"""Top-journal mechanism figure for the weather-window decision paper.

Design brief
------------
Role:       Fig. 1 object-problem-mechanism map (top-journal figure set #1).
Takeaway:   The raw gust threshold misreads the window event; calibrating the
            event repairs it. (5-10 s read.)
Object:     Tower-crane segment lift with a sourced in-service limit.
Driver:     Archived as-issued gust forecast behind an audited 4 h publication
            boundary.
Mechanism:  An instantaneous grid-point gust is compared "as equals" with the
            event "any hour of the window exceeds the limit".
Response:   Raw rule misses 45-63% of true events and alarms on 6.9% of safe
            blocks; calibration recovers held-out skill and decision value.
Evidence:   Numbers come from the 2025 held-out split (Table 1, Figs. 2-4).
Boundary:   The diagram is schematic; the averaging interval of the crane limit
            is undocumented and swept, not resolved.
Export:     SVG (source of truth) + PDF + PNG via cairosvg.
"""
from pathlib import Path

import cairosvg
import drawsvg as dw

OUT = Path(__file__).resolve().parents[1] / "paper_figures" / "output"

W, H = 1180, 640
d = dw.Drawing(W, H, origin=(0, 0), displayInline=False)
d.set_pixel_scale(1.0)

F = "Helvetica, Arial, sans-serif"
INK = "#1e293b"
PAL = {
    "object": "#1d4ed8",
    "driver": "#52606d",
    "misread": "#b45309",
    "fail": "#c53030",
    "repair": "#2f855a",
    "outcome": "#6b46c1",
    "imply": "#0f172a",
    "soft": "#f8fafc",
    "line": "#94a3b8",
}


def box(x, y, w, h, fill, title, title_color, lines, line_h=16):
    d.append(dw.Rectangle(x, y, w, h, rx=9, ry=9,
                          fill=fill, stroke=title_color, stroke_width=1.8))
    d.append(dw.Text(title, 15, x + w / 2, y + 26, center=True, fill=title_color,
                     font_family=F, font_weight="bold", letter_spacing=0.6))
    ty = y + 52
    for line in lines:
        d.append(dw.Text(line, 11.5, x + w / 2, ty, center=True, fill=INK,
                         font_family=F))
        ty += line_h
    return (x, y, w, h)


def arrow(x1, y1, x2, y2, color, label=None, lx=None, ly=None, dash=None):
    d.append(dw.Line(x1, y1, x2, y2, stroke=color, stroke_width=2.2,
                     marker_end=dw.Marker(-0.3, -0.5, 0.9, 0.9, orient="auto-start-reverse",
                                          fill=color, stroke=color,
                                          shape=[(0, 0), (0.9, 0.5), (0, 0.9), (0.25, 0.5)]),
                     stroke_dasharray=dash or ""))
    if label:
        d.append(dw.Text(label, 10.5, lx, ly, center=True, fill=color,
                         font_family=F, font_style="italic"))


# ---- crane icon (object anchor) ------------------------------------------
def crane(cx, cy, s, color):
    d.append(dw.Line(cx, cy + 34 * s, cx, cy - 30 * s, stroke=color, stroke_width=2.4 * s))
    d.append(dw.Line(cx - 4 * s, cy + 34 * s, cx + 4 * s, cy + 34 * s, stroke=color, stroke_width=2.4 * s))
    d.append(dw.Line(cx, cy - 30 * s, cx + 26 * s, cy - 34 * s, stroke=color, stroke_width=2.4 * s))
    d.append(dw.Line(cx, cy - 24 * s, cx - 14 * s, cy - 32 * s, stroke=color, stroke_width=1.4 * s))
    d.append(dw.Circle(cx, cy - 30 * s, 2.6 * s, fill=color))
    d.append(dw.Circle(cx + 26 * s, cy - 34 * s, 2.6 * s, fill=color))
    d.append(dw.Line(cx + 18 * s, cy - 34 * s, cx + 18 * s, cy - 10 * s, stroke=color, stroke_width=1.1 * s))
    d.append(dw.Rectangle(cx + 15 * s, cy - 10 * s, 6 * s, 10 * s, fill="none", stroke=color, stroke_width=1.1 * s))
    d.append(dw.Text("limit b", 8.5 * s, cx + 24 * s, cy - 16 * s, fill=color, font_family=F))


# ---- top row: failure path (dominant) ------------------------------------
y0, h0 = 84, 150
xs = [36, 292, 548, 804]
ws = [216, 216, 216, 330]
box(xs[0], y0, ws[0], h0, PAL["soft"], "OPERATION OBJECT", PAL["object"], [])
crane(xs[0] + 168, y0 + 84, 0.62, PAL["object"])
d.append(dw.Text("Tower-crane", 11.5, xs[0] + 16, y0 + 52, fill=INK, font_family=F))
d.append(dw.Text("segment lift", 11.5, xs[0] + 16, y0 + 68, fill=INK, font_family=F))
d.append(dw.Text("in-service wind limit b", 11.5, xs[0] + 16, y0 + 84, fill=INK, font_family=F))
d.append(dw.Text("9.0–20.0 m/s, sourced", 11.5, xs[0] + 16, y0 + 100, fill=INK, font_family=F))
d.append(dw.Text("duration swept", 10.5, xs[0] + 16, y0 + 118, fill=PAL["line"], font_family=F, font_style="italic"))
box(xs[1], y0, ws[1], h0, PAL["soft"], "EXTERNAL DRIVER", PAL["driver"],
    ["Archived as-issued forecast", "NOAA GFS surface gust, 0.25°", "issued at t", "published at t + 4 h (audited)"])
box(xs[2], y0, ws[2], h0, PAL["soft"], "INTERNAL MECHANISM", PAL["misread"],
    ["instantaneous grid-point gust", "is compared, as an equal, with", "the event the contract cares about:", "\"any hour of the window > b\""])
box(xs[3], y0, ws[3], h0, PAL["soft"], "FAILURE STATE", PAL["fail"],
    ["raw threshold rule misreads the event:", "misses 30.8–53.6% of true exceedances", "false alarms on up to 15.4% of safe blocks", "(held-out 2025, 45 stations)"])

arrow(xs[0] + ws[0], y0 + 40, xs[1], y0 + 40, PAL["driver"], "feeds the decision",
      (xs[0] + ws[0] + xs[1]) / 2, y0 + h0 + 16)
arrow(xs[1] + ws[1], y0 + 40, xs[2], y0 + 40, PAL["misread"], "compared as equals",
      (xs[1] + ws[1] + xs[2]) / 2, y0 + h0 + 16)
arrow(xs[2] + ws[2], y0 + 40, xs[3], y0 + 40, PAL["fail"], "misreads the event",
      (xs[2] + ws[2] + xs[3]) / 2, y0 + h0 + 16)

# failure -> repair connector
d.append(dw.Text("the failure site is the detector, not the weather model",
                 11.5, xs[2] + ws[2] / 2, y0 + h0 + 52, center=True, fill=PAL["fail"],
                 font_family=F, font_style="italic"))

# ---- bottom row: repair path ---------------------------------------------
y1, h1 = 330, 150
bx = [36, 292, 548, 804]
bw = [216, 216, 216, 330]
box(bx[0], y1, bw[0], h1, PAL["soft"], "METHOD INTERVENTION", PAL["repair"],
    ["Decision-level calibration", "P(any hour of window > b | forecast)", "binned frequency + logistic", "fitted on 2021–2023 only"])
box(bx[1], y1, bw[1], h1, PAL["soft"], "EVIDENCE (HELD-OUT)", PAL["outcome"],
    ["reliability on the diagonal", "Brier skill vs climatology  +0.27…+0.42", "Brier skill vs raw threshold +0.26…+0.37", "survives 2025 split, 45 stations"])
box(bx[2], y1, bw[2], h1, PAL["soft"], "DECISION VALUE", PAL["imply"],
    ["tunable risk dial p* on the", "exposure–miss frontier", "peak relative economic value 0.44", "(9.0 m/s; decays as events get rarer)"])
box(bx[3], y1, bw[3], h1, PAL["soft"], "DESIGN IMPLICATION", PAL["imply"],
    ["calibrate the window event,", "not the weather model:", "one probability table per site & limit", "turns a fixed rule into a decision tool"])

arrow(bx[0] + bw[0], y1 + 42, bx[1], y1 + 42, PAL["repair"], "re-estimates the same event",
      (bx[0] + bw[0] + bx[1]) / 2, y1 + h1 + 16)
arrow(bx[1] + bw[1], y1 + 42, bx[2], y1 + 42, PAL["outcome"], "skill becomes value",
      (bx[1] + bw[1] + bx[2]) / 2, y1 + h1 + 16)
arrow(bx[2] + bw[2], y1 + 42, bx[3], y1 + 42, PAL["imply"], "usable rule",
      (bx[2] + bw[2] + bx[3]) / 2, y1 + h1 + 16)

# intervention targets the failure site (dashed, green, upward)
d.append(dw.Line(bx[0] + bw[0] / 2, y1 - 6, xs[2] + ws[2] / 2, y0 + h0 + 6,
                 stroke=PAL["repair"], stroke_width=2.0, stroke_dasharray="6 5",
                 marker_end=dw.Marker(-0.3, -0.5, 0.9, 0.9, orient="auto-start-reverse",
                                      fill=PAL["repair"], stroke=PAL["repair"],
                                      shape=[(0, 0), (0.9, 0.5), (0, 0.9), (0.25, 0.5)])))
d.append(dw.Text("repairs the misread event", 11, 400, y0 + h0 + 34, center=True,
                 fill=PAL["repair"], font_family=F, font_style="italic"))

# ---- footer: boundary ------------------------------------------------------
d.append(dw.Text("Boundary: crane-limit averaging interval and reference height are undocumented; limits swept across jurisdictions. "
                 "Station gusts are a proxy for crane-level exposure.",
                 9.5, W / 2, H - 12, center=True, fill=PAL["line"], font_family=F))

d.save_svg(OUT / "fig1_forecast_decision_mechanism.svg")
print("SVG written")

# PNG + PDF via cairosvg
cairosvg.svg2pdf(url=str(OUT / "fig1_forecast_decision_mechanism.svg"),
                 write_to=str(OUT / "fig1_forecast_decision_mechanism.pdf"))
cairosvg.svg2png(url=str(OUT / "fig1_forecast_decision_mechanism.svg"),
                 write_to=str(OUT / "fig1_forecast_decision_mechanism.png"), scale=2.0)
print("PDF/PNG written")






