"""R3 microstructure EDA — HYDROGEL_PACK + VELVETFRUIT_EXTRACT.

Answers Q1-Q8 from the analysis brief: depth profile, wall_mid stability,
spread regimes, autocorr robustness, mean reversion, fill simulation,
inventory drift, adverse selection.

Run: venv/bin/python notebooks/02_microstructure_eda.py
"""
from __future__ import annotations

import glob
import os
import warnings

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

PRICE_GLOB = "data/round_3/prices_round_3_day_*.csv"
TRADE_GLOB = "data/round_3/trades_round_3_day_*.csv"
PRODUCTS = ["HYDROGEL_PACK", "VELVETFRUIT_EXTRACT"]
PLOTS_DIR = "docs/round_3/research/plots"
os.makedirs(PLOTS_DIR, exist_ok=True)


# ----- load -----
def load_prices() -> pd.DataFrame:
    df = pd.concat([pd.read_csv(f, sep=";") for f in sorted(glob.glob(PRICE_GLOB))],
                   ignore_index=True)
    df = df[df["product"].isin(PRODUCTS)].copy()
    df["t"] = df["day"] * 1_000_000 + df["timestamp"]
    df = df.sort_values(["product", "t"]).reset_index(drop=True)
    # bid_volumes are abs sizes; ask_volumes too in this dataset
    for c in df.columns:
        if c.startswith(("bid_volume", "ask_volume")):
            df[c] = df[c].fillna(0)
    return df


def load_trades() -> pd.DataFrame:
    parts = []
    for f in sorted(glob.glob(TRADE_GLOB)):
        d = pd.read_csv(f, sep=";")
        day = int(f.rsplit("_", 1)[-1].split(".")[0])
        d["day"] = day
        parts.append(d)
    df = pd.concat(parts, ignore_index=True)
    df = df[df["symbol"].isin(PRODUCTS)].copy()
    df["t"] = df["day"] * 1_000_000 + df["timestamp"]
    return df


# ----- per-product helpers -----
def per_prod(df: pd.DataFrame, prod: str) -> pd.DataFrame:
    return df[df["product"] == prod].copy().reset_index(drop=True)


def add_book_features(p: pd.DataFrame) -> pd.DataFrame:
    p["best_bid"] = p["bid_price_1"]
    p["best_ask"] = p["ask_price_1"]
    p["top_mid"] = (p["best_bid"] + p["best_ask"]) / 2
    p["spread"] = p["best_ask"] - p["best_bid"]
    # wall_mid: deepest level (largest size) on each side; fall back to top
    bid_px = p[["bid_price_1", "bid_price_2", "bid_price_3"]].to_numpy()
    bid_sz = p[["bid_volume_1", "bid_volume_2", "bid_volume_3"]].to_numpy()
    ask_px = p[["ask_price_1", "ask_price_2", "ask_price_3"]].to_numpy()
    ask_sz = p[["ask_volume_1", "ask_volume_2", "ask_volume_3"]].to_numpy()
    # for missing levels px is NaN; mask their sizes to -inf so argmax picks real ones
    bid_sz_m = np.where(np.isnan(bid_px), -np.inf, bid_sz)
    ask_sz_m = np.where(np.isnan(ask_px), -np.inf, ask_sz)
    bid_idx = np.argmax(bid_sz_m, axis=1)
    ask_idx = np.argmax(ask_sz_m, axis=1)
    rows = np.arange(len(p))
    deep_bid = bid_px[rows, bid_idx]
    deep_ask = ask_px[rows, ask_idx]
    p["wall_bid"] = deep_bid
    p["wall_ask"] = deep_ask
    p["wall_mid"] = (deep_bid + deep_ask) / 2
    # depth count: how many levels populated per side
    p["bid_levels"] = (~np.isnan(bid_px)).sum(axis=1)
    p["ask_levels"] = (~np.isnan(ask_px)).sum(axis=1)
    p["total_bid_size"] = np.nansum(bid_sz, axis=1)
    p["total_ask_size"] = np.nansum(ask_sz, axis=1)
    return p


