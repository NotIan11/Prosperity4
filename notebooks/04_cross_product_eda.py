"""R3 cross-product EDA: cointegration, lead-lag, Granger, PCA, regime, day-stability.

Run: venv/bin/python notebooks/04_cross_product_eda.py
Plots: docs/round_3/research/plots/04_*.png
Findings: docs/round_3/research/06_cross_product.md (written manually, not by this script).
"""
from __future__ import annotations

import glob
import math
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats
from statsmodels.tsa.stattools import adfuller, kpss, coint, grangercausalitytests
from statsmodels.tsa.stattools import acf

warnings.filterwarnings("ignore")

ROOT = Path("/Users/bensinek/Documents/Coding/Prosperity4")
DATA_GLOB = str(ROOT / "data/round_3/prices_round_3_day_*.csv")
PLOTS = ROOT / "docs/round_3/research/plots"
PLOTS.mkdir(parents=True, exist_ok=True)

DEAD = {"VEV_6000", "VEV_6500"}  # variance ~ 0
GOODS = ["HYDROGEL_PACK", "VELVETFRUIT_EXTRACT"]


# ---------------- load ----------------

def load_wide() -> pd.DataFrame:
    df = pd.concat([pd.read_csv(f, sep=";") for f in sorted(glob.glob(DATA_GLOB))],
                   ignore_index=True)
    df["t"] = df.day * 1_000_000 + df.timestamp
    wide = (df.pivot_table(index=["day", "timestamp", "t"],
                           columns="product", values="mid_price")
              .reset_index().sort_values("t").reset_index(drop=True))
    return wide


def live_products(wide: pd.DataFrame) -> list[str]:
    cols = [c for c in wide.columns if c not in ("day", "timestamp", "t")]
    return [c for c in cols if c not in DEAD and wide[c].std() > 0]


# ---------------- 1. cointegration: HYDROGEL vs each ----------------

def hydrogel_cointegration(wide: pd.DataFrame, prods: list[str]) -> pd.DataFrame:
    rows = []
    h = wide["HYDROGEL_PACK"].dropna()
    for p in prods:
        if p == "HYDROGEL_PACK":
            continue
        s = wide[p].dropna()
        idx = h.index.intersection(s.index)
        try:
            t, pval, _ = coint(h.loc[idx], s.loc[idx])
        except Exception as e:  # noqa: BLE001
            t, pval = np.nan, np.nan
        rows.append({"product": p, "eg_tstat": t, "eg_pvalue": pval})
    out = pd.DataFrame(rows).sort_values("eg_pvalue")
    return out


# ---------------- 2. lead-lag CCF ----------------

def ccf(x: pd.Series, y: pd.Series, max_lag: int = 50) -> tuple[np.ndarray, np.ndarray]:
    """Cross-correlation: corr(x_t, y_{t+lag}). Positive lag => y leads x's future = x leads y."""
    x = (x - x.mean()) / x.std()
    y = (y - y.mean()) / y.std()
    n = len(x)
    lags = np.arange(-max_lag, max_lag + 1)
    out = np.zeros_like(lags, dtype=float)
    for i, k in enumerate(lags):
        if k >= 0:
            out[i] = np.corrcoef(x[: n - k], y[k:])[0, 1] if n - k > 10 else np.nan
        else:
            kk = -k
            out[i] = np.corrcoef(x[kk:], y[: n - kk])[0, 1] if n - kk > 10 else np.nan
    return lags, out


def leadlag_table(rets: pd.DataFrame, pairs: list[tuple[str, str]],
                  max_lag: int = 50) -> pd.DataFrame:
    rows = []
    for a, b in pairs:
        x = rets[a].dropna()
        y = rets[b].dropna()
        idx = x.index.intersection(y.index)
        lags, c = ccf(x.loc[idx], y.loc[idx], max_lag=max_lag)
        valid = ~np.isnan(c)
        if not valid.any():
            continue
        i_peak = np.nanargmax(np.abs(c))
        rows.append({
            "a": a, "b": b,
            "peak_lag": int(lags[i_peak]),
            "peak_corr": float(c[i_peak]),
            "corr_lag0": float(c[lags == 0][0]),
        })
    return pd.DataFrame(rows).sort_values("peak_corr", key=lambda s: s.abs(), ascending=False)


