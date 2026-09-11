"""Generate round-3 data plots.

Run from repo root:
    ./.venv/bin/python notebooks/round3_plots.py

Saves PNGs to notebooks/r3_plots/.
"""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.stats import norm

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data" / "round3"
OUT = REPO / "notebooks" / "r3_plots"
OUT.mkdir(parents=True, exist_ok=True)

DAYS = [0, 1, 2]
STRIKES = [4000, 4500, 5000, 5100, 5200, 5300, 5400, 5500, 6000, 6500]
VEV_SYMS = [f"VEV_{k}" for k in STRIKES]
UND = "VELVETFRUIT_EXTRACT"
HYD = "HYDROGEL_PACK"
TS_PER_DAY = 1_000_000

DPI = 150


def load_prices() -> pd.DataFrame:
    frames = []
    for d in DAYS:
        f = DATA / f"prices_round_3_day_{d}.csv"
        df = pd.read_csv(f, sep=";")
        df["day"] = d
        df["gts"] = df["timestamp"] + d * TS_PER_DAY
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def load_trades() -> pd.DataFrame:
    frames = []
    for d in DAYS:
        f = DATA / f"trades_round_3_day_{d}.csv"
        df = pd.read_csv(f, sep=";")
        df["day"] = d
        df["gts"] = df["timestamp"] + d * TS_PER_DAY
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def pivot_mid(prices: pd.DataFrame, symbols: list[str]) -> pd.DataFrame:
    sub = prices[prices["product"].isin(symbols)]
    return sub.pivot_table(index="gts", columns="product", values="mid_price")


def add_day_boundaries(ax):
    for d in DAYS[1:]:
        ax.axvline(d * TS_PER_DAY, color="k", linestyle=":", alpha=0.3)
    for d in DAYS:
        ax.text(
            d * TS_PER_DAY + TS_PER_DAY / 2,
            ax.get_ylim()[1],
            f"day {d}",
            ha="center",
            va="top",
            fontsize=8,
            color="gray",
        )


def plot_underlying(prices: pd.DataFrame) -> str:
    s = prices[prices["product"] == UND].sort_values("gts")
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(s["gts"], s["mid_price"], lw=0.6, color="tab:blue")
    ax.set_title(f"{UND} mid price — 3 days stitched")
    ax.set_xlabel("global timestamp")
    ax.set_ylabel("mid")
    ax.grid(alpha=0.3)
    add_day_boundaries(ax)
    fig.tight_layout()
    fig.savefig(OUT / "01_velvet_underlying.png", dpi=DPI)
    plt.close(fig)
    return f"VELVET mid: min={s.mid_price.min():.1f} max={s.mid_price.max():.1f} mean={s.mid_price.mean():.1f} std={s.mid_price.std():.1f}"


def plot_chain_snapshots(prices: pd.DataFrame) -> str:
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), sharey=True)
    snap_fracs = [0.1, 0.5, 0.9]
    for ax, d in zip(axes, DAYS):
        day = prices[prices["day"] == d]
        und_day = day[day["product"] == UND].set_index("timestamp")["mid_price"]
        idx_arr = np.asarray(und_day.index)
        for frac in snap_fracs:
            ts_target = int(999900 * frac)
            ts = int(idx_arr[np.abs(idx_arr - ts_target).argmin()])
            S = und_day.loc[ts]
            vev_prices = []
            for k, sym in zip(STRIKES, VEV_SYMS):
                row = day[(day["product"] == sym) & (day["timestamp"] == ts)]
                vev_prices.append(row["mid_price"].iloc[0] if len(row) else np.nan)
            ax.plot(STRIKES, vev_prices, marker="o", label=f"t={ts} S={S:.1f}")
        intrinsic_avg = [max(und_day.mean() - k, 0) for k in STRIKES]
        ax.plot(STRIKES, intrinsic_avg, "k--", alpha=0.5, label="intrinsic @ day-mean S")
        ax.set_title(f"day {d}")
        ax.set_xlabel("strike")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=7)
    axes[0].set_ylabel("VEV mid")
    fig.suptitle("VEV chain snapshots vs intrinsic max(S−K, 0)")
    fig.tight_layout()
    fig.savefig(OUT / "02_vev_chain_snapshots.png", dpi=DPI)
    plt.close(fig)
    spot_mean = prices[prices["product"] == UND]["mid_price"].mean()
    return f"chain snapshots: spot mean={spot_mean:.1f}; strikes span 4000-6500"


