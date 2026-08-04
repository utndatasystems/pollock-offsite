#!/usr/bin/env python3
"""Teaser figure: one polluted CSV -> two readings (human vs. rule-based parser)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, FancyArrowPatch

# ---- embed real fonts in the PDF (camera-ready friendly) ----
plt.rcParams.update({
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "svg.fonttype": "none",
    "font.family": "DejaVu Sans",
})

MONO = "DejaVu Sans Mono"

# ---- palette ----
INK      = "#1a1a1a"
MUTED    = "#9aa0a6"   # delimiters / annotations
HEADERBG = "#eef1f5"
HEADERTX = "#1f3b57"
GRID     = "#c9ced6"
RED      = "#d1342f"   # malformed region / wrong cells
REDBG    = "#fbe3e1"
GHOST    = "#f4f5f7"   # inferred NULL cell
GREEN    = "#1f8a4c"
GROUPBG  = "#fafbfc"
GROUPED  = "#dfe3e8"

FIG_W, FIG_H = 3.35, 2.0
fig = plt.figure(figsize=(FIG_W, FIG_H), dpi=400)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis("off")


def fx(inches):
    """Convert inches to x-axis figure fraction."""
    return inches / FIG_W


# --------------------------------------------------------------------------
# LEFT: raw polluted CSV with the missing delimiter highlighted
# --------------------------------------------------------------------------
RAW_FS = 6.6
CW = fx(RAW_FS * 0.602 / 72.0)  # approximate monospace character advance
x0 = 0.05
lines_y = [0.635, 0.505, 0.375]

card = FancyBboxPatch(
    (0.028, 0.30), 0.45, 0.44,
    boxstyle="round,pad=0.006,rounding_size=0.02",
    linewidth=0.7, edgecolor=GROUPED, facecolor=GROUPBG, zorder=0,
)
ax.add_patch(card)
ax.text(
    0.036, 0.785, "raw csv", family=MONO, fontsize=6.2,
    color=MUTED, weight="bold", va="center",
)


def draw_line(y, tokens):
    """Draw fixed-width tokens: (text, color, bold)."""
    x = x0
    for text, color, bold in tokens:
        ax.text(
            x, y, text, family=MONO, fontsize=RAW_FS, color=color,
            va="center", ha="left", weight=("bold" if bold else "normal"),
        )
        x += CW * len(text)
    return x


D = (",", MUTED, False)
draw_line(lines_y[0], [
    ("id", INK, False), D, ("name", INK, False), D, ("city", INK, False),
])
draw_line(lines_y[1], [
    ("1", INK, False), D, ("Ann Adams", INK, False), D, ("New York", INK, False),
])

# Malformed row: the delimiter between "Bob Baker" and "Berlin" is missing.
row3_prefix = "2,"
name_part = "Bob Baker"
city_part = "Berlin"
start_bad = x0 + CW * len(row3_prefix)
end_bad = start_bad + CW * len(name_part + city_part)
split_x = start_bad + CW * len(name_part)

ax.add_patch(Rectangle(
    (start_bad - 0.004, lines_y[2] - 0.05),
    (end_bad - start_bad) + 0.008, 0.10,
    facecolor=REDBG, edgecolor="none", zorder=0.5,
))
draw_line(lines_y[2], [
    ("2", INK, False), D,
    (name_part, INK, False),
    (city_part, INK, False),
])

# Mark the inferred split point without inserting a character into the raw CSV.
ax.plot(
    [split_x, split_x],
    [lines_y[2] - 0.052, lines_y[2] + 0.052],
    color=RED, lw=0.9, linestyle=(0, (1.2, 1.0)), zorder=3,
)
ax.text(
    split_x, lines_y[2] - 0.102, "missing ,",
    family=MONO, fontsize=4.8, color=RED,
    ha="center", va="center",
)


# --------------------------------------------------------------------------
# Generic table renderer
# --------------------------------------------------------------------------
def table(
    x_left, y_top, col_w, rows,
    cell_fs=5.7, header_fs=5.4, row_h=0.098,
    header_style=None, cell_style=None,
):
    n_cols = len(col_w)
    xs = [x_left]
    for width in col_w:
        xs.append(xs[-1] + width)

    for r, row in enumerate(rows):
        y = y_top - r * row_h
        for c in range(n_cols):
            val = row[c] if c < len(row) else ""
            fc = HEADERBG if r == 0 else "white"
            tc = HEADERTX if r == 0 else INK
            weight = "bold" if r == 0 else "normal"

            st = {}
            if r == 0 and header_style:
                st = header_style(c) or {}
            elif r > 0 and cell_style:
                st = cell_style(r, c) or {}

            fc = st.get("fc", fc)
            tc = st.get("tc", tc)
            weight = st.get("weight", weight)
            linestyle = st.get("linestyle", "-")

            ax.add_patch(Rectangle(
                (xs[c], y - row_h), col_w[c], row_h,
                facecolor=fc, edgecolor=GRID, linewidth=0.6,
                linestyle=linestyle, zorder=1,
            ))
            if val != "":
                ax.text(
                    xs[c] + col_w[c] / 2, y - row_h / 2, val,
                    family=MONO,
                    fontsize=(header_fs if r == 0 else cell_fs),
                    color=tc, weight=weight,
                    ha="center", va="center", zorder=2,
                )


# --------------------------------------------------------------------------
# RIGHT-TOP: human reconstruction
# --------------------------------------------------------------------------
RX = 0.565
col_w = [0.056, 0.205, 0.125]
human_rows = [
    ["id", "name", "city"],
    ["1", "Ann Adams", "New York"],
    ["2", "Bob Baker", "Berlin"],
]

ax.text(
    RX - 0.026, 0.925, "\u2713", fontsize=8.0,
    color=GREEN, weight="bold", va="center", ha="center",
)
ax.text(
    RX, 0.925, "human reconstruction", family=MONO, fontsize=6.0,
    color=GREEN, weight="bold", va="center",
)
table(RX, 0.865, col_w, human_rows)


# --------------------------------------------------------------------------
# RIGHT-BOTTOM: rule-based parser leaves the missing field as NULL
# --------------------------------------------------------------------------
parser_rows = [
    ["id", "name", "city"],
    ["1", "Ann Adams", "New York"],
    ["2", "Bob BakerBerlin", "NULL"],
]


def parser_cell_style(r, c):
    if r == 2 and c == 1:
        return {"fc": REDBG, "tc": RED, "weight": "bold"}
    if r == 2 and c == 2:
        return {
            "fc": GHOST,
            "tc": RED,
            "weight": "bold",
            "linestyle": ":",
        }
    return {}


ax.text(
    RX - 0.026, 0.485, "\u2717", fontsize=7.5,
    color=RED, weight="bold", va="center", ha="center",
)
ax.text(
    RX, 0.485, "rule-based parser", family=MONO, fontsize=6.0,
    color=RED, weight="bold", va="center",
)
table(RX, 0.425, col_w, parser_rows, cell_fs=5.35, cell_style=parser_cell_style)


# --------------------------------------------------------------------------
# Arrows: one file -> two readings
# --------------------------------------------------------------------------
def arrow(y_to, rad):
    ax.add_patch(FancyArrowPatch(
        (0.488, 0.505), (RX - 0.04, y_to),
        connectionstyle="arc3,rad=%.2f" % rad,
        arrowstyle="-|>", mutation_scale=7,
        lw=0.8, color=MUTED, zorder=0.5,
    ))


arrow(0.74, 0.28)
arrow(0.28, -0.28)


from pathlib import Path

output_dir = Path(__file__).resolve().parent

from matplotlib.transforms import Bbox
crop = Bbox.from_bounds(
    0, 0.16,          # left, bottom crop
    FIG_W, FIG_H - 0.16
)


fig.savefig(
    output_dir / "csv_teaser_missing_delimiter.pdf",
    bbox_inches="tight",
    pad_inches=0,
)
fig.savefig(
    output_dir / "csv_teaser_missing_delimiter.png",
    dpi=400,
    bbox_inches="tight",
    pad_inches=0,
)


print("wrote csv_teaser_missing_delimiter.pdf and csv_teaser_missing_delimiter.png")