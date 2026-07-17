#!/usr/bin/env python3
"""Teaser figure: one polluted CSV -> two readings (human vs. parser)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, FancyArrowPatch

# ---- embed real fonts in the PDF (camera-ready friendly) ----
plt.rcParams.update({
    "pdf.fonttype": 42, "ps.fonttype": 42,
    "svg.fonttype": "none",
    "font.family": "DejaVu Sans",
})

MONO = "DejaVu Sans Mono"

# ---- palette ----
INK      = "#1a1a1a"
MUTED    = "#9aa0a6"   # delimiters
HEADERBG = "#eef1f5"
HEADERTX = "#1f3b57"
GRID     = "#c9ced6"
RED      = "#d1342f"   # offending quotes / wrong cells
REDBG    = "#fbe3e1"
GHOST    = "#f4f5f7"   # overflow (data outside the schema)
GREEN    = "#1f8a4c"
GROUPBG  = "#fafbfc"
GROUPED  = "#dfe3e8"

FIG_W, FIG_H = 3.35, 2.0
fig = plt.figure(figsize=(FIG_W, FIG_H), dpi=400)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")

def fx(inches):  # inches -> x fraction
    return inches / FIG_W

# --------------------------------------------------------------------------
# LEFT: raw polluted CSV with syntax highlighting
# --------------------------------------------------------------------------
RAW_FS = 6.6
CW = fx(RAW_FS * 0.602 / 72.0)          # monospace char advance (x-fraction)
x0 = 0.05
lines_y = [0.635, 0.505, 0.375]

# grouping card behind the raw block
card = FancyBboxPatch((0.028, 0.30), 0.45, 0.44,
                      boxstyle="round,pad=0.006,rounding_size=0.02",
                      linewidth=0.7, edgecolor=GROUPED, facecolor=GROUPBG, zorder=0)
ax.add_patch(card)
ax.text(0.036, 0.785, "raw csv", family=MONO, fontsize=6.2, color=MUTED,
        weight="bold", va="center")

def draw_line(y, tokens):
    """tokens: list of (text, color, bold). Fixed monospace advance."""
    x = x0
    for text, color, bold in tokens:
        ax.text(x, y, text, family=MONO, fontsize=RAW_FS, color=color,
                va="center", ha="left", weight=("bold" if bold else "normal"))
        x += CW * len(text)
    return x

D = (",", MUTED, False)   # delimiter comma
draw_line(lines_y[0], [("id", INK, False), D, ("quote", INK, False), D,
                       ("speaker", INK, False)])
# polluted row -- highlight the intended atomic value + the offending quotes
start_val = x0 + CW * len("1,")
end_val   = start_val + CW * len('said "wait, stop"')
ax.add_patch(Rectangle((start_val - 0.004, lines_y[1] - 0.05),
                        (end_val - start_val) + 0.008, 0.10,
                        facecolor=REDBG, edgecolor="none", zorder=0.5))
draw_line(lines_y[1], [
    ("1", INK, False), D,
    ("said ", INK, False),
    ('"', RED, True), ("wait", INK, False),
    (",", RED, True),                       # the comma the parser will misread
    (" stop", INK, False), ('"', RED, True),
    D, ("Ann", INK, False),
])
draw_line(lines_y[2], [("2", INK, False), D, ("she agreed", INK, False), D,
                       ("Bob", INK, False)])
# subtle brace under the intended single value
ax.plot([start_val, end_val], [lines_y[1] - 0.062, lines_y[1] - 0.062],
        color=RED, lw=0.7, zorder=2)
ax.text((start_val + end_val) / 2, lines_y[1] - 0.10, "one value",
        family=MONO, fontsize=4.8, color=RED, ha="center", va="center")

# --------------------------------------------------------------------------
# generic table renderer
# --------------------------------------------------------------------------
def table(x_left, y_top, col_w, rows, cell_fs=5.7, header_fs=5.4, row_h=0.098,
          header_style=None, cell_style=None, ghost_last=False):
    n_cols = len(col_w)
    xs = [x_left]
    for w in col_w:
        xs.append(xs[-1] + w)
    for r, row in enumerate(rows):
        y = y_top - r * row_h
        for c in range(n_cols):
            val = row[c] if c < len(row) else ""
            is_ghost = ghost_last and c == n_cols - 1
            fc = HEADERBG if r == 0 else "white"
            tc = HEADERTX if r == 0 else INK
            weight = "bold" if r == 0 else "normal"
            if is_ghost:
                fc = GHOST
            st = {}
            if r == 0 and header_style:
                st = header_style(c) or {}
            elif r > 0 and cell_style:
                st = cell_style(r, c) or {}
            fc = st.get("fc", fc); tc = st.get("tc", tc)
            weight = st.get("weight", weight)
            ax.add_patch(Rectangle((xs[c], y - row_h), col_w[c], row_h,
                         facecolor=fc, edgecolor=GRID, linewidth=0.6, zorder=1,
                         linestyle=(":" if is_ghost and r == 0 else "-")))
            if val != "":
                ax.text(xs[c] + col_w[c] / 2, y - row_h / 2, val, family=MONO,
                        fontsize=(header_fs if r == 0 else cell_fs), color=tc,
                        weight=weight, ha="center", va="center", zorder=2)

# --------------------------------------------------------------------------
# RIGHT-TOP: human reconstruction  (correct 3x3 table)
# --------------------------------------------------------------------------
RX = 0.545
human_rows = [
    ["id", "quote", "speaker"],
    ["1", 'said "wait, stop"', "Ann"],
    ["2", "she agreed", "Bob"],
]
ax.text(RX - 0.026, 0.925, "\u2713", fontsize=8.0, color=GREEN,
        weight="bold", va="center", ha="center")
ax.text(RX, 0.925, "human reconstruction", family=MONO, fontsize=6.0,
        color=GREEN, weight="bold", va="center")
table(RX, 0.865, [0.056, 0.256, 0.104], human_rows)

# --------------------------------------------------------------------------
# RIGHT-BOTTOM: standard parser (row shifts into a phantom column)
# --------------------------------------------------------------------------
parser_rows = [
    ["id", "quote", "speaker", ""],
    ["1", 'said "wait', ' stop"', "Ann"],
    ["2", "she agreed", "Bob", ""],
]
def p_cell_style(r, c):
    if r == 1 and c in (1, 2, 3):          # silently shifted / phantom cells
        return {"fc": REDBG, "tc": RED, "weight": "bold"}
    if r == 2 and c == 3:
        return {"fc": GHOST}
    return {}
def p_header_style(c):
    if c == 3:
        return {"fc": GHOST, "tc": MUTED}
    return {}

ax.text(RX - 0.026, 0.485, "\u2717", fontsize=7.5, color=RED,
        weight="bold", va="center", ha="center")
ax.text(RX, 0.485, "standard parser", family=MONO, fontsize=6.0,
        color=RED, weight="bold", va="center")
pw = [0.056, 0.156, 0.104, 0.066]
table(RX, 0.425, pw, parser_rows, cell_style=p_cell_style,
      header_style=p_header_style, ghost_last=True)
ax.text(RX + sum(pw) - pw[-1] / 2, 0.445, "+1 col", family=MONO,
        fontsize=4.6, color=RED, ha="center", va="center")

# --------------------------------------------------------------------------
# arrows: one file -> two readings
# --------------------------------------------------------------------------
def arrow(y_to, rad):
    ax.add_patch(FancyArrowPatch((0.488, 0.505), (RX - 0.04, y_to),
                 connectionstyle="arc3,rad=%.2f" % rad, arrowstyle="-|>",
                 mutation_scale=7, lw=0.8, color=MUTED, zorder=0.5))
arrow(0.74, 0.28)    # to human
arrow(0.28, -0.28)   # to parser

fig.savefig("csv_teaser.pdf")
fig.savefig("csv_teaser.png", dpi=400)
print("wrote csv_teaser.pdf and csv_teaser.png")