def plot_vev_timeseries(prices: pd.DataFrame) -> str:
    fig, axes = plt.subplots(2, 5, figsize=(18, 6), sharex=True)
    for ax, k, sym in zip(axes.flat, STRIKES, VEV_SYMS):
        s = prices[prices["product"] == sym].sort_values("gts")
        ax.plot(s["gts"], s["mid_price"], lw=0.4)
        ax.set_title(sym, fontsize=9)
        ax.grid(alpha=0.3)
        for d in DAYS[1:]:
            ax.axvline(d * TS_PER_DAY, color="k", linestyle=":", alpha=0.3)
    fig.suptitle("VEV mid time series per strike (3 days stitched)")
    fig.tight_layout()
    fig.savefig(OUT / "03_vev_timeseries_grid.png", dpi=DPI)
    plt.close(fig)
    return "vev timeseries: 2x5 grid saved"


def bs_call(S, K, T, sigma, r=0.0):
    if T <= 0 or sigma <= 0:
        return max(S - K, 0.0)
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)


def implied_vol(price, S, K, T):
    intrinsic = max(S - K, 0.0)
    if price <= intrinsic + 1e-6:
        return np.nan
    if price >= S:
        return np.nan
    try:
        return brentq(lambda sig: bs_call(S, K, T, sig) - price, 1e-4, 5.0, xtol=1e-6)
    except Exception:
        return np.nan


def plot_iv_smile(prices: pd.DataFrame) -> str:
    fig, ax = plt.subplots(figsize=(10, 5))
    summary = []
    # TTE assumption: 7 trading days remaining at start of day 0, decreasing linearly
    # across the 3-day sample (each day ≈ 1/252 year). End-of-round target ~4/252 at day-2 end.
    T_start = 7 / 252
    T_end = 4 / 252
    total_gts = 3 * TS_PER_DAY
    for d in DAYS:
        day = prices[prices["day"] == d].copy()
        und = day[day["product"] == UND].set_index("timestamp")["mid_price"]
        iv_by_strike: dict[int, list[float]] = {k: [] for k in STRIKES}
        sample_ts = und.index[::200]  # subsample for speed
        for ts in sample_ts:
            if ts not in und.index:
                continue
            S = und.loc[ts]
            gts = ts + d * TS_PER_DAY
            T = T_start - (T_start - T_end) * (gts / total_gts)
            for k, sym in zip(STRIKES, VEV_SYMS):
                row = day[(day["product"] == sym) & (day["timestamp"] == ts)]
                if not len(row):
                    continue
                p = row["mid_price"].iloc[0]
                if pd.isna(p):
                    continue
                iv = implied_vol(p, S, k, T)
                if not np.isnan(iv):
                    iv_by_strike[k].append(iv)
        means = [np.mean(iv_by_strike[k]) if iv_by_strike[k] else np.nan for k in STRIKES]
        ax.plot(STRIKES, means, marker="o", label=f"day {d}")
        atm_idx = int(np.argmin([abs(k - und.mean()) for k in STRIKES]))
        atm_iv = means[atm_idx] if not np.isnan(means[atm_idx]) else float("nan")
        wing_ivs = [m for m in means if not np.isnan(m)]
        summary.append(f"d{d} ATM≈{atm_iv:.3f} wing_max={max(wing_ivs):.3f}")
    ax.set_title("VEV implied-vol smile per day (BS, r=0, TTE 7→4/252 linear)")
    ax.set_xlabel("strike")
    ax.set_ylabel("implied vol (annualized)")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "04_iv_smile.png", dpi=DPI)
    plt.close(fig)
    return "IV smile: " + " | ".join(summary)


