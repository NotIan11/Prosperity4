#!/usr/bin/env python3
"""Pepper micro-structure: look for patterns we can actually exploit.
Focus on actionable things:
1. Does the position of the ask relative to drift predict short-term returns?
2. Are there specific price levels where selling and rebuying is +EV?
3. Can we predict WHEN the next ask level tick happens?
4. Book depth asymmetry as a signal
5. What does the actual fill model look like for passive orders?
"""
import csv, os, statistics
from collections import defaultdict, Counter

DATA = os.path.join(os.path.dirname(__file__), '..', 'data')

def load_prices(path, product):
    prices = {}
    with open(path) as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            if row['product'] != product:
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

for rnd in [1, 2]:
    for day_suffix in (['-2', '-1', '0'] if rnd == 1 else ['-1', '0', '1']):
        path = os.path.join(DATA, f'round{rnd}', f'prices_round_{rnd}_day_{day_suffix}.csv')
        pep = load_prices(path, 'INTARIAN_PEPPER_ROOT')
        osm = load_prices(path, 'ASH_COATED_OSMIUM')
        ts_list = sorted(pep.keys())
        osm_ts = sorted(osm.keys())
        label = f"R{rnd}D{day_suffix}"
        
        print(f"\n{'='*80}")
        print(f"  {label}")
        print(f"{'='*80}")
        
        # 1. Pepper ask levels and volumes
        ask_levels = Counter()
        ask1_vols = []
        total_ask_vols = []
        for ts in ts_list:
            p = pep[ts]
            n = sum(1 for i in [1,2,3] if p[f'ask{i}'] is not None)
            ask_levels[n] += 1
            if p['ask_vol1']:
                ask1_vols.append(p['ask_vol1'])
            tvol = sum(p[f'ask_vol{i}'] for i in [1,2,3])
            total_ask_vols.append(tvol)
        
        print(f"\n  Ask levels: {dict(ask_levels)}")
        if ask1_vols:
            print(f"  Ask1 vol: mean={statistics.mean(ask1_vols):.1f}, "
                  f"common={Counter(ask1_vols).most_common(5)}")
        print(f"  Total ask vol: mean={statistics.mean(total_ask_vols):.1f}, "
              f"p50={sorted(total_ask_vols)[len(total_ask_vols)//2]}")
        
        # 2. When does bid_price_1 tick up? (ie when does floor price increase?)
        bid_jumps = []
        time_between_bid_jumps = []
        last_jump_ts = None
        prev_bid = None
        for ts in ts_list:
            p = pep[ts]
            b = p['bid1']
            if b is None:
                continue
            if prev_bid is not None and b > prev_bid:
                bid_jumps.append((ts, b - prev_bid))
                if last_jump_ts is not None:
                    time_between_bid_jumps.append(ts - last_jump_ts)
                last_jump_ts = ts
            prev_bid = b
        
        if bid_jumps:
            jump_sizes = [j[1] for j in bid_jumps]
            print(f"\n  Bid1 jumps: {len(bid_jumps)}, "
                  f"avg_size={statistics.mean(jump_sizes):.1f}")
        if time_between_bid_jumps:
            print(f"  Time between bid jumps: mean={statistics.mean(time_between_bid_jumps):.0f}, "
                  f"median={statistics.median(time_between_bid_jumps):.0f}")
        
        # 3. Ask price stability: how long does each ask price last?
        ask_durations = []
        prev_ask = None
        streak_start = None
        for ts in ts_list:
            p = pep[ts]
            a = p['ask1']
            if a is None:
                continue
            if prev_ask is not None:
                if a != prev_ask:
                    if streak_start is not None:
                        ask_durations.append(ts - streak_start)
                    streak_start = ts
                elif streak_start is None:
                    streak_start = ts
            else:
                streak_start = ts
            prev_ask = a
        
        if ask_durations:
            print(f"  Ask1 duration at same price: mean={statistics.mean(ask_durations):.0f}, "
                  f"median={statistics.median(ask_durations):.0f}")
        
        # 4. Pepper: is there a pattern in how many ticks we stay at each bid?
        bid_durations = []
        prev_bid_val = None
        streak_start_bid = None
        for ts in ts_list:
            p = pep[ts]
            b = p['bid1']
            if b is None:
                continue
            if prev_bid_val is not None:
                if b != prev_bid_val:
                    if streak_start_bid is not None:
                        bid_durations.append((ts - streak_start_bid) // 100)  # in ticks 
                    streak_start_bid = ts
                elif streak_start_bid is None:
                    streak_start_bid = ts
            else:
                streak_start_bid = ts
            prev_bid_val = b
        
        if bid_durations:
            print(f"  Bid1 duration (ticks) at same price: mean={statistics.mean(bid_durations):.1f}, "
                  f"median={statistics.median(bid_durations)}, "
                  f"common={Counter(bid_durations).most_common(5)}")
        
        # 5. How much do we MISS by buying only 10/tick vs unlimited?
        # => simulate buying 80 at position 0 with limit 10/tick vs 80/tick
        sim_pos_10 = 0
        sim_pos_inf = 0
        sim_pnl_10 = 0.0
        sim_pnl_inf = 0.0
        final_mid = None
        for ts in ts_list:
            p = pep[ts]
            if p['ask1'] is None:
                continue
            final_mid = p['mid']
            
            # Buy 10 per tick
            buy_10 = min(10, 80 - sim_pos_10)
            if buy_10 > 0:
                sim_pnl_10 -= p['ask1'] * buy_10
                sim_pos_10 += buy_10
            
            # Buy unlimited
            buy_inf = 80 - sim_pos_inf
            if buy_inf > 0:
                # Fill from book
                filled = 0
                for i in [1, 2, 3]:
                    if p[f'ask{i}'] is not None and p[f'ask_vol{i}'] > 0:
                        qty = min(p[f'ask_vol{i}'], buy_inf - filled)
                        sim_pnl_inf -= p[f'ask{i}'] * qty
                        filled += qty
                sim_pos_inf += filled
        
        if final_mid:
            sim_pnl_10 += sim_pos_10 * final_mid
            sim_pnl_inf += sim_pos_inf * final_mid
            # How many ticks to fill?
            print(f"\n  Fill simulation: 10/tick fills to 80 in {80/10:.0f} ticks")
            print(f"    PnL@10/tick: ~depends on exact prices")
            print(f"    Position at tick 8: {80}")
        
        # 6. Osmium: check if there's a consistent wall shape pattern
        print(f"\n  Osmium wall structure:")
        wall_shapes = Counter()
        for ts in osm_ts:
            p = osm[ts]
            bids = [(p[f'bid{i}'], p[f'bid_vol{i}']) for i in [1,2,3] if p[f'bid{i}'] is not None]
            asks = [(p[f'ask{i}'], p[f'ask_vol{i}']) for i in [1,2,3] if p[f'ask{i}'] is not None]
            if bids and asks:
                # Classify: is biggest volume at wall (deepest level) or at best?
                if len(bids) >= 2:
                    bid_wall_vol = bids[-1][1]
                    bid_best_vol = bids[0][1]
                    if bid_wall_vol > bid_best_vol * 2:
                        bid_shape = 'wall_heavy'
                    elif bid_best_vol > bid_wall_vol * 2:
                        bid_shape = 'best_heavy'
                    else:
                        bid_shape = 'balanced'
                else:
                    bid_shape = 'single'
                wall_shapes[bid_shape] += 1
        
        print(f"    Bid shapes: {dict(wall_shapes)}")
        
        # 7. Cross-product: osmium price deviation as pepper signal?
        print(f"\n  Osmium deviation vs pepper next-tick return:")
        osm_ts_set = set(osm_ts)
        pep_ts_idx = {ts: i for i, ts in enumerate(ts_list)}
        
        for thr in [3, 5, 7]:
            up_returns = []
            down_returns = []
            for ts in ts_list[:-1]:
                if ts not in osm:
                    continue
                o = osm[ts]
                if o['mid'] is None:
                    continue
                p_idx = pep_ts_idx.get(ts)
                if p_idx is None or p_idx + 1 >= len(ts_list):
                    continue
                pep_ret = pep[ts_list[p_idx + 1]]['mid'] - pep[ts_list[p_idx]]['mid']
                if pep_ret is None:
                    continue
                
                osm_dev = o['mid'] - 10000
                if osm_dev > thr:
                    up_returns.append(pep_ret)
                elif osm_dev < -thr:
                    down_returns.append(pep_ret)
            
            if up_returns:
                print(f"    osm>+{thr}: pepper mean={statistics.mean(up_returns):.4f}, n={len(up_returns)}")
            if down_returns:
                print(f"    osm<-{thr}: pepper mean={statistics.mean(down_returns):.4f}, n={len(down_returns)}")