# ----- analysis blocks -----
def q1_depth(books: dict) -> None:
    print("\n### Q1 — Order book depth profile")
    for prod, p in books.items():
        print(f"\n[{prod}]")
        for side in ("bid", "ask"):
            lc = p[f"{side}_levels"].value_counts(normalize=True).sort_index()
            print(f"  {side} levels distribution: " +
                  ", ".join(f"L{int(k)}={v:.1%}" for k, v in lc.items()))
        for L in (1, 2, 3):
            bm = p[f"bid_volume_{L}"].replace(0, np.nan).median()
            am = p[f"ask_volume_{L}"].replace(0, np.nan).median()
            print(f"  median size  L{L}: bid={bm}, ask={am}")
        deep_frac = ((p["bid_levels"] == 3) & (p["ask_levels"] == 3)).mean()
        print(f"  fraction ticks with both sides 3-deep: {deep_frac:.1%}")
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for ax, (prod, p) in zip(axes, books.items()):
        for L in (1, 2, 3):
            ax.hist(p[f"bid_volume_{L}"].replace(0, np.nan).dropna(), bins=40,
                    alpha=0.5, label=f"bid L{L}")
        ax.set_title(f"{prod}: bid size by level")
        ax.set_xlabel("size")
        ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(f"{PLOTS_DIR}/02_q1_depth.png", dpi=110)
    plt.close(fig)


def q2_wall_mid(books: dict) -> None:
    print("\n### Q2 — Wall mid vs top-of-book mid")
    for prod, p in books.items():
        diff = p["wall_mid"] - p["top_mid"]
        d_top = p["top_mid"].diff()
        d_wall = p["wall_mid"].diff()
        print(f"\n[{prod}]")
        print(f"  wall_mid - top_mid: mean={diff.mean():.3f}, std={diff.std():.3f}, "
              f"|>0|={ (diff.abs() > 0).mean():.1%}")
        print(f"  std of d(top_mid) ={d_top.std():.3f}")
        print(f"  std of d(wall_mid)={d_wall.std():.3f}")
        print(f"  ratio std(d_wall)/std(d_top)={d_wall.std()/d_top.std():.3f}")
        print(f"  P(|d_wall|=0)={ (d_wall == 0).mean():.1%}, "
              f"P(|d_top|=0)={ (d_top == 0).mean():.1%}")
    # plot a 1500-tick slice
    fig, axes = plt.subplots(2, 1, figsize=(11, 6))
    for ax, (prod, p) in zip(axes, books.items()):
        s = p.iloc[5000:6500]
        ax.plot(s["t"].values, s["top_mid"].values, alpha=0.6, lw=0.8, label="top_mid")
        ax.plot(s["t"].values, s["wall_mid"].values, alpha=0.9, lw=0.8, label="wall_mid")
        ax.set_title(prod)
        ax.legend()
    fig.tight_layout()
    fig.savefig(f"{PLOTS_DIR}/02_q2_wallmid_vs_topmid.png", dpi=110)
    plt.close(fig)


def q3_spread(books: dict) -> None:
    print("\n### Q3 — Spread regimes")
    fig, axes = plt.subplots(2, 2, figsize=(12, 7))
    for col, (prod, p) in enumerate(books.items()):
        sp = p["spread"]
        med = sp.median()
        print(f"\n[{prod}] spread median={med}, mean={sp.mean():.2f}, "
              f"std={sp.std():.2f}, min={sp.min()}, max={sp.max()}")
        vc = sp.value_counts(normalize=True).sort_index()
        print("  top spread values:", ", ".join(f"{int(k)}:{v:.1%}" for k, v in vc.head(8).items()))
        # by day
        per_day = p.groupby("day")["spread"].agg(["median", "mean", "std"])
        print(per_day)
        # heatmap day x intraday-quartile
        p["bucket"] = pd.cut(p["timestamp"], bins=10, labels=range(10))
        heat = p.groupby(["day", "bucket"], observed=True)["spread"].mean().unstack()
        axes[0, col].imshow(heat.values, aspect="auto", cmap="viridis")
        axes[0, col].set_title(f"{prod}: mean spread, day×bucket")
        axes[0, col].set_xlabel("intraday bucket"); axes[0, col].set_ylabel("day")
        axes[1, col].hist(sp, bins=range(int(sp.min()), int(sp.max()) + 2), alpha=0.8)
        axes[1, col].set_title(f"{prod}: spread hist")
    fig.tight_layout()
    fig.savefig(f"{PLOTS_DIR}/02_q3_spread.png", dpi=110)
    plt.close(fig)


