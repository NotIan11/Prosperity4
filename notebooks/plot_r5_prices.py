import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

data_dir = Path("data/round5")
out_dir = Path("notebooks/r5_plots")
out_dir.mkdir(exist_ok=True)

dfs = []
for f in sorted(data_dir.glob("prices_round_5_day_*.csv")):
    df = pd.read_csv(f, sep=";")
    day = int(f.stem.split("_")[-1])
    df["global_ts"] = day * 1_000_000 + df["timestamp"]
    dfs.append(df)

prices = pd.concat(dfs, ignore_index=True)
prices = prices[prices["product"] != "product"]

categories = {
    "galaxy_sound_recorders": "GALAXY_SOUNDS",
    "vertical_sleeping_pods": "SLEEP_POD",
    "organic_microchips": "MICROCHIP",
    "pebbles": "PEBBLES",
    "robots": "ROBOT",
    "uv_visors": "UV_VISOR",
    "translators": "TRANSLATOR",
    "panels": "PANEL",
    "oxygen_shakes": "OXYGEN_SHAKE",
    "protein_snack_packs": "SNACKPACK",
}

fig, ax = plt.subplots(figsize=(20, 8))

for name, prefix in categories.items():
    subset = prices[prices["product"].str.startswith(prefix)].copy()
    for variant in sorted(subset["product"].unique()):
        vdata = subset[subset["product"] == variant].sort_values("global_ts")
        label = variant.replace("_", " ").title()
        ax.plot(vdata["global_ts"], vdata["mid_price"], label=label, linewidth=0.7)

ax.set_title("All Products — Mid Price")
ax.set_xlabel("Timestep")
ax.set_ylabel("Mid Price")
ax.legend(fontsize=5, loc="best", ncol=3)
ax.grid(True, alpha=0.3)
fig.tight_layout()
fig.savefig(out_dir / "all_products.png", dpi=150)
plt.close(fig)
print("Saved all_products.png")
