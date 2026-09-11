#!/usr/bin/env python3
"""Analyze pepper trades data to find if market making beats holding.

For each tick where we see pepper trades, we look at:
1. The trade price vs mid price
2. Short-term price movements after trades
3. Whether selling at a trade price and rebuying later has positive EV
4. Spread capture opportunities vs drift cost

Key question: is there a predictable condition where sell+rebuy > hold?
"""
import csv
import os
import statistics
from collections import defaultdict

DATA = os.path.join(os.path.dirname(__file__), '..', 'data')

def load_prices(path):
    """Load prices CSV, return dict of timestamp -> row for pepper."""
    prices = {}
    with open(path) as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            if row['product'] == 'INTARIAN_PEPPER_ROOT':
                ts = int(row['timestamp'])
                prices[ts] = {
                    'bid1': float(row['bid_price_1']) if row['bid_price_1'] else None,
                    'bid_vol1': int(row['bid_volume_1']) if row['bid_volume_1'] else 0,
                    'bid2': float(row['bid_price_2']) if row['bid_price_2'] else None,
                    'bid_vol2': int(row['bid_volume_2']) if row['bid_volume_2'] else 0,
                    'ask1': float(row['ask_price_1']) if row['ask_price_1'] else None,
                    'ask_vol1': int(row['ask_volume_1']) if row['ask_volume_1'] else 0,
                    'ask2': float(row['ask_price_2']) if row['ask_price_2'] else None,
                    'ask_vol2': int(row['ask_volume_2']) if row['ask_volume_2'] else 0,
                    'mid': float(row['mid_price']) if row['mid_price'] else None,
                }
    return prices

def load_trades(path):
    """Load trades CSV, return list of pepper trades."""
    trades = []
    with open(path) as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            if row['symbol'] == 'INTARIAN_PEPPER_ROOT':
                trades.append({
                    'timestamp': int(row['timestamp']),
                    'buyer': row['buyer'],
                    'seller': row['seller'],
                    'price': float(row['price']),
                    'quantity': int(row['quantity']),
                })
    return trades

