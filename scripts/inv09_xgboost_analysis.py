"""
inv09: XGBoost/GBT analysis on R5 capsule data.
Train on day 2, evaluate OOS on days 3 & 4.
Features: BI_L1, BI_L2_L3, spread, rolling vol, rolling drift, time-of-day.
Target: next-100-tick mid-price return.
"""

import pandas as pd
import numpy as np
import warnings
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.tree import DecisionTreeRegressor, export_text
from sklearn.metrics import mean_absolute_error, r2_score
import os, json

warnings.filterwarnings("ignore")

DATA_DIR = "/Users/bensinek/Documents/Coding/Prosperity4/data/round_5/prices"
OUT_DIR = "/Users/bensinek/Documents/Coding/Prosperity4/docs/round_5/research"
HORIZON = 100  # ticks
ROLL_VOL = 50
ROLL_DRIFT = 100
MAX_TICKS_PER_DAY = 10000


def load_day(day: int) -> pd.DataFrame:
    path = os.path.join(DATA_DIR, f"prices_round_5_day_{day}.csv")
    df = pd.read_csv(path, sep=";")
    return df


def compute_features(df: pd.DataFrame, product: str) -> pd.DataFrame:
    """Compute features for a single product from price data."""
    p = df[df["product"] == product].copy()
    p = p.sort_values("timestamp").reset_index(drop=True)

    # Mid price
    mid = p["mid_price"].values.astype(float)
    n = len(mid)

    # Spread
    spread = (p["ask_price_1"] - p["bid_price_1"]).values.astype(float)

    # Bid imbalance L1
    bv1 = p["bid_volume_1"].fillna(0).values.astype(float)
    av1 = p["ask_volume_1"].fillna(0).values.astype(float)
    total_l1 = bv1 + av1
    bi_l1 = np.where(total_l1 > 0, (bv1 - av1) / total_l1, 0.0)

    # Bid imbalance L2+L3
    bv23 = (p["bid_volume_2"].fillna(0) + p["bid_volume_3"].fillna(0)).values.astype(float)
    av23 = (p["ask_volume_2"].fillna(0) + p["ask_volume_3"].fillna(0)).values.astype(float)
    total_l23 = bv23 + av23
    bi_l2l3 = np.where(total_l23 > 0, (bv23 - av23) / total_l23, 0.0)

    # Returns
    ret = np.diff(mid, prepend=mid[0]) / np.where(mid > 0, mid, 1.0)

    # Rolling vol (std of last 50 returns)
    ret_series = pd.Series(ret)
    roll_vol = ret_series.rolling(ROLL_VOL, min_periods=5).std().fillna(0).values

    # Rolling drift (mean of last 100 returns)
    roll_drift = ret_series.rolling(ROLL_DRIFT, min_periods=10).mean().fillna(0).values

    # Time of day (normalized 0-1 within the day)
    ts = p["timestamp"].values.astype(float)
    tod = ts / MAX_TICKS_PER_DAY

    # Target: next-100-tick forward return
    fwd_mid = np.empty(n)
    fwd_mid[:] = np.nan
    for i in range(n - HORIZON):
        fwd_mid[i] = (mid[i + HORIZON] - mid[i]) / mid[i] if mid[i] != 0 else 0.0

    features = pd.DataFrame({
        "bi_l1": bi_l1,
        "bi_l2l3": bi_l2l3,
        "spread": spread,
        "roll_vol": roll_vol,
        "roll_drift": roll_drift,
        "tod": tod,
        "fwd_ret": fwd_mid,
    })

    return features.dropna()


def directional_accuracy(y_true, y_pred):
    """Fraction of times sign(pred) == sign(true), ignoring exact zeros."""
    mask = y_true != 0
    if mask.sum() == 0:
        return np.nan
    return (np.sign(y_pred[mask]) == np.sign(y_true[mask])).mean()


def fit_product(df2: pd.DataFrame, product: str):
    """Build features for day 2, return fitted model + feature cols."""
    feats = compute_features(df2, product)
    if len(feats) < 200:
        return None, None, None
    feature_cols = ["bi_l1", "bi_l2l3", "spread", "roll_vol", "roll_drift", "tod"]
    X = feats[feature_cols].values
    y = feats["fwd_ret"].values
    model = GradientBoostingRegressor(
        n_estimators=50,
        max_depth=3,
        learning_rate=0.1,
        subsample=0.8,
        random_state=42,
    )
    model.fit(X, y)
    return model, feature_cols, feats


def eval_product(model, feature_cols, df_eval: pd.DataFrame, product: str):
    """Evaluate model on OOS day."""
    feats = compute_features(df_eval, product)
    if len(feats) < 50:
        return None
    X = feats[feature_cols].values
    y = feats["fwd_ret"].values
    y_pred = model.predict(X)
    mae = mean_absolute_error(y, y_pred)
    r2 = r2_score(y, y_pred)
    dir_acc = directional_accuracy(y, y_pred)
    return {"mae": mae, "r2": r2, "dir_acc": dir_acc, "n": len(y)}


def extract_single_tree_rules(model, feature_names, max_depth=3, tree_idx=0):
    """Extract a single decision tree from the ensemble as if-else Python."""
    # Use first tree (stage 0, output 0)
    tree = model.estimators_[tree_idx][0]
    tree_rules = export_text(tree, feature_names=feature_names, max_depth=max_depth)
    return tree_rules