# ---------------- 3. Granger causality ----------------

def granger(rets: pd.DataFrame, a: str, b: str, max_lag: int = 5) -> dict:
    """H0: a does NOT Granger-cause b. Returns p-value at best lag."""
    x = rets[[b, a]].dropna()
    if len(x) < 100:
        return {"a": a, "b": b, "min_p": np.nan, "best_lag": np.nan}
    try:
        res = grangercausalitytests(x, maxlag=max_lag, verbose=False)
        ps = {lag: res[lag][0]["ssr_ftest"][1] for lag in res}
        best = min(ps, key=ps.get)
        return {"a": a, "b": b, "min_p": ps[best], "best_lag": best}
    except Exception:
        return {"a": a, "b": b, "min_p": np.nan, "best_lag": np.nan}


# ---------------- 4. cointegration heatmap (vouchers) ----------------

def voucher_cointegration_matrix(wide: pd.DataFrame,
                                  vouchers: list[str]) -> pd.DataFrame:
    n = len(vouchers)
    M = pd.DataFrame(np.ones((n, n)), index=vouchers, columns=vouchers)
    for i, a in enumerate(vouchers):
        for j, b in enumerate(vouchers):
            if i >= j:
                continue
            x, y = wide[a].dropna(), wide[b].dropna()
            idx = x.index.intersection(y.index)
            try:
                _, p, _ = coint(x.loc[idx], y.loc[idx])
            except Exception:
                p = np.nan
            M.loc[a, b] = p
            M.loc[b, a] = p
    return M


# ---------------- 5. PCA on returns ----------------

def pca_returns(rets: pd.DataFrame, prods: list[str]) -> tuple[np.ndarray, np.ndarray, pd.DataFrame]:
    R = rets[prods].dropna()
    Z = (R - R.mean()) / R.std()
    cov = np.cov(Z.values.T)
    eigvals, eigvecs = np.linalg.eigh(cov)
    order = np.argsort(eigvals)[::-1]
    eigvals = eigvals[order]
    eigvecs = eigvecs[:, order]
    explained = eigvals / eigvals.sum()
    loadings = pd.DataFrame(eigvecs, index=prods,
                            columns=[f"PC{i+1}" for i in range(len(prods))])
    return explained, eigvals, loadings


# ---------------- 6. stationarity ----------------

def stationarity_table(wide: pd.DataFrame, prods: list[str]) -> pd.DataFrame:
    rows = []
    for p in prods:
        s = wide[p].dropna()
        r = np.log(s).diff().dropna()
        try:
            adf_lvl = adfuller(s, autolag="AIC")[1]
        except Exception:
            adf_lvl = np.nan
        try:
            kpss_lvl = kpss(s, nlags="auto")[1]
        except Exception:
            kpss_lvl = np.nan
        try:
            adf_ret = adfuller(r, autolag="AIC")[1]
        except Exception:
            adf_ret = np.nan
        try:
            kpss_ret = kpss(r, nlags="auto")[1]
        except Exception:
            kpss_ret = np.nan
        rows.append({"product": p,
                     "adf_lvl_p": adf_lvl, "kpss_lvl_p": kpss_lvl,
                     "adf_ret_p": adf_ret, "kpss_ret_p": kpss_ret})
    return pd.DataFrame(rows)


# ---------------- 7. delta-weighted basket vs VFE ----------------

def bs_call_delta(S: float, K: float, T: float, sigma: float) -> float:
    if T <= 0 or sigma <= 0 or S <= 0:
        return 1.0 if S > K else 0.0
    d1 = (math.log(S / K) + 0.5 * sigma * sigma * T) / (sigma * math.sqrt(T))
    return 0.5 * (1 + math.erf(d1 / math.sqrt(2)))


