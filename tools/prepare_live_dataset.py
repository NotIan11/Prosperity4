"""
Convert a live round log (JSON + .log) into a rust_backtester dataset.

Usage:
    python tools/prepare_live_dataset.py logs/r3live/485250 data/r3live
"""
import json
import os
import sys


def main():
    if len(sys.argv) < 3:
        print("Usage: prepare_live_dataset.py <log_prefix> <out_dir>")
        sys.exit(1)

    prefix = sys.argv[1]
    out_dir = sys.argv[2]
    os.makedirs(out_dir, exist_ok=True)

    json_path = prefix + ".json"
    log_path = prefix + ".log"

    # ── prices CSV from activitiesLog ────────────────────────────────────────
    with open(json_path) as f:
        data = json.load(f)

    activities = data["activitiesLog"]
    # Determine day number from first data row
    lines = activities.strip().split("\n")
    header = lines[0]
    first_row = lines[1] if len(lines) > 1 else ""
    day_num = int(first_row.split(";")[0]) if first_row else 0

    prices_path = os.path.join(out_dir, f"prices_round_live_day_{day_num}.csv")
    with open(prices_path, "w") as f:
        f.write(activities)
        if not activities.endswith("\n"):
            f.write("\n")
    print(f"Wrote {prices_path}")

    # ── trades CSV from .log ─────────────────────────────────────────────────
    with open(log_path) as f:
        log_data = json.load(f)

    # .log is a JSON dict with a "tradeHistory" list
    trades = log_data["tradeHistory"]

    trades_header = "timestamp;buyer;seller;symbol;currency;price;quantity"
    trades_path = os.path.join(out_dir, f"trades_round_live_day_{day_num}.csv")
    with open(trades_path, "w") as f:
        f.write(trades_header + "\n")
        for t in trades:
            row = ";".join([
                str(t.get("timestamp", "")),
                str(t.get("buyer", "")),
                str(t.get("seller", "")),
                str(t.get("symbol", "")),
                str(t.get("currency", "")),
                str(t.get("price", "")),
                str(t.get("quantity", "")),
            ])
            f.write(row + "\n")
    print(f"Wrote {trades_path} ({len(trades)} trades)")
    print(f"Dataset ready → {out_dir}  (day {day_num})")


if __name__ == "__main__":
    main()