def autocorr(x: np.ndarray, lag: int) -> float:
    x = x[~np.isnan(x)]
    if len(x) < lag + 5:
        return np.nan
    return float(np.corrcoef(x[:-lag], x[lag:])[0, 1])


def q4_autocorr(books: dict) -> None:
    print("\n### Q4 — Autocorrelation robustness")
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    for ax, (prod, p) in zip(axes, books.items()):
        print(f"\n[{prod}]")
        rets = p["wall_mid"].diff().to_numpy()
        # per-day lag-1
        for d in sorted(p["day"].unique()):
            sub = p[p["day"] == d]["wall_mid"].diff().to_numpy()
            print(f"  day {d}: lag1={autocorr(sub, 1):.3f}, lag2={autocorr(sub, 2):.3f}, "
                  f"lag5={autocorr(sub, 5):.3f}")
        # per-quarter intraday
        p["q"] = pd.cut(p["timestamp"], bins=4, labels=[0, 1, 2, 3])
        for q in [0, 1, 2, 3]:
            sub = p[p["q"] == q]["wall_mid"].diff().to_numpy()
            print(f"  intraday Q{q}: lag1={autocorr(sub, 1):.3f}")
        # full lag spectrum
        lags = list(range(1, 201))
        ac = [autocorr(rets, L) for L in lags]
        ax.axhline(0, color="k", lw=0.5)
        ax.plot(lags, ac)
        ax.set_title(f"{prod}: wall_mid return autocorr")
        ax.set_xlabel("lag (ticks)"); ax.set_ylabel("rho")
    fig.tight_layout()
    fig.savefig(f"{PLOTS_DIR}/02_q4_autocorr.png", dpi=110)
    plt.close(fig)


def variance_ratio(x: np.ndarray, k: int) -> float:
    x = x[~np.isnan(x)]
    if len(x) < k * 5:
        return np.nan
    var1 = np.var(x, ddof=1)
    rk = pd.Series(x).rolling(k).sum().dropna().to_numpy()
    vark = np.var(rk, ddof=1)
    return float(vark / (k * var1))


def hurst_rs(x: np.ndarray) -> float:
    x = x[~np.isnan(x)]
    if len(x) < 200:
        return np.nan
    ns = [16, 32, 64, 128, 256, 512]
    rs_vals = []
    for n in ns:
        if n * 4 > len(x):
            break
        chunks = len(x) // n
        rs_chunk = []
        for i in range(chunks):
            seg = x[i * n:(i + 1) * n]
            mean = seg.mean()
            cum = np.cumsum(seg - mean)
            R = cum.max() - cum.min()
            S = seg.std(ddof=1)
            if S > 0:
                rs_chunk.append(R / S)
        if rs_chunk:
            rs_vals.append((np.log(n), np.log(np.mean(rs_chunk))))
    if len(rs_vals) < 3:
        return np.nan
    xs, ys = zip(*rs_vals)
    slope = np.polyfit(xs, ys, 1)[0]
    return float(slope)