def basket_spread(wide: pd.DataFrame) -> pd.DataFrame:
    """Build basket = sum(delta_i * voucher_mid_i) and compare to VFE."""
    sigma = 0.15
    # TTE per day in years (R1=7d expiry, days 0/1/2 -> tte 8,7,6 days)
    tte_per_day = {0: 8 / 365, 1: 7 / 365, 2: 6 / 365}
    strikes = [4000, 4500, 5000, 5100, 5200, 5300, 5400, 5500]
    vouchers = [f"VEV_{k}" for k in strikes]
    sub = wide[["day", "t", "VELVETFRUIT_EXTRACT"] + vouchers].dropna().copy()
    deltas = pd.DataFrame(index=sub.index, columns=vouchers, dtype=float)
    for i, row in sub.iterrows():
        T = tte_per_day[int(row["day"])]
        S = row["VELVETFRUIT_EXTRACT"]
        for K, v in zip(strikes, vouchers):
            deltas.at[i, v] = bs_call_delta(S, K, T, sigma)
    basket = (deltas.values * sub[vouchers].values).sum(axis=1)
    sub["basket"] = basket
    sub["spread"] = sub["basket"] - sub["VELVETFRUIT_EXTRACT"]
    return sub[["day", "t", "VELVETFRUIT_EXTRACT", "basket", "spread"]]


# ---------------- 8. volatility clustering ----------------

def vol_clustering(rets: pd.DataFrame, prods: list[str], nlags: int = 20) -> pd.DataFrame:
    rows = []
    for p in prods:
        r = rets[p].dropna()
        if len(r) < 100:
            continue
        # Ljung-Box on r^2
        sq = r ** 2
        ac = acf(sq, nlags=nlags, fft=True)
        rows.append({"product": p, "acf_sq_lag1": ac[1],
                     "acf_sq_lag5": ac[5], "acf_sq_lag10": ac[10]})
    return pd.DataFrame(rows)


# ---------------- 9. day stability ----------------

def per_day_corr(wide: pd.DataFrame, prods: list[str]) -> dict:
    out = {}
    for d in sorted(wide["day"].unique()):
        sub = wide[wide["day"] == d]
        rets = np.log(sub[prods]).diff()
        out[int(d)] = rets.corr()
    return out


# ===================== MAIN =====================

