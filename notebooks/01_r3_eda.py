"""R3 initial EDA — cross-correlation, microstructure, spread/vol analysis.

Run: ../venv/bin/python notebooks/01_r3_eda.py
Findings written to docs/round_3/research/01_initial_eda.md.
"""
import glob
import numpy as np
import pandas as pd

DATA_GLOB = "data/round_3/prices_round_3_day_*.csv"
PRODUCTS_GOODS = ["HYDROGEL_PACK", "VELVETFRUIT_EXTRACT"]


def load() -> pd.DataFrame:
    df = pd.concat([pd.read_csv(f, sep=";") for f in sorted(glob.glob(DATA_GLOB))],
                   ignore_index=True)
    df["t"] = df.day * 1_000_000 + df.timestamp
    return df


def wide_mids(df: pd.DataFrame) -> pd.DataFrame:
    return (df.pivot_table(index=["day", "timestamp", "t"],
                           columns="product", values="mid_price")
              .reset_index().sort_values("t").reset_index(drop=True))


def correlation_report(wide: pd.DataFrame) -> None:
    products = [c for c in wide.columns if c not in ("day", "timestamp", "t")]
    print("=== mid-price correlation (levels) ===")
    print(wide[products].corr().round(2), "\n")
    rets = np.log(wide[products]).diff()
    live = [p for p in products if rets[p].std() > 0]
    print("=== return correlation (1-tick log returns) ===")
    print(rets[live].corr().round(2))


def microstructure(df: pd.DataFrame, wide: pd.DataFrame) -> None:
    for prod in PRODUCTS_GOODS:
        print(f"\n========== {prod} ==========")
        s = wide[prod]
        r = s.diff()
        print(f"  level: mean={s.mean():.2f} std={s.std():.2f} "
              f"min={s.min()} max={s.max()}")
        for d in sorted(wide.day.unique()):
            sd = wide.loc[wide.day == d, prod]
            print(f"    day {d}: std={sd.std():.2f} range=[{sd.min()}, {sd.max()}]")
        print("  return autocorr (1-tick diff):")
        for lag in [1, 2, 5, 10, 50, 100]:
            print(f"    lag {lag:>3}: {r.autocorr(lag):+.4f}")
        spr = (df.loc[df["product"] == prod, "ask_price_1"]
               - df.loc[df["product"] == prod, "bid_price_1"])
        print(f"  spread: mean={spr.mean():.2f} median={spr.median():.0f} "
              f"min={spr.min():.0f} max={spr.max():.0f}")


if __name__ == "__main__":
    df = load()
    wide = wide_mids(df)
    print(f"loaded {len(df):,} price rows over {wide.day.nunique()} days, "
          f"{df['product'].nunique()} products\n")
    correlation_report(wide)
    microstructure(df, wide)