def plot_rv_vs_iv(prices: pd.DataFrame) -> str:
    und = prices[prices["product"] == UND].sort_values("gts").copy()
    und["logret"] = np.log(und["mid_price"]).diff()
    # 100-tick rolling stdev, annualized: 10000 ticks/day, 252 days/year => 2.52M ticks/yr
    window = 500
    und["rv"] = und["logret"].rolling(window).std() * math.sqrt(2_520_000 / window * window)
    # Simpler: annualization factor = sqrt(ticks_per_year / 1) = sqrt(2.52e6) per single-tick stdev
    und["rv"] = und["logret"].rolling(window).std() * math.sqrt(2_520_000)

    # Median IV across strikes at each sampled timestamp (coarse grid for speed)
    T_start = 7 / 252
    T_end = 4 / 252
    total_gts = 3 * TS_PER_DAY
    sample_mask = und["timestamp"] % 2000 == 0
    med_iv = []
    gts_iv = []
    for _, row in und[sample_mask].iterrows():
        S = row["mid_price"]
        gts = row["gts"]
        T = T_start - (T_start - T_end) * (gts / total_gts)
        d = row["day"]
        ts = row["timestamp"]
        day_df = prices[(prices["day"] == d) & (prices["timestamp"] == ts)]
        ivs = []
        for k, sym in zip(STRIKES, VEV_SYMS):
            r = day_df[day_df["product"] == sym]
            if not len(r):
                continue
            p = r["mid_price"].iloc[0]
            if pd.isna(p):
                continue
            iv = implied_vol(p, S, k, T)
            if not np.isnan(iv):
                ivs.append(iv)
        if ivs:
            med_iv.append(np.median(ivs))
            gts_iv.append(gts)

    fig, ax = plt.subplots(figsize=(12, 4.5))
    ax.plot(und["gts"], und["rv"], label=f"realized vol (rolling {window} ticks)", color="tab:blue", lw=0.7)
    ax.plot(gts_iv, med_iv, label="median implied vol across strikes", color="tab:orange", lw=1.0)
    ax.set_title("Realized vs implied volatility (annualized)")
    ax.set_xlabel("global timestamp")
    ax.set_ylabel("vol")
    ax.legend()
    ax.grid(alpha=0.3)
    for d in DAYS[1:]:
        ax.axvline(d * TS_PER_DAY, color="k", linestyle=":", alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "05_realized_vs_implied.png", dpi=DPI)
    plt.close(fig)
    rv_mean = und["rv"].mean()
    iv_mean = np.mean(med_iv) if med_iv else float("nan")
    return f"RV mean={rv_mean:.3f} IV mean={iv_mean:.3f} => {'short vol' if iv_mean > rv_mean else 'long vol'} edge (if stable)"


def plot_hydrogel_price(prices: pd.DataFrame) -> str:
    s = prices[prices["product"] == HYD].sort_values("gts")
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(s["gts"], s["mid_price"], lw=0.5, color="tab:green")
    ax.axhline(10000, color="red", linestyle="--", alpha=0.6, label="FV=10000")
    std = s["mid_price"].std()
    ax.axhspan(10000 - std, 10000 + std, color="red", alpha=0.08, label=f"±1σ={std:.0f}")
    ax.set_title(f"{HYD} mid — 3 days stitched")
    ax.set_xlabel("global timestamp")
    ax.set_ylabel("mid")
    ax.legend()
    ax.grid(alpha=0.3)
    for d in DAYS[1:]:
        ax.axvline(d * TS_PER_DAY, color="k", linestyle=":", alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "06_hydrogel_price.png", dpi=DPI)
    plt.close(fig)
    return f"HYDROGEL mid mean={s.mid_price.mean():.1f} std={std:.2f} range=[{s.mid_price.min():.0f},{s.mid_price.max():.0f}]"


def plot_hydrogel_book(prices: pd.DataFrame) -> str:
    s = prices[prices["product"] == HYD].sort_values("gts").copy()
    s["spread"] = s["ask_price_1"] - s["bid_price_1"]
    s["depth_lvl1"] = s["bid_volume_1"].fillna(0) + s["ask_volume_1"].fillna(0)
    fig, axes = plt.subplots(1, 2, figsize=(14, 4))
    axes[0].plot(s["gts"], s["spread"], lw=0.4, color="tab:purple")
    axes[0].set_title(f"{HYD} bid-ask spread (ticks)")
    axes[0].set_xlabel("global timestamp")
    axes[0].set_ylabel("spread")
    axes[0].grid(alpha=0.3)
    for d in DAYS[1:]:
        axes[0].axvline(d * TS_PER_DAY, color="k", linestyle=":", alpha=0.3)
    axes[1].hist(s["depth_lvl1"], bins=30, color="tab:purple", alpha=0.7)
    axes[1].set_title(f"{HYD} level-1 depth (bid vol + ask vol)")
    axes[1].set_xlabel("units at level 1")
    axes[1].set_ylabel("frequency")
    axes[1].grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "07_hydrogel_book.png", dpi=DPI)
    plt.close(fig)
    return f"HYDROGEL spread mean={s.spread.mean():.2f} median={s.spread.median():.0f}; depth_lvl1 mean={s.depth_lvl1.mean():.1f}"


def plot_trade_counts(trades: pd.DataFrame) -> str:
    counts = trades.groupby(["day", "symbol"]).size().unstack(fill_value=0)
    fig, ax = plt.subplots(figsize=(14, 5))
    counts.T.plot(kind="bar", ax=ax)
    ax.set_title("Trade counts per product per day (from trades CSVs)")
    ax.set_xlabel("product")
    ax.set_ylabel("# trades")
    ax.grid(alpha=0.3, axis="y")
    ax.legend(title="day")
    plt.xticks(rotation=45, ha="right")
    fig.tight_layout()
    fig.savefig(OUT / "08_trade_counts.png", dpi=DPI)
    plt.close(fig)
    total_by_sym = counts.sum(axis=0).sort_values(ascending=False)
    top3 = ", ".join(f"{s}:{n}" for s, n in total_by_sym.head(3).items())
    return f"trade counts 3d total top3: {top3}"