def main() -> None:
    wide = load_wide()
    prods = live_products(wide)
    vouchers = [p for p in prods if p.startswith("VEV_")]
    print(f"live products ({len(prods)}): {prods}")
    rets = np.log(wide[prods]).diff()

    # 1. HYDROGEL cointegration
    print("\n=== 1. Engle-Granger cointegration: HYDROGEL vs each ===")
    eg = hydrogel_cointegration(wide, prods)
    print(eg.to_string(index=False))

    # 6. Stationarity
    print("\n=== 6. Stationarity (ADF p-val for unit root, KPSS p-val for stationarity) ===")
    stn = stationarity_table(wide, prods)
    print(stn.round(4).to_string(index=False))

    # 2. Lead-lag CCF
    print("\n=== 2. Lead-lag CCF peaks (returns, ±50 ticks) ===")
    pairs = []
    # VFE vs each voucher
    for v in vouchers:
        pairs.append(("VELVETFRUIT_EXTRACT", v))
    # adjacent vouchers
    for i in range(len(vouchers) - 1):
        pairs.append((vouchers[i], vouchers[i + 1]))
    # HYDROGEL vs all
    for p in prods:
        if p != "HYDROGEL_PACK":
            pairs.append(("HYDROGEL_PACK", p))
    ll = leadlag_table(rets, pairs, max_lag=50)
    print(ll.to_string(index=False))

    # Plot CCF for top 4 pairs by |peak_corr|
    top = ll.head(6)
    fig, axes = plt.subplots(2, 3, figsize=(15, 7))
    for ax, (_, row) in zip(axes.flatten(), top.iterrows()):
        a, b = row["a"], row["b"]
        idx = rets[a].dropna().index.intersection(rets[b].dropna().index)
        lags, c = ccf(rets[a].loc[idx], rets[b].loc[idx], 50)
        ax.bar(lags, c, width=1.0)
        ax.axvline(0, color="k", lw=0.5)
        ax.axhline(0, color="k", lw=0.5)
        ax.set_title(f"{a} vs {b}\npeak_lag={row['peak_lag']} corr={row['peak_corr']:.2f}",
                     fontsize=9)
        ax.set_xlabel("lag (b leads a if lag<0)")
    fig.tight_layout()
    fig.savefig(PLOTS / "04_leadlag_ccf_top.png", dpi=110)
    plt.close(fig)

    # 3. Granger on top correlated pairs (lag != 0 ones first)
    print("\n=== 3. Granger causality (top pairs, max_lag=5) ===")
    g_rows = []
    for _, row in ll.head(8).iterrows():
        g_rows.append(granger(rets, row["a"], row["b"], 5))
        g_rows.append(granger(rets, row["b"], row["a"], 5))
    gdf = pd.DataFrame(g_rows)
    print(gdf.to_string(index=False))

    # 4. Voucher cointegration heatmap
    print("\n=== 4. Voucher cointegration matrix (Engle-Granger p-values) ===")
    M = voucher_cointegration_matrix(wide, vouchers)
    print(M.round(3).to_string())
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(M.astype(float), annot=True, fmt=".2f", cmap="viridis_r",
                vmin=0, vmax=0.2, ax=ax, cbar_kws={"label": "EG p-value (capped 0.2)"})
    ax.set_title("Voucher pairwise Engle-Granger cointegration p-values\n(<0.05 = cointegrated)")
    fig.tight_layout()
    fig.savefig(PLOTS / "04_voucher_coint_heatmap.png", dpi=110)
    plt.close(fig)

    cointegrated_pairs = []
    for i, a in enumerate(vouchers):
        for j, b in enumerate(vouchers):
            if i < j and M.loc[a, b] < 0.05:
                cointegrated_pairs.append((a, b, M.loc[a, b]))
    print("Cointegrated voucher pairs (p<0.05):", cointegrated_pairs)

    # 5. PCA
    print("\n=== 5. PCA on returns ===")
    explained, eigvals, loadings = pca_returns(rets, prods)
    print("Explained variance ratio:", np.round(explained, 4))
    print("Cumulative:", np.round(np.cumsum(explained), 4))
    n95 = int(np.argmax(np.cumsum(explained) >= 0.95) + 1)
    print(f"# factors for >=95% variance: {n95}")
    print("\nLoadings PC1..PC4:")
    print(loadings.iloc[:, :4].round(3).to_string())

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    axes[0].bar(range(1, len(explained) + 1), explained)
    axes[0].plot(range(1, len(explained) + 1), np.cumsum(explained), "o-r")
    axes[0].axhline(0.95, color="grey", ls="--")
    axes[0].set_xlabel("PC")
    axes[0].set_ylabel("explained var ratio")
    axes[0].set_title("Scree (bars) + cumulative (red)")
    sns.heatmap(loadings.iloc[:, :4], annot=True, fmt=".2f",
                cmap="RdBu_r", center=0, ax=axes[1])
    axes[1].set_title("PC1..PC4 loadings")
    fig.tight_layout()
    fig.savefig(PLOTS / "04_pca_scree_loadings.png", dpi=110)
    plt.close(fig)

    # 7. Basket vs VFE spread
    print("\n=== 7. Delta-weighted voucher basket vs VFE (sigma=0.15) ===")
    bsk = basket_spread(wide)
    sp = bsk["spread"]
    try:
        adf_p = adfuller(sp, autolag="AIC")[1]
    except Exception:
        adf_p = np.nan
    print(f"basket mean={bsk['basket'].mean():.2f}, VFE mean={bsk['VELVETFRUIT_EXTRACT'].mean():.2f}")
    print(f"spread mean={sp.mean():.2f}, std={sp.std():.2f}, ADF p={adf_p:.4f}")
    fig, axes = plt.subplots(2, 1, figsize=(12, 6))
    axes[0].plot(bsk["t"], bsk["basket"], label="basket(Σδ·voucher)", lw=0.6)
    axes[0].plot(bsk["t"], bsk["VELVETFRUIT_EXTRACT"], label="VFE", lw=0.6)
    axes[0].legend(); axes[0].set_title("Basket vs VFE")
    axes[1].plot(bsk["t"], sp, lw=0.4)
    axes[1].axhline(sp.mean(), color="r", ls="--")
    axes[1].set_title(f"Spread = basket − VFE  (ADF p={adf_p:.4f})")
    fig.tight_layout()
    fig.savefig(PLOTS / "04_basket_vs_vfe.png", dpi=110)
    plt.close(fig)

    # 8. Vol clustering
    print("\n=== 8. Volatility clustering (ACF of squared returns) ===")
    vc = vol_clustering(rets, prods)
    print(vc.round(3).to_string(index=False))

    # 9. Day stability — corr between days (focus VFE-near-ATM)
    print("\n=== 9. Per-day return correlations: VFE × VEV_5000 / VEV_5200 / HYDROGEL ===")
    per_day = per_day_corr(wide, prods)
    focus = ["VELVETFRUIT_EXTRACT", "VEV_5000", "VEV_5200", "HYDROGEL_PACK"]
    for d, C in per_day.items():
        present = [p for p in focus if p in C.columns]
        print(f"--- day {d} ---")
        print(C.loc[present, present].round(2).to_string())

    print("\n### FINDINGS")
    print("- HYDROGEL_PACK Engle-Granger min p-value across all other live products:",
          f"{eg['eg_pvalue'].min():.4f}")
    print(f"- Cointegrated voucher pairs (EG p<0.05): {len(cointegrated_pairs)}")
    print(f"- # PCs for 95% variance: {n95}")
    print(f"- Basket-VFE spread ADF p: {adf_p:.4f}")
    print("- Top lead-lag (peak_lag != 0):",
          ll[ll["peak_lag"] != 0].head(3).to_dict("records"))