def q5_meanreversion(books: dict) -> None:
    print("\n### Q5 — Mean reversion structure")
    for prod, p in books.items():
        print(f"\n[{prod}]")
        rets = p["wall_mid"].diff().to_numpy()
        for k in (2, 5, 10, 50):
            print(f"  variance ratio k={k}: {variance_ratio(rets, k):.3f} "
                  "(<1 = mean-reverting)")
        # Hurst on price levels
        h_p = hurst_rs(p["wall_mid"].dropna().to_numpy())
        # Hurst on returns (sanity)
        h_r = hurst_rs(rets[~np.isnan(rets)])
        print(f"  Hurst (price R/S): {h_p:.3f}  (Hurst returns: {h_r:.3f})")
        # AR(1) half-life on demeaned price
        s = p["wall_mid"].dropna().to_numpy()
        s_dm = s - s.mean()
        rho = np.corrcoef(s_dm[:-1], s_dm[1:])[0, 1]
        if 0 < rho < 1:
            hl = -np.log(2) / np.log(rho)
            print(f"  AR(1) on price rho={rho:.4f}, half-life={hl:.1f} ticks")
        else:
            print(f"  AR(1) on price rho={rho:.4f} (no usable half-life)")


def simulate_mm(p: pd.DataFrame, h: int, max_pos: int = 200) -> dict:
    """Naive passive MM simulator.
    Each tick: post bid at floor(wall_mid - h), ask at ceil(wall_mid + h).
    Fill rules (per-tick, conservative):
      - If our bid >= best_ask of NEXT tick (book moved through us) -> we get filled buy at our bid.
      - If our ask <= best_bid of NEXT tick -> we get filled sell at our ask.
      - Size: assume 1 unit per fill (lower bound), capped by position limit.
    """
    wall = p["wall_mid"].to_numpy()
    ba = p["best_ask"].to_numpy()
    bb = p["best_bid"].to_numpy()
    n = len(p)
    pos = 0
    cash = 0.0
    fills_buy = 0
    fills_sell = 0
    pos_track = []
    for i in range(n - 1):
        if np.isnan(wall[i]):
            pos_track.append(pos)
            continue
        my_bid = np.floor(wall[i] - h)
        my_ask = np.ceil(wall[i] + h)
        # next-tick fill check
        nb_a = ba[i + 1]
        nb_b = bb[i + 1]
        if not np.isnan(nb_a) and my_bid >= nb_a and pos < max_pos:
            cash -= my_bid
            pos += 1
            fills_buy += 1
        if not np.isnan(nb_b) and my_ask <= nb_b and pos > -max_pos:
            cash += my_ask
            pos -= 1
            fills_sell += 1
        pos_track.append(pos)
    # mark to wall_mid at end
    final_mid = wall[~np.isnan(wall)][-1]
    pnl = cash + pos * final_mid
    return {
        "h": h, "fills_buy": fills_buy, "fills_sell": fills_sell,
        "fill_rate_per_tick": (fills_buy + fills_sell) / n,
        "avg_abs_pos": float(np.mean(np.abs(pos_track))),
        "max_abs_pos": int(np.max(np.abs(pos_track))),
        "pnl_proxy": float(pnl),
    }


def q6_fillsim(books: dict) -> None:
    print("\n### Q6 — Mock fill simulation (passive at wall_mid ± h)")
    rows = []
    for prod, p in books.items():
        for h in (2, 5, 8, 10, 15):
            r = simulate_mm(p, h)
            r["product"] = prod
            rows.append(r)
            print(f"  {prod} h={h:2d}: fill/tick={r['fill_rate_per_tick']:.3%}, "
                  f"buys={r['fills_buy']}, sells={r['fills_sell']}, "
                  f"avg|pos|={r['avg_abs_pos']:.1f}, max|pos|={r['max_abs_pos']}, "
                  f"pnl_proxy={r['pnl_proxy']:.0f}")
    df = pd.DataFrame(rows)
    df.to_csv(f"{PLOTS_DIR}/02_q6_fillsim.csv", index=False)


