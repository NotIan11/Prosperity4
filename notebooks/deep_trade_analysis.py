#!/usr/bin/env python3
"""Deep dive into trades data looking for unexploited signals."""
import csv, os, statistics
from collections import defaultdict, Counter

DATA = os.path.join(os.path.dirname(__file__), '..', 'data')

def load_prices(path):
    prices = {}
    with open(path) as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            ts = int(row['timestamp'])
            prod = row['product']
            if prod not in prices:
                prices[prod] = {}
            prices[prod][ts] = {
                'bid1': float(row['bid_price_1']) if row['bid_price_1'] else None,
                'bid_vol1': int(row['bid_volume_1']) if row['bid_volume_1'] else 0,
                'bid2': float(row['bid_price_2']) if row['bid_price_2'] else None,
                'bid_vol2': int(row['bid_volume_2']) if row['bid_volume_2'] else 0,
                'bid3': float(row['bid_price_3']) if row['bid_price_3'] else None,
                'bid_vol3': int(row['bid_volume_3']) if row['bid_volume_3'] else 0,
                'ask1': float(row['ask_price_1']) if row['ask_price_1'] else None,
                'ask_vol1': int(row['ask_volume_1']) if row['ask_volume_1'] else 0,
                'ask2': float(row['ask_price_2']) if row['ask_price_2'] else None,
                'ask_vol2': int(row['ask_volume_2']) if row['ask_volume_2'] else 0,
                'ask3': float(row['ask_price_3']) if row['ask_price_3'] else None,
                'ask_vol3': int(row['ask_volume_3']) if row['ask_volume_3'] else 0,
                'mid': float(row['mid_price']) if row['mid_price'] else None,
            }
    return prices

def load_trades(path):
    trades = []
    with open(path) as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            trades.append({
                'timestamp': int(row['timestamp']),
                'buyer': row['buyer'],
                'seller': row['seller'],
                'symbol': row['symbol'],
                'price': float(row['price']),
                'quantity': int(row['quantity']),
            })
    return trades

