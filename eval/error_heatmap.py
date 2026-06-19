import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from matplotlib.colors import LinearSegmentedColormap

reddish_cmap = LinearSegmentedColormap.from_list(
    "paper_reddish",
    ["#05051a", "#3b1f46", "#a61c5b", "#ef4444", "#f6c9ad", "#fff1e6"]
)

# Optional but useful for a LaTeX-paper look.
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 16,
    "axes.titlesize": 22,
    "axes.labelsize": 20,
    "xtick.labelsize": 15,
    "ytick.labelsize": 15,
})


# Example data: replace with your actual results
systems = [
    "DuckDB",
    "Pandas",
    "Python csv",
    "CleverCSV",
    "CSVsniffer",
    "Agentic Loader"
]

pollutions = [
    "Preamble",
    "Superheader",
    "Schema Drift",
    "Embedded JSON",
    "Footer",
    "Merged Cells",
    "Multi-table",
    "Comments"
]

scores = np.array([
    [72, 48, 35, 68, 61, 30, 28, 70],
    [65, 42, 31, 63, 55, 25, 22, 66],
    [58, 35, 22, 55, 47, 18, 15, 60],
    [75, 52, 38, 64, 60, 33, 30, 72],
    [78, 55, 41, 66, 63, 36, 32, 75],
    [92, 86, 78, 88, 84, 73, 69, 90],
])

df = pd.DataFrame(scores, index=systems, columns=pollutions)

fig, ax = plt.subplots(figsize=(12, 6.2))

im = ax.imshow(
    df.values,
    cmap=reddish_cmap,
    aspect="auto",
    vmin=0,
    vmax=100
)

# Axes
ax.set_xticks(np.arange(len(pollutions)))
ax.set_yticks(np.arange(len(systems)))
ax.set_xticklabels(pollutions, rotation=35, ha="right")
ax.set_yticklabels(systems)

ax.set_xlabel("Pollution Category")
ax.set_ylabel("System")
ax.set_title("Performance per Pollution Category")

# Cell annotations
for i in range(df.shape[0]):
    for j in range(df.shape[1]):
        value = df.iloc[i, j]

        # White text on dark cells, black on light cells
        color = "white" if value > 60 else "black"

        ax.text(
            j, i,
            f"{value:.0f}",
            ha="center",
            va="center",
            color=color,
            fontsize=9
        )

# Colorbar
cbar = fig.colorbar(im, ax=ax)
cbar.set_label("Full Correctness (%)")

plt.tight_layout()
plt.savefig("eval/error_heatmap.png", dpi=300)