def q7_q8_inventory_adverse(books: dict) -> None:
    print("\n### Q7/Q8 — Inventory drift & adverse selection")
    # We re-simulate at h=median_spread/2 and inspect mid drift after fills.
    for prod, p in books.items():
        h = int(round(p["spread"].median() / 2))
        wall = p["wall_mid"].to_numpy()
        ba = p["best_ask"].to_numpy()
        bb = p["best_bid"].to_numpy()
        n = len(p)
        pos = 0
        buy_idx, sell_idx = [], []
        for i in range(n - 1):
            if np.isnan(wall[i]):
                continue
            my_bid = np.floor(wall[i] - h)
            my_ask = np.ceil(wall[i] + h)
            if not np.isnan(ba[i + 1]) and my_bid >= ba[i + 1] and pos < 200:
                pos += 1
                buy_idx.append(i + 1)
            if not np.isnan(bb[i + 1]) and my_ask <= bb[i + 1] and pos > -200:
                pos -= 1
                sell_idx.append(i + 1)
        print(f"\n[{prod}] h={h}, buys={len(buy_idx)}, sells={len(sell_idx)}")
        for horizon in (5, 10, 50):
            buy_drift = []
            for i in buy_idx:
                if i + horizon < n:
                    buy_drift.append(wall[i + horizon] - wall[i])
            sell_drift = []
            for i in sell_idx:
                if i + horizon < n:
                    sell_drift.append(wall[i + horizon] - wall[i])
            if buy_drift and sell_drift:
                # adverse if buys see negative drift, sells see positive drift
                bd = np.mean(buy_drift); sd = np.mean(sell_drift)
                edge = bd - sd  # positive = favorable (buy then mid up, sell then mid down)
                print(f"  +{horizon:3d}t: drift after BUY ={bd:+.3f}, "
                      f"after SELL ={sd:+.3f}, edge={edge:+.3f}")


# ----- main -----
def main() -> None:
    print("Loading prices...")
    prices = load_prices()
    print("Loading trades...")
    trades = load_trades()  # used for sanity / not heavy

    books = {}
    for prod in PRODUCTS:
        p = per_prod(prices, prod)
        p = add_book_features(p)
        books[prod] = p
        print(f"  {prod}: {len(p)} ticks across days {sorted(p['day'].unique())}")

    print(f"  trades loaded: {len(trades)} rows")

    q1_depth(books)
    q2_wall_mid(books)
    q3_spread(books)
    q4_autocorr(books)
    q5_meanreversion(books)
    q6_fillsim(books)
    q7_q8_inventory_adverse(books)

    print("\nDone. Plots in", PLOTS_DIR)


if __name__ == "__main__":
    main()


### FINDINGS
# Full writeup: docs/round_3/research/04_microstructure.md
#
# - Books are 2-level deep ~98% of ticks for HYDROGEL, ~52% for VFE (rest L1-only).
#   3-level books essentially never appear. Wall = the deeper L2.
# - Wall_mid is only ~12% smoother than top_mid (std ratio 0.88). Use wall_mid as
#   anchor (matches Frankfurt) but expect similar dynamics. d_wall_mid std=1.92
#   for HYDROGEL, 0.98 for VFE.
# - Spread is rock-stable: HYDROGEL=16 (92.7% of ticks), VFE=5 (74%) or 6 (18%).
#   No intraday or per-day drift in the spread.
# - Lag-1 autocorr on wall_mid returns: HYDROGEL -0.01..-0.03 per day, VFE
#   -0.04..-0.05. Weaker than the top-of-book mid_price-based numbers from
#   01_initial_eda.md (most of that signal was bid-ask bounce).
# - Variance ratios 0.90-0.98 for k=2..50 = mild mean reversion, not exploitable
#   on the tick scale. AR(1) half-life ~350-380 ticks.
# - Mock fill sim: at half_edge=8 (HYDROGEL) we're at best bid/ask ~50% of ticks,
#   zero "cross" fills (book never crosses our quote). At half_edge=2 (VFE) we're
#   top-of-book 81% with real cross fills. Recommend possible h=7 sweep for
#   HYDROGEL to put quote inside spread always.
# - VFE shows 213 buys vs 28 sells in the sim — strong long-side asymmetry,
#   suggests skewed quoting may be needed.
# - Adverse selection at +5/+10/+50t is mild on VFE (positive net edge); not
#   measurable on HYDROGEL at h=8 due to no cross fills in the sim.
# - All metrics stable across days 0/1/2 → strategy generalises.