def analyze_day(prices_path, trades_path, label):
    prices = load_prices(prices_path)
    trades = load_trades(trades_path)
    
    print(f"\n{'='*80}")
    print(f"  {label}")
    print(f"{'='*80}")
    
    pep_trades = [t for t in trades if t['symbol'] == 'INTARIAN_PEPPER_ROOT']
    osm_trades = [t for t in trades if t['symbol'] == 'ASH_COATED_OSMIUM']
    
    pep_prices = prices.get('INTARIAN_PEPPER_ROOT', {})
    osm_prices = prices.get('ASH_COATED_OSMIUM', {})
    pep_ts = sorted(pep_prices.keys())
    osm_ts = sorted(osm_prices.keys())
    
    # ---- 1. BUYER/SELLER IDENTITY ----
    print("\n--- Buyer/Seller Identity ---")
    for name, tlist in [("Pepper", pep_trades), ("Osmium", osm_trades)]:
        buyers = Counter(t['buyer'] for t in tlist)
        sellers = Counter(t['seller'] for t in tlist)
        print(f"  {name} buyers:  {buyers.most_common(10)}")
        print(f"  {name} sellers: {sellers.most_common(10)}")
    
    # ---- 2. TRADE TIMING: inter-trade intervals ----
    print("\n--- Trade Timing (inter-trade interval in ticks) ---")
    for name, tlist in [("Pepper", pep_trades), ("Osmium", osm_trades)]:
        if len(tlist) < 2:
            continue
        intervals = [tlist[i+1]['timestamp'] - tlist[i]['timestamp'] for i in range(len(tlist)-1)]
        intervals = [x for x in intervals if x > 0]
        if intervals:
            print(f"  {name}: mean={statistics.mean(intervals):.0f}, median={statistics.median(intervals):.0f}, "
                  f"min={min(intervals)}, max={max(intervals)}, std={statistics.stdev(intervals):.0f}")
    
    # ---- 3. TRADE CLUSTERING: multiple trades at same timestamp ----
    print("\n--- Trade Clustering (same-tick trades) ---")
    for name, tlist in [("Pepper", pep_trades), ("Osmium", osm_trades)]:
        by_ts = defaultdict(list)
        for t in tlist:
            by_ts[t['timestamp']].append(t)
        multi = {ts: tt for ts, tt in by_ts.items() if len(tt) > 1}
        print(f"  {name}: {len(multi)} timestamps with multiple trades (of {len(by_ts)} total)")
        if multi:
            sizes = [len(tt) for tt in multi.values()]
            print(f"    cluster sizes: {Counter(sizes).most_common()}")
    
    # ---- 4. CROSS-PRODUCT SIGNAL: does osmium trade predict pepper? ----
    print("\n--- Cross-Product Signal (osmium trade → pepper direction) ---")
    if osm_trades and pep_prices:
        pep_ts_set = set(pep_ts)
        pep_ts_idx = {ts: i for i, ts in enumerate(pep_ts)}
        
        for h in [1, 2, 5, 10]:
            pep_changes = []
            for t in osm_trades:
                ts = t['timestamp']
                # Find nearest pepper tick
                if ts in pep_ts_idx:
                    idx = pep_ts_idx[ts]
                    if idx + h < len(pep_ts):
                        cur = pep_prices[pep_ts[idx]]['mid']
                        fut = pep_prices[pep_ts[idx + h]]['mid']
                        if cur is not None and fut is not None:
                            pep_changes.append(fut - cur)
            if pep_changes:
                print(f"  h={h}: pepper mid change after osmium trade: "
                      f"mean={statistics.mean(pep_changes):.3f}, "
                      f"std={statistics.stdev(pep_changes):.2f}, n={len(pep_changes)}")
    
    # ---- 5. TRADE PRICE vs BOOK DEPTH: trades consuming L2/L3 ----
    print("\n--- Trades Consuming Beyond L1 ---")
    for name, tlist, pdict, ts_list in [
        ("Pepper", pep_trades, pep_prices, pep_ts),
        ("Osmium", osm_trades, osm_prices, osm_ts)
    ]:
        at_l1 = 0
        beyond_l1 = 0
        for t in tlist:
            ts = t['timestamp']
            if ts not in pdict:
                continue
            p = pdict[ts]
            price = t['price']
            if p['ask1'] is not None and price > p['ask1']:
                beyond_l1 += 1
            elif p['bid1'] is not None and price < p['bid1']:
                beyond_l1 += 1
            else:
                at_l1 += 1
        print(f"  {name}: at_L1={at_l1}, beyond_L1={beyond_l1}")
    
    # ---- 6. BOOK IMBALANCE as signal ----
    print("\n--- Book Imbalance Signal ---")
    for name, pdict, ts_list in [
        ("Pepper", pep_prices, pep_ts),
        ("Osmium", osm_prices, osm_ts)
    ]:
        if len(ts_list) < 2:
            continue
        imbal_buckets = defaultdict(list)  # bucket -> next-tick mid change
        for i in range(len(ts_list) - 1):
            ts = ts_list[i]
            next_ts = ts_list[i + 1]
            p = pdict[ts]
            pn = pdict[next_ts]
            if p['bid_vol1'] and p['ask_vol1'] and p['mid'] is not None and pn['mid'] is not None:
                total = p['bid_vol1'] + p['ask_vol1']
                imbal = (p['bid_vol1'] - p['ask_vol1']) / total  # +1 = all bids, -1 = all asks
                change = pn['mid'] - p['mid']
                if imbal > 0.3:
                    imbal_buckets['bid_heavy'].append(change)
                elif imbal < -0.3:
                    imbal_buckets['ask_heavy'].append(change)
                else:
                    imbal_buckets['balanced'].append(change)
        
        for bucket in ['bid_heavy', 'balanced', 'ask_heavy']:
            vals = imbal_buckets.get(bucket, [])
            if vals:
                print(f"  {name} {bucket}: mean_change={statistics.mean(vals):.4f}, "
                      f"std={statistics.stdev(vals):.3f}, n={len(vals)}")
    
    # ---- 7. VOLUME-WEIGHTED PRICE vs MID ----
    print("\n--- VWAP vs Mid (per-tick) ---")
    for name, tlist, pdict in [
        ("Pepper", pep_trades, pep_prices),
        ("Osmium", osm_trades, osm_prices)
    ]:
        by_ts = defaultdict(list)
        for t in tlist:
            by_ts[t['timestamp']].append(t)
        
        vwap_vs_mid = []
        for ts, tt in by_ts.items():
            if ts in pdict and pdict[ts]['mid'] is not None:
                total_val = sum(t['price'] * t['quantity'] for t in tt)
                total_qty = sum(t['quantity'] for t in tt)
                vwap = total_val / total_qty
                diff = vwap - pdict[ts]['mid']
                vwap_vs_mid.append(diff)
        
        if vwap_vs_mid:
            print(f"  {name}: VWAP-mid mean={statistics.mean(vwap_vs_mid):.2f}, "
                  f"std={statistics.stdev(vwap_vs_mid):.2f}")
    
    # ---- 8. TIME-OF-DAY PATTERN ----
    print("\n--- Time-of-Day PnL (pepper mid change per 100K tick bucket) ---")
    if pep_ts:
        bucket_size = 100000
        bucket_pnl = defaultdict(float)
        bucket_count = defaultdict(int)
        for i in range(len(pep_ts) - 1):
            ts = pep_ts[i]
            next_ts = pep_ts[i + 1]
            p = pep_prices[ts]
            pn = pep_prices[next_ts]
            if p['mid'] is not None and pn['mid'] is not None:
                bucket = ts // bucket_size
                bucket_pnl[bucket] += pn['mid'] - p['mid']
                bucket_count[bucket] += 1
        
        for b in sorted(bucket_pnl.keys()):
            avg = bucket_pnl[b] / bucket_count[b] if bucket_count[b] > 0 else 0
            print(f"  {b*bucket_size:>8}-{(b+1)*bucket_size:>8}: "
                  f"total_drift={bucket_pnl[b]:>8.1f}, ticks={bucket_count[b]:>5}, "
                  f"avg/tick={avg:.4f}")
    
    # ---- 9. TRADE-DRIVEN MOMENTUM (do trades predict short-term direction?) ----
    print("\n--- Trade as Momentum Signal (buy at ask → price up?) ---")
    for name, tlist, pdict, ts_list in [
        ("Pepper", pep_trades, pep_prices, pep_ts),
        ("Osmium", osm_trades, osm_prices, osm_ts)
    ]:
        ts_idx = {ts: i for i, ts in enumerate(ts_list)}
        buy_trades = []  # trades at ask (buyer-initiated)
        sell_trades = []  # trades at bid (seller-initiated)
        
        for t in tlist:
            ts = t['timestamp']
            if ts not in pdict:
                continue
            p = pdict[ts]
            if p['ask1'] is not None and t['price'] >= p['ask1']:
                buy_trades.append(t)
            elif p['bid1'] is not None and t['price'] <= p['bid1']:
                sell_trades.append(t)
        
        for side, side_trades in [("buyer-init", buy_trades), ("seller-init", sell_trades)]:
            for h in [1, 3, 5, 10]:
                changes = []
                for t in side_trades:
                    ts = t['timestamp']
                    if ts not in ts_idx:
                        continue
                    idx = ts_idx[ts]
                    if idx + h < len(ts_list):
                        cur_mid = pdict[ts_list[idx]]['mid']
                        fut_mid = pdict[ts_list[idx + h]]['mid']
                        if cur_mid is not None and fut_mid is not None:
                            changes.append(fut_mid - cur_mid)
                if changes:
                    print(f"  {name} {side} h={h}: "
                          f"mean={statistics.mean(changes):>7.3f}, "
                          f"win_up={sum(1 for c in changes if c>0)/len(changes)*100:>5.1f}%, "
                          f"n={len(changes)}")
    
    # ---- 10. OSMIUM: does book depth predict price? ----
    print("\n--- Osmium Book Depth Signal ---")
    if osm_ts:
        depth_changes = defaultdict(list)
        for i in range(len(osm_ts) - 5):
            ts = osm_ts[i]
            fut_ts = osm_ts[i + 5]
            p = osm_prices[ts]
            pf = osm_prices[fut_ts]
            if p['mid'] is None or pf['mid'] is None:
                continue
            
            # Total bid/ask volume
            bid_vol = sum(v for v in [p['bid_vol1'], p['bid_vol2'], p['bid_vol3']] if v)
            ask_vol = sum(v for v in [p['ask_vol1'], p['ask_vol2'], p['ask_vol3']] if v)
            total = bid_vol + ask_vol
            if total == 0:
                continue
            
            imbal = (bid_vol - ask_vol) / total
            change = pf['mid'] - p['mid']
            
            if imbal > 0.5:
                depth_changes['strong_bid'].append(change)
            elif imbal > 0.2:
                depth_changes['mild_bid'].append(change)
            elif imbal < -0.5:
                depth_changes['strong_ask'].append(change)
            elif imbal < -0.2:
                depth_changes['mild_ask'].append(change)
            else:
                depth_changes['neutral'].append(change)
        
        for bucket in ['strong_bid', 'mild_bid', 'neutral', 'mild_ask', 'strong_ask']:
            vals = depth_changes.get(bucket, [])
            if vals:
                print(f"  {bucket}: h=5 mean={statistics.mean(vals):>7.3f}, "
                      f"std={statistics.stdev(vals):>6.2f}, n={len(vals)}")

    # ---- 11. PEPPER: spread changes predict next-tick direction? ----
    print("\n--- Pepper Spread Change as Signal ---")
    if pep_ts and len(pep_ts) > 2:
        for h in [1, 3]:
            widen_changes = []
            narrow_changes = []
            for i in range(1, len(pep_ts) - h):
                prev_ts = pep_ts[i - 1]
                ts = pep_ts[i]
                fut_ts = pep_ts[i + h]
                pp = pep_prices[prev_ts]
                pc = pep_prices[ts]
                pf = pep_prices[fut_ts]
                
                if pp['bid1'] is None or pp['ask1'] is None or pc['bid1'] is None or pc['ask1'] is None:
                    continue
                if pf['mid'] is None or pc['mid'] is None:
                    continue
                
                prev_spread = pp['ask1'] - pp['bid1']
                cur_spread = pc['ask1'] - pc['bid1']
                mid_change = pf['mid'] - pc['mid']
                
                if cur_spread > prev_spread + 1:
                    widen_changes.append(mid_change)
                elif cur_spread < prev_spread - 1:
                    narrow_changes.append(mid_change)
            
            if widen_changes:
                print(f"  h={h} after spread WIDEN:  mean={statistics.mean(widen_changes):>7.3f}, n={len(widen_changes)}")
            if narrow_changes:
                print(f"  h={h} after spread NARROW: mean={statistics.mean(narrow_changes):>7.3f}, n={len(narrow_changes)}")


# Process all days
for rnd in [1, 2]:
    for day_suffix in (['-2', '-1', '0'] if rnd == 1 else ['-1', '0', '1']):
        prices_file = os.path.join(DATA, f'round{rnd}', f'prices_round_{rnd}_day_{day_suffix}.csv')
        trades_file = os.path.join(DATA, f'round{rnd}', f'trades_round_{rnd}_day_{day_suffix}.csv')
        analyze_day(prices_file, trades_file, f"Round {rnd}, Day {day_suffix}")
