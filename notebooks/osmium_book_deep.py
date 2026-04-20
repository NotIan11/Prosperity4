#!/usr/bin/env python3
"""Focused analysis: osmium L1 volume imbalance as a consistent signal.
Looking at ALL 3 book levels and checking if total depth imbalance predicts direction."""
import csv, os, statistics
from collections import defaultdict

DATA = os.path.join(os.path.dirname(__file__), '..', 'data')

def load_osm_prices(path):
    prices = {}
    with open(path) as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            if row['product'] != 'ASH_COATED_OSMIUM':
                continue
            ts = int(row['timestamp'])
            def val(k): return float(row[k]) if row[k] else None
            def vol(k): return int(row[k]) if row[k] else 0
            prices[ts] = {
                'bid1': val('bid_price_1'), 'bid_vol1': vol('bid_volume_1'),
                'bid2': val('bid_price_2'), 'bid_vol2': vol('bid_volume_2'),
                'bid3': val('bid_price_3'), 'bid_vol3': vol('bid_volume_3'),
                'ask1': val('ask_price_1'), 'ask_vol1': vol('ask_volume_1'),
                'ask2': val('ask_price_2'), 'ask_vol2': vol('ask_volume_2'),
                'ask3': val('ask_price_3'), 'ask_vol3': vol('ask_volume_3'),
                'mid': val('mid_price'),
            }
    return prices

print("=" * 90)
print("  OSMIUM: Detailed Book Structure Analysis")
print("=" * 90)

for rnd in [1, 2]:
    for day_suffix in (['-2', '-1', '0'] if rnd == 1 else ['-1', '0', '1']):
        path = os.path.join(DATA, f'round{rnd}', f'prices_round_{rnd}_day_{day_suffix}.csv')
        prices = load_osm_prices(path)
        ts_list = sorted(prices.keys())
        
        label = f"R{rnd}D{day_suffix}"
        
        # How many book levels are typically populated?
        n_levels = defaultdict(int)
        for ts in ts_list:
            p = prices[ts]
            bid_levels = sum(1 for k in ['bid1', 'bid2', 'bid3'] if p[k] is not None)
            ask_levels = sum(1 for k in ['ask1', 'ask2', 'ask3'] if p[k] is not None)
            n_levels[(bid_levels, ask_levels)] += 1
        
        print(f"\n--- {label}: Book Level Counts ---")
        for (bl, al), cnt in sorted(n_levels.items(), key=lambda x: -x[1])[:5]:
            print(f"  ({bl} bids, {al} asks): {cnt} ({cnt/len(ts_list)*100:.1f}%)")
        
        # L1 spread distribution
        spreads = []
        for ts in ts_list:
            p = prices[ts]
            if p['bid1'] is not None and p['ask1'] is not None:
                spreads.append(p['ask1'] - p['bid1'])
        if spreads:
            print(f"  L1 spread: mean={statistics.mean(spreads):.1f}, "
                  f"median={statistics.median(spreads):.0f}, "
                  f"p25={sorted(spreads)[len(spreads)//4]:.0f}, "
                  f"p75={sorted(spreads)[3*len(spreads)//4]:.0f}")
        
        # L1 volume distribution
        bid_vols = [prices[ts]['bid_vol1'] for ts in ts_list if prices[ts]['bid_vol1'] > 0]
        ask_vols = [prices[ts]['ask_vol1'] for ts in ts_list if prices[ts]['ask_vol1'] > 0]
        if bid_vols:
            print(f"  L1 bid vol: mean={statistics.mean(bid_vols):.1f}, vals={sorted(set(bid_vols))[:10]}")
        if ask_vols:
            print(f"  L1 ask vol: mean={statistics.mean(ask_vols):.1f}, vals={sorted(set(ask_vols))[:10]}")
        
        # Wall distance (bid_wall/ask_wall distance from best)
        wall_dists = {'bid': [], 'ask': []}
        for ts in ts_list:
            p = prices[ts]
            if p['bid1'] is not None:
                # Find lowest bid
                bids = [p[f'bid{i}'] for i in [1,2,3] if p[f'bid{i}'] is not None]
                if len(bids) > 1:
                    wall_dists['bid'].append(p['bid1'] - min(bids))
            if p['ask1'] is not None:
                asks = [p[f'ask{i}'] for i in [1,2,3] if p[f'ask{i}'] is not None]
                if len(asks) > 1:
                    wall_dists['ask'].append(max(asks) - p['ask1'])
        
        if wall_dists['bid']:
            print(f"  Bid wall distance: mean={statistics.mean(wall_dists['bid']):.1f}, "
                  f"vals={sorted(set(int(x) for x in wall_dists['bid']))[:10]}")
        if wall_dists['ask']:
            print(f"  Ask wall distance: mean={statistics.mean(wall_dists['ask']):.1f}, "
                  f"vals={sorted(set(int(x) for x in wall_dists['ask']))[:10]}")
        
        # Number of bid/ask levels and which side has more -> predict direction?
        print(f"\n  Level count vs next-tick direction (h=1,5):")
        for h in [1, 5]:
            more_bids = []
            more_asks = []
            equal = []
            for i in range(len(ts_list) - h):
                ts = ts_list[i]
                fut_ts = ts_list[i + h]
                p = prices[ts]
                pf = prices[fut_ts]
                if p['mid'] is None or pf['mid'] is None:
                    continue
                bid_levels = sum(1 for k in ['bid1', 'bid2', 'bid3'] if p[k] is not None)
                ask_levels = sum(1 for k in ['ask1', 'ask2', 'ask3'] if p[k] is not None)
                change = pf['mid'] - p['mid']
                if bid_levels > ask_levels:
                    more_bids.append(change)
                elif ask_levels > bid_levels:
                    more_asks.append(change)
                else:
                    equal.append(change)
            
            for name, vals in [("more_bids", more_bids), ("equal", equal), ("more_asks", more_asks)]:
                if vals:
                    print(f"    h={h} {name}: mean={statistics.mean(vals):>7.3f}, "
                          f"std={statistics.stdev(vals):>6.2f}, n={len(vals)}")