def plot_arb_diagnostics(prices: pd.DataFrame) -> str:
    # Sample at a coarse grid; compute per-day mean of butterfly and vertical spreads
    fig, axes = plt.subplots(1, 2, figsize=(14, 4.5))
    butterfly_by_day = {}
    vertical_by_day = {}
    for d in DAYS:
        day = prices[prices["day"] == d]
        pivot = day[day["product"].isin(VEV_SYMS)].pivot_table(
            index="timestamp", columns="product", values="mid_price"
        )
        # Butterfly: C(K-) - 2 C(K) + C(K+)
        bfly = {}
        for i in range(1, len(STRIKES) - 1):
            k_mid = STRIKES[i]
            try:
                vals = (
                    pivot[f"VEV_{STRIKES[i - 1]}"]
                    - 2 * pivot[f"VEV_{k_mid}"]
                    + pivot[f"VEV_{STRIKES[i + 1]}"]
                )
                bfly[k_mid] = vals.mean()
            except KeyError:
                bfly[k_mid] = np.nan
        butterfly_by_day[d] = bfly
        # Vertical: C(K) - C(K+1)
        vert = {}
        for i in range(len(STRIKES) - 1):
            k = STRIKES[i]
            try:
                vals = pivot[f"VEV_{k}"] - pivot[f"VEV_{STRIKES[i + 1]}"]
                vert[k] = vals.mean()
            except KeyError:
                vert[k] = np.nan
        vertical_by_day[d] = vert

    for d in DAYS:
        ks = list(butterfly_by_day[d].keys())
        vs = [butterfly_by_day[d][k] for k in ks]
        axes[0].plot(ks, vs, marker="o", label=f"day {d}")
        ks2 = list(vertical_by_day[d].keys())
        vs2 = [vertical_by_day[d][k] for k in ks2]
        axes[1].plot(ks2, vs2, marker="o", label=f"day {d}")
    axes[0].axhline(0, color="k", lw=0.5)
    axes[0].set_title("Butterfly: C(K−) − 2·C(K) + C(K+)  (should be ≥ 0)")
    axes[0].set_xlabel("middle strike K")
    axes[0].set_ylabel("butterfly value (day mean)")
    axes[0].legend()
    axes[0].grid(alpha=0.3)
    axes[1].axhline(0, color="k", lw=0.5)
    axes[1].set_title("Vertical: C(K) − C(K+1)  (should be ≥ 0 and ≤ ΔK)")
    axes[1].set_xlabel("lower strike K")
    axes[1].set_ylabel("vertical spread (day mean)")
    axes[1].legend()
    axes[1].grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "09_arb_diagnostics.png", dpi=DPI)
    plt.close(fig)
    # Count any day-mean violations
    violations = 0
    for d in DAYS:
        for k, v in butterfly_by_day[d].items():
            if not np.isnan(v) and v < -0.5:
                violations += 1
        for k, v in vertical_by_day[d].items():
            if not np.isnan(v) and v < -0.5:
                violations += 1
    return f"arb diagnostics: day-mean violations (butterfly<−0.5 or vertical<−0.5): {violations}"


def main() -> None:
    print("loading data...")
    prices = load_prices()
    trades = load_trades()
    print(f"  prices rows={len(prices):,}, trades rows={len(trades):,}")

    print("\nplot 1/9: underlying")
    print(" ", plot_underlying(prices))
    print("plot 2/9: chain snapshots")
    print(" ", plot_chain_snapshots(prices))
    print("plot 3/9: VEV time series grid")
    print(" ", plot_vev_timeseries(prices))
    print("plot 4/9: IV smile (slow — solving BS)")
    print(" ", plot_iv_smile(prices))
    print("plot 5/9: realized vs implied vol")
    print(" ", plot_rv_vs_iv(prices))
    print("plot 6/9: HYDROGEL price")
    print(" ", plot_hydrogel_price(prices))
    print("plot 7/9: HYDROGEL book")
    print(" ", plot_hydrogel_book(prices))
    print("plot 8/9: trade counts")
    print(" ", plot_trade_counts(trades))
    print("plot 9/9: arb diagnostics")
    print(" ", plot_arb_diagnostics(prices))

    print(f"\nwrote PNGs to {OUT}")


if __name__ == "__main__":
    main()