def analyze_day(prices_path, trades_path, label):
    prices = load_prices(prices_path)
    trades = load_trades(trades_path)
    
    timestamps = sorted(prices.keys())
    ts_to_idx = {ts: i for i, ts in enumerate(timestamps)}
    
    print(f"\n{'='*70}")
    print(f"  {label}")
    print(f"{'='*70}")
    
    # Basic stats
    pepper_trades = [t for t in trades]
    print(f"Pepper trades: {len(pepper_trades)}")
    
    if not pepper_trades:
        return
    
    # 1. Price drift per tick
    mids = [(ts, prices[ts]['mid']) for ts in timestamps if prices[ts]['mid'] is not None]
    if len(mids) > 1:
        drift = (mids[-1][1] - mids[0][1]) / (len(mids) - 1)
        total_drift = mids[-1][1] - mids[0][1]
        print(f"Total drift: {total_drift:.1f}, drift/tick: {drift:.3f}")
    
    # 2. Spread analysis at trade timestamps
    spreads_at_trade = []
    for t in pepper_trades:
        ts = t['timestamp']
        if ts in prices and prices[ts]['bid1'] is not None and prices[ts]['ask1'] is not None:
            spread = prices[ts]['ask1'] - prices[ts]['bid1']
            spreads_at_trade.append(spread)
    
    if spreads_at_trade:
        print(f"Spread at trade times: mean={statistics.mean(spreads_at_trade):.1f}, "
              f"median={statistics.median(spreads_at_trade):.1f}, "
              f"min={min(spreads_at_trade):.0f}, max={max(spreads_at_trade):.0f}")
    
    # 3. For each trade, compute: if we sold at trade price, what's the cost to rebuy?
    # Look at next N ticks' best ask price
    horizons = [1, 2, 3, 5, 10, 20, 50]
    
    print(f"\n--- Sell at trade price, rebuy at best_ask after N ticks ---")
    print(f"  (Positive = sell+rebuy beats hold)")
    print(f"{'Horizon':>10} {'Mean PnL':>10} {'Median':>10} {'Win%':>8} {'Count':>8}")
    
    for h in horizons:
        pnls = []
        for t in pepper_trades:
            ts = t['timestamp']
            if ts not in ts_to_idx:
                continue
            idx = ts_to_idx[ts]
            if idx + h >= len(timestamps):
                continue
            
            sell_price = t['price']
            future_ts = timestamps[idx + h]
            if future_ts in prices and prices[future_ts]['ask1'] is not None:
                rebuy_price = prices[future_ts]['ask1']
                # PnL of sell+rebuy vs hold:
                # sell+rebuy: sell_price - rebuy_price (per unit)
                # hold: future_mid - current_mid (per unit) -- but we already hold
                # Net advantage = sell_price - rebuy_price - drift_cost
                # Or simpler: sell at sell_price, rebuy at rebuy_price
                # Profit = sell_price - rebuy_price (negative if price went up)
                pnl = sell_price - rebuy_price
                pnls.append(pnl)
        
        if pnls:
            win_pct = sum(1 for p in pnls if p > 0) / len(pnls) * 100
            print(f"{h:>10} {statistics.mean(pnls):>10.2f} {statistics.median(pnls):>10.2f} {win_pct:>7.1f}% {len(pnls):>8}")
    
    # 4. Look at trades where price drops — potential dips to exploit
    print(f"\n--- Price drops after trades (mid change from trade tick to next) ---")
    drops = []
    rises = []
    for t in pepper_trades:
        ts = t['timestamp']
        if ts not in ts_to_idx:
            continue
        idx = ts_to_idx[ts]
        if idx + 1 >= len(timestamps):
            continue
        
        cur_ts = timestamps[idx]
        next_ts = timestamps[idx + 1]
        if cur_ts in prices and next_ts in prices:
            if prices[cur_ts]['mid'] is not None and prices[next_ts]['mid'] is not None:
                change = prices[next_ts]['mid'] - prices[cur_ts]['mid']
                if change < 0:
                    drops.append((t, change))
                else:
                    rises.append((t, change))
    
    print(f"  Ticks with drops after trade: {len(drops)}/{len(drops)+len(rises)}")
    if drops:
        drop_vals = [d[1] for d in drops]
        print(f"  Drop magnitudes: mean={statistics.mean(drop_vals):.1f}, "
              f"median={statistics.median(drop_vals):.1f}, max={min(drop_vals):.1f}")
    
    # 5. Trade price vs current book — are trades happening at spreads we could post at?
    print(f"\n--- Trade price relative to book ---")
    above_ask = 0
    at_ask = 0
    below_ask = 0
    at_bid = 0
    below_bid = 0
    between = 0
    
    for t in pepper_trades:
        ts = t['timestamp']
        if ts in prices and prices[ts]['bid1'] is not None and prices[ts]['ask1'] is not None:
            bid1 = prices[ts]['bid1']
            ask1 = prices[ts]['ask1']
            p = t['price']
            if p > ask1:
                above_ask += 1
            elif p == ask1:
                at_ask += 1
            elif p > bid1:
                between += 1
            elif p == bid1:
                at_bid += 1
            else:
                below_bid += 1
    
    total_classified = above_ask + at_ask + between + at_bid + below_bid
    print(f"  Above ask: {above_ask} ({above_ask/total_classified*100:.1f}%)")
    print(f"  At ask:    {at_ask} ({at_ask/total_classified*100:.1f}%)")
    print(f"  Between:   {between} ({between/total_classified*100:.1f}%)")
    print(f"  At bid:    {at_bid} ({at_bid/total_classified*100:.1f}%)")
    print(f"  Below bid: {below_bid} ({below_bid/total_classified*100:.1f}%)")
    
    # 6. Key question: conditional on a large trade (high qty), does price mean-revert?
    print(f"\n--- Large trade analysis (qty >= 10) ---")
    large_trades = [t for t in pepper_trades if t['quantity'] >= 10]
    print(f"  Large trades: {len(large_trades)}")
    
    if large_trades:
        for h in [1, 2, 3, 5, 10]:
            pnls = []
            for t in large_trades:
                ts = t['timestamp']
                if ts not in ts_to_idx:
                    continue
                idx = ts_to_idx[ts]
                if idx + h >= len(timestamps):
                    continue
                future_ts = timestamps[idx + h]
                if prices[ts]['mid'] is not None and prices[future_ts]['mid'] is not None:
                    change = prices[future_ts]['mid'] - prices[ts]['mid']
                    pnls.append(change)
            if pnls:
                print(f"  h={h}: mid_change mean={statistics.mean(pnls):>7.2f}, "
                      f"median={statistics.median(pnls):>7.2f}, std={statistics.stdev(pnls):>7.2f}")
    
    # 7. Spread widening events — when spread is abnormally wide, is there opportunity?
    print(f"\n--- Wide spread analysis (spread > 20) ---")
    all_spreads = []
    for ts in timestamps:
        if prices[ts]['bid1'] is not None and prices[ts]['ask1'] is not None:
            all_spreads.append((ts, prices[ts]['ask1'] - prices[ts]['bid1']))
    
    if all_spreads:
        spread_vals = [s[1] for s in all_spreads]
        p75 = sorted(spread_vals)[int(len(spread_vals)*0.75)]
        p90 = sorted(spread_vals)[int(len(spread_vals)*0.90)]
        p95 = sorted(spread_vals)[int(len(spread_vals)*0.95)]
        print(f"  Spread percentiles: p75={p75:.0f}, p90={p90:.0f}, p95={p95:.0f}")
        
        wide_spreads = [(ts, s) for ts, s in all_spreads if s >= 20]
        print(f"  Ticks with spread >= 20: {len(wide_spreads)} ({len(wide_spreads)/len(all_spreads)*100:.1f}%)")
        
        # For wide spread ticks, what happens to spread and mid over next few ticks?
        if wide_spreads:
            for h in [1, 2, 3, 5]:
                contractions = []
                for ts, s in wide_spreads:
                    if ts not in ts_to_idx:
                        continue
                    idx = ts_to_idx[ts]
                    if idx + h >= len(timestamps):
                        continue
                    future_ts = timestamps[idx + h]
                    if prices[future_ts]['bid1'] is not None and prices[future_ts]['ask1'] is not None:
                        future_spread = prices[future_ts]['ask1'] - prices[future_ts]['bid1']
                        contractions.append(s - future_spread)
                if contractions:
                    print(f"  h={h}: spread contracts by mean={statistics.mean(contractions):>6.1f}, "
                          f"median={statistics.median(contractions):>6.1f}")
    
    # 8. Best theoretical MM P&L: post at best_bid+1/best_ask-1, immediate fill both sides
    print(f"\n--- Theoretical MM at best_bid+1 / best_ask-1 ---")
    mm_pnls = []
    for i in range(len(timestamps) - 1):
        ts = timestamps[i]
        next_ts = timestamps[i + 1]
        p = prices[ts]
        pn = prices[next_ts]
        if p['bid1'] is not None and p['ask1'] is not None:
            if pn['bid1'] is not None and pn['ask1'] is not None:
                buy_price = p['bid1'] + 1
                sell_price = p['ask1'] - 1
                if sell_price > buy_price:
                    # If we buy at bid+1 and sell at ask-1 immediately (1 tick round trip)
                    # But in reality we can only do one side per tick with passive fills
                    # Assume we sell at ask-1 this tick, rebuy at bid+1 next tick
                    rebuy_next = pn['bid1'] + 1
                    profit_sell_rebuy = sell_price - rebuy_next
                    mm_pnls.append(profit_sell_rebuy)
    
    if mm_pnls:
        win_pct = sum(1 for p in mm_pnls if p > 0) / len(mm_pnls) * 100
        print(f"  Sell@ask-1 then rebuy@bid+1 next tick: "
              f"mean={statistics.mean(mm_pnls):.2f}, median={statistics.median(mm_pnls):.2f}, "
              f"win={win_pct:.1f}%")
        print(f"  Total if 1 lot every tick: {sum(mm_pnls):.0f}")
    
    # 9. What if we only MM when spread is wide?
    print(f"\n--- Conditional MM: only when spread > threshold ---")
    for spread_thr in [14, 16, 18, 20, 25]:
        profits = []
        count = 0
        for i in range(len(timestamps) - 1):
            ts = timestamps[i]
            next_ts = timestamps[i + 1]
            p = prices[ts]
            pn = prices[next_ts]
            if p['bid1'] is None or p['ask1'] is None:
                continue
            if pn['bid1'] is None or pn['ask1'] is None:
                continue
            spread = p['ask1'] - p['bid1']
            if spread >= spread_thr:
                sell_price = p['ask1'] - 1
                rebuy_next = pn['ask1']  # worst case: have to market buy next tick
                profit = sell_price - rebuy_next
                profits.append(profit)
                count += 1
        
        if profits:
            win_pct = sum(1 for p in profits if p > 0) / len(profits) * 100
            print(f"  spread>={spread_thr}: n={count}, mean={statistics.mean(profits):>7.2f}, "
                  f"median={statistics.median(profits):>7.2f}, win={win_pct:.1f}%, "
                  f"total={sum(profits):.0f}")


# Process all days
for rnd in [1, 2]:
    for day_suffix in (['-2', '-1', '0'] if rnd == 1 else ['-1', '0', '1']):
        prices_file = f"data/round{rnd}/prices_round_{rnd}_day_{day_suffix}.csv"
        trades_file = f"data/round{rnd}/trades_round_{rnd}_day_{day_suffix}.csv"
        label = f"Round {rnd}, Day {day_suffix}"
        
        pp = os.path.join(os.path.dirname(__file__), '..', prices_file)
        tp = os.path.join(os.path.dirname(__file__), '..', trades_file)
        analyze_day(pp, tp, label)