# Now look at something new: price level clustering / round number effects
print("\n" + "=" * 90)
print("  OSMIUM: Price Level Effects")
print("=" * 90)

for rnd in [1, 2]:
    for day_suffix in (['-2', '-1', '0'] if rnd == 1 else ['-1', '0', '1']):
        path = os.path.join(DATA, f'round{rnd}', f'prices_round_{rnd}_day_{day_suffix}.csv')
        prices = load_osm_prices(path)
        ts_list = sorted(prices.keys())
        label = f"R{rnd}D{day_suffix}"
        
        # How often is mid at round numbers?
        round_counts = defaultdict(int)
        for ts in ts_list:
            m = prices[ts]['mid']
            if m is not None:
                dist_to_10k = abs(m - 10000)
                if dist_to_10k <= 1:
                    round_counts['within_1_of_10k'] += 1
                elif dist_to_10k <= 3:
                    round_counts['within_3_of_10k'] += 1
                elif dist_to_10k <= 5:
                    round_counts['within_5_of_10k'] += 1
                else:
                    round_counts['far_from_10k'] += 1
        
        total = sum(round_counts.values())
        print(f"\n  {label}: Mid distance from 10000:")
        for k in ['within_1_of_10k', 'within_3_of_10k', 'within_5_of_10k', 'far_from_10k']:
            print(f"    {k}: {round_counts[k]} ({round_counts[k]/total*100:.1f}%)")
        
        # wall_mid distribution
        wall_mids = []
        for ts in ts_list:
            p = prices[ts]
            bids = [p[f'bid{i}'] for i in [1,2,3] if p[f'bid{i}'] is not None]
            asks = [p[f'ask{i}'] for i in [1,2,3] if p[f'ask{i}'] is not None]
            if bids and asks:
                wall_mids.append((min(bids) + max(asks)) / 2)
        if wall_mids:
            print(f"    wall_mid: mean={statistics.mean(wall_mids):.1f}, "
                  f"std={statistics.stdev(wall_mids):.1f}, "
                  f"min={min(wall_mids):.0f}, max={max(wall_mids):.0f}")