def build_simple_stump(df2: pd.DataFrame, product: str, feature_cols: list):
    """Fit a shallow (depth 3) single tree for hand-coding."""
    feats = compute_features(df2, product)
    if len(feats) < 200:
        return None
    X = feats[feature_cols].values
    y = feats["fwd_ret"].values
    stump = DecisionTreeRegressor(max_depth=3, random_state=42)
    stump.fit(X, y)
    return stump


def tree_to_python(tree, feature_names, func_name="predict_signal"):
    """Convert a sklearn DecisionTreeRegressor to Python if/else code."""
    from sklearn.tree import _tree
    tree_ = tree.tree_
    feature_name = [
        feature_names[i] if i != _tree.TREE_UNDEFINED else "undefined!"
        for i in tree_.feature
    ]
    lines = []
    lines.append(f"def {func_name}(bi_l1, bi_l2l3, spread, roll_vol, roll_drift, tod):")
    lines.append(f"    # Auto-generated from depth-3 decision tree stump")

    def recurse(node, depth):
        indent = "    " * (depth + 1)
        if tree_.feature[node] != _tree.TREE_UNDEFINED:
            name = feature_name[node]
            threshold = tree_.threshold[node]
            lines.append(f"{indent}if {name} <= {threshold:.6f}:")
            recurse(tree_.children_left[node], depth + 1)
            lines.append(f"{indent}else:  # {name} > {threshold:.6f}")
            recurse(tree_.children_right[node], depth + 1)
        else:
            val = tree_.value[node][0][0]
            lines.append(f"{indent}return {val:.8f}")

    recurse(0, 0)
    return "\n".join(lines)


def main():
    print("Loading data...")
    df2 = load_day(2)
    df3 = load_day(3)
    df4 = load_day(4)

    products = sorted(df2["product"].unique())
    print(f"Products: {len(products)}")

    results = {}
    good_products = []
    feature_cols = ["bi_l1", "bi_l2l3", "spread", "roll_vol", "roll_drift", "tod"]

    for i, product in enumerate(products):
        print(f"  [{i+1}/{len(products)}] {product} ... ", end="", flush=True)
        model, fc, feats_train = fit_product(df2, product)
        if model is None:
            print("SKIP (insufficient data)")
            results[product] = None
            continue

        r3 = eval_product(model, fc, df3, product)
        r4 = eval_product(model, fc, df4, product)

        if r3 is None or r4 is None:
            print("SKIP (OOS insufficient data)")
            results[product] = None
            continue

        results[product] = {"day3": r3, "day4": r4}
        avg_dir = (r3["dir_acc"] + r4["dir_acc"]) / 2
        print(f"dir_acc day3={r3['dir_acc']:.3f} day4={r4['dir_acc']:.3f} avg={avg_dir:.3f}")

        if r3["dir_acc"] > 0.55 and r4["dir_acc"] > 0.55:
            good_products.append(product)

    print(f"\nGood OOS products (>55% both days): {good_products}")

    # --- Build summary table ---
    rows = []
    for product, res in results.items():
        if res is None:
            rows.append({"product": product, "d3_dir_acc": None, "d4_dir_acc": None,
                         "d3_r2": None, "d4_r2": None, "d3_mae": None, "d4_mae": None})
            continue
        rows.append({
            "product": product,
            "d3_dir_acc": round(res["day3"]["dir_acc"], 4),
            "d4_dir_acc": round(res["day4"]["dir_acc"], 4),
            "d3_r2": round(res["day3"]["r2"], 4),
            "d4_r2": round(res["day4"]["r2"], 4),
            "d3_mae": round(res["day3"]["mae"], 8),
            "d4_mae": round(res["day4"]["mae"], 8),
        })

    df_results = pd.DataFrame(rows).sort_values("d3_dir_acc", ascending=False)

    # Save results JSON for doc generation
    with open("/tmp/inv09_results.json", "w") as f:
        json.dump({"results": results, "good_products": good_products,
                   "table": df_results.to_dict(orient="records")}, f, indent=2, default=str)

    # --- Dump tree code for good products ---
    tree_lines = []
    tree_lines.append("# inv09_trees.py — hand-codable decision tree stumps for R5")
    tree_lines.append("# Generated from depth-3 single DecisionTreeRegressor trained on day 2 only")
    tree_lines.append("# Inference: call predict_PRODUCT(bi_l1, bi_l2l3, spread, roll_vol, roll_drift, tod)")
    tree_lines.append("# Returns: estimated next-100-tick return (use sign for direction signal)")
    tree_lines.append("")

    if good_products:
        for product in good_products:
            stump = build_simple_stump(df2, product, feature_cols)
            if stump is not None:
                safe_name = product.replace(" ", "_").replace("-", "_")
                code = tree_to_python(stump, feature_cols, func_name=f"predict_{safe_name}")
                tree_lines.append(code)
                tree_lines.append("")
        print(f"\nDumping {len(good_products)} tree(s) to docs/round_5/research/inv09_trees.py")

    # Save trees
    with open("/tmp/inv09_trees.py", "w") as f:
        f.write("\n".join(tree_lines))

    return df_results, good_products


if __name__ == "__main__":
    df_results, good_products = main()
    print("\n=== TOP 20 BY DAY3 DIR ACC ===")
    print(df_results.head(20).to_string(index=False))