if __name__ == "__main__":
    main()


### FINDINGS
# - HYDROGEL is statistically "cointegrated" with every product at p<0.0001, BUT
#   ADF rejects unit root in HYDROGEL levels (p=0.0000) — HYDROGEL is already
#   stationary (mean-reverting around 9991). EG cointegration on a stationary
#   series is degenerate / not meaningful. Combined with: (a) lag-0 return
#   correlation ~0.00, (b) max |CCF| over ±50 lags is 0.02 (noise level), and
#   (c) per-day correlations identical across days 0/1/2 — HYDROGEL is genuinely
#   independent. Verdict: **trade HYDROGEL standalone, no cross-asset hedge.**
#
# - Lead-lag: ALL meaningful pairs peak at lag 0. No exploitable lead-lag in
#   returns at the 1-tick scale. Granger tests are significant in BOTH directions
#   (p≈0) for VFE↔voucher and adjacent-strike pairs — that's contemporaneous
#   co-movement leaking into the lag structure, not directional causality.
#
# - Voucher cointegration: VEV_5500 cointegrates with everything (p<0.05) and
#   the deepest-ITM pair VEV_4000–VEV_4500 is cointegrated at p≈0.
#   Caveat: VEV_4000/4500 are deep-ITM ⇒ near-pure delta-1 proxies for VFE,
#   so they are essentially the same series shifted by intrinsic value.
#   VEV_5500's "cointegration" is partly an artifact of its low variance (it is
#   close to dead like VEV_6000/6500). Real spread trade candidates are limited.
#
# - PCA: PC1 = 60.5% (uniform negative loadings on VFE + all 8 vouchers) =
#   "VFE factor" exactly as expected. PC2 = 10.0% and is HYDROGEL ALONE
#   (loading -1.00) — confirms HYDROGEL is its own orthogonal factor.
#   PC3/PC4 (8.5%/6.4%) capture wing-vs-belly: PC3 contrasts VEV_5500 vs the
#   rest (skew/wing factor), PC4 contrasts VEV_5400 vs the deep-ITM 4000/4500
#   (curvature). 95% variance needs 7 PCs — long tail of idiosyncratic
#   per-strike noise, no obvious clean residual stat-arb.
#
# - Basket vs VFE: delta-weighted basket (σ=0.15, BS deltas) and VFE differ by
#   ~2761 (intrinsic value of the deep-ITM strikes — basket = ΣΔ·V is NOT the
#   underlying replication). Spread is mean-reverting (ADF p=0.0000) but with
#   std=62 dominated by the changing intrinsic. NOT directly tradeable as
#   stat-arb without a proper put-call-parity / synthetic-underlying construction
#   (left to the voucher chain agent).
#
# - Vol clustering: VEV_4000/4500 (deep-ITM) ACF(r²,lag1)=0.41/0.35 — strong
#   GARCH effect inherited from VFE level moves. Wing strikes VEV_5400/5500
#   ACF=0.16/0.31. VFE itself = 0.11, HYDROGEL = 0.13 — modest. No big regime
#   signal in HYDROGEL's vol process worth modelling.
#
# - Day stability: correlations are identical to 2 decimals across days 0/1/2.
#   Whatever structure exists generalises. No regime shift between days.
