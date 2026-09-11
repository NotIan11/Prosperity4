from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd

MPL_CACHE_DIR = Path("/tmp/prosperity4_matplotlib_cache")
MPL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MPL_CACHE_DIR))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


DATA_DIR = Path("data/round5")
OUT_DIR = Path("notebooks/r5_correlations")

CATEGORY_PREFIXES = [
    ("Galaxy sounds", "GALAXY_SOUNDS"),
    ("Microchips", "MICROCHIP"),
    ("Oxygen shakes", "OXYGEN_SHAKE"),
    ("Panels", "PANEL"),
    ("Pebbles", "PEBBLES"),
    ("Robots", "ROBOT"),
    ("Sleep pods", "SLEEP_POD"),
    ("Snackpacks", "SNACKPACK"),
    ("Translators", "TRANSLATOR"),
    ("UV visors", "UV_VISOR"),
]


def category_for_product(product: str) -> tuple[str, str]:
    for category, prefix in CATEGORY_PREFIXES:
        if product.startswith(prefix):
            return category, prefix
    return "Other", ""


def product_sort_key(product: str) -> tuple[int, str, str]:
    category, prefix = category_for_product(product)
    category_idx = next(
        (i for i, (name, _) in enumerate(CATEGORY_PREFIXES) if name == category),
        len(CATEGORY_PREFIXES),
    )
    variant = product.removeprefix(prefix).removeprefix("_")
    return category_idx, variant, product


def short_label(product: str) -> str:
    _, prefix = category_for_product(product)
    if not prefix:
        return product
    category_token = "".join(part[0] for part in prefix.split("_"))
    variant = product.removeprefix(prefix).removeprefix("_")
    return f"{category_token}_{variant}".replace("_", " ")


def load_mid_prices(data_dir: Path) -> pd.DataFrame:
    frames = []
    for path in sorted(data_dir.glob("prices_round_5_day_*.csv")):
        df = pd.read_csv(
            path,
            sep=";",
            usecols=["day", "timestamp", "product", "mid_price"],
        )
        df = df[df["product"] != "product"].copy()
        df["day"] = pd.to_numeric(df["day"], errors="raise").astype(int)
        df["timestamp"] = pd.to_numeric(df["timestamp"], errors="raise").astype(int)
        df["mid_price"] = pd.to_numeric(df["mid_price"], errors="raise")
        frames.append(df)

    if not frames:
        raise FileNotFoundError(f"No round 5 price files found in {data_dir}")

    prices = pd.concat(frames, ignore_index=True)
    ordered_products = sorted(prices["product"].unique(), key=product_sort_key)
    wide = prices.pivot_table(
        index=["day", "timestamp"],
        columns="product",
        values="mid_price",
        aggfunc="last",
    )
    return wide.sort_index().reindex(columns=ordered_products)


def pairwise_correlations(corr: pd.DataFrame) -> pd.DataFrame:
    rows = []
    products = list(corr.columns)
    for i, left in enumerate(products):
        for right in products[i + 1 :]:
            value = corr.loc[left, right]
            rows.append(
                {
                    "product_a": left,
                    "product_b": right,
                    "correlation": value,
                    "abs_correlation": abs(value),
                    "category_a": category_for_product(left)[0],
                    "category_b": category_for_product(right)[0],
                    "same_category": category_for_product(left)[0]
                    == category_for_product(right)[0],
                }
            )
    return pd.DataFrame(rows).sort_values(
        ["abs_correlation", "correlation"],
        ascending=[False, False],
        ignore_index=True,
    )


def write_heatmap(corr: pd.DataFrame, path: Path, title: str) -> None:
    labels = [short_label(product) for product in corr.columns]

    fig, ax = plt.subplots(figsize=(18, 16))
    image = ax.imshow(corr.to_numpy(), cmap="RdBu_r", vmin=-1, vmax=1)
    cbar = fig.colorbar(image, ax=ax, shrink=0.82)
    cbar.set_label("Pearson correlation")

    ax.set_title(title)
    ax.set_xticks(np.arange(len(labels)))
    ax.set_yticks(np.arange(len(labels)))
    ax.set_xticklabels(labels, rotation=90, fontsize=6)
    ax.set_yticklabels(labels, fontsize=6)

    boundaries = []
    last_category = None
    for idx, product in enumerate(corr.columns):
        category = category_for_product(product)[0]
        if last_category is not None and category != last_category:
            boundaries.append(idx - 0.5)
        last_category = category

    for boundary in boundaries:
        ax.axhline(boundary, color="black", linewidth=0.6, alpha=0.45)
        ax.axvline(boundary, color="black", linewidth=0.6, alpha=0.45)

    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    mid_prices = load_mid_prices(DATA_DIR)
    if mid_prices.shape[1] != 50:
        raise ValueError(f"Expected 50 products, found {mid_prices.shape[1]}")

    price_corr = mid_prices.corr()

    log_prices = np.log(mid_prices)
    log_returns = log_prices.groupby(level="day").diff().dropna(how="all")
    return_corr = log_returns.corr()

    mid_prices.to_csv(OUT_DIR / "r5_mid_prices_wide.csv")
    price_corr.to_csv(OUT_DIR / "r5_mid_price_correlation.csv")
    return_corr.to_csv(OUT_DIR / "r5_log_return_correlation.csv")

    pairs = pairwise_correlations(return_corr)
    price_pairs = pairwise_correlations(price_corr)
    price_pairs.to_csv(OUT_DIR / "r5_mid_price_correlation_pairs.csv", index=False)
    price_pairs.head(50).to_csv(
        OUT_DIR / "r5_top_50_abs_mid_price_correlations.csv",
        index=False,
    )
    price_pairs.sort_values("correlation", ascending=False).head(50).to_csv(
        OUT_DIR / "r5_top_50_positive_mid_price_correlations.csv",
        index=False,
    )
    price_pairs.sort_values("correlation", ascending=True).head(50).to_csv(
        OUT_DIR / "r5_top_50_negative_mid_price_correlations.csv",
        index=False,
    )

    pairs.to_csv(OUT_DIR / "r5_log_return_correlation_pairs.csv", index=False)
    pairs.head(50).to_csv(
        OUT_DIR / "r5_top_50_abs_log_return_correlations.csv",
        index=False,
    )
    pairs.sort_values("correlation", ascending=False).head(50).to_csv(
        OUT_DIR / "r5_top_50_positive_log_return_correlations.csv",
        index=False,
    )
    pairs.sort_values("correlation", ascending=True).head(50).to_csv(
        OUT_DIR / "r5_top_50_negative_log_return_correlations.csv",
        index=False,
    )

    write_heatmap(
        return_corr,
        OUT_DIR / "r5_log_return_correlation_heatmap.png",
        "Round 5 All Products - Log Return Correlation",
    )
    write_heatmap(
        price_corr,
        OUT_DIR / "r5_mid_price_correlation_heatmap.png",
        "Round 5 All Products - Mid Price Correlation",
    )

    print(f"Loaded {mid_prices.shape[1]} products x {mid_prices.shape[0]} timestamps")
    print(f"Wrote outputs to {OUT_DIR}")
    print("Top 10 absolute log-return correlations:")
    print(
        pairs.head(10)[
            ["product_a", "product_b", "correlation", "same_category"]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
