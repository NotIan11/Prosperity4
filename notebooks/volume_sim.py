#!/usr/bin/env python3
"""Simulate our strategies against the CSV data with 25% more market volume.

The rust backtester is a black box, so we replicate the key mechanics:
- Osmium: wall-anchored passive quoting + overbid/underbid + AC-graded MR taking
- Pepper: aggressive buy 10/tick + conditional sell at spread≥16

We simulate two scenarios:
  A) baseline: original volumes (sanity-check against real backtester)
  B) +25% vol: all order book volumes scaled up by 1.25

Fill model (matching the rust backtester's simplified model):
- Aggressive orders: fill immediately at the limit price against available volume
- Passive orders: fill if the market trades through your price next tick
  (approximated by: if next-tick best_bid >= your_sell_price, sell fills; 
   if next-tick best_ask <= your_buy_price, buy fills)
"""
import csv, os, math
from collections import defaultdict

DATA = os.path.join(os.path.dirname(__file__), '..', 'data')
FAIR_VALUE = 10000

def load_book(path):
    """Load order book snapshots per product per timestamp."""
    books = defaultdict(dict)
    with open(path) as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            prod = row['product']
            ts = int(row['timestamp'])
            def val(k): return float(row[k]) if row.get(k) and row[k] else None
            def vol(k): return int(row[k]) if row.get(k) and row[k] else 0
            books[prod][ts] = {
                'bids': [(val(f'bid_price_{i}'), vol(f'bid_volume_{i}')) 
                         for i in [1,2,3] if val(f'bid_price_{i}') is not None],
                'asks': [(val(f'ask_price_{i}'), vol(f'ask_volume_{i}'))
                         for i in [1,2,3] if val(f'ask_price_{i}') is not None],
            }
    return books


def scale_volumes(book, factor):
    """Return a new book with volumes scaled by factor."""
    new_book = {}
    for prod, ticks in book.items():
        new_book[prod] = {}
        for ts, ob in ticks.items():
            new_book[prod][ts] = {
                'bids': [(p, max(1, int(round(v * factor)))) for p, v in ob['bids']],
                'asks': [(p, max(1, int(round(v * factor)))) for p, v in ob['asks']],
            }
    return new_book


def sim_osmium(timestamps, book_data, pos_limit=50):
    """Simulate OsmiumStrategy. Returns total PnL."""
    pos = 0
    cash = 0.0
    prev_mid = None
    MR_TAKE_THR = 2.5
    MR_BUY_ADJ = 4.5
    MR_SELL_ADJ = -5.5
    
    # For passive fill tracking
    pending_buy = None   # (price, qty)
    pending_sell = None  # (price, qty)
    
    for i, ts in enumerate(timestamps):
        ob = book_data.get(ts)
        if not ob or not ob['bids'] or not ob['asks']:
            continue
        
        bids = sorted(ob['bids'], key=lambda x: -x[0])  # highest first
        asks = sorted(ob['asks'], key=lambda x: x[0])    # lowest first
        
        best_bid = bids[0][0]
        best_ask = asks[0][0]
        bid_wall = bids[-1][0]
        ask_wall = asks[-1][0]
        wall_mid = (bid_wall + ask_wall) / 2.0
        mid = (best_bid + best_ask) / 2.0
        fd = wall_mid - FAIR_VALUE
        
        buys = 0
        sells = 0
        
        # --- Fill pending passive orders from last tick ---
        if pending_buy is not None:
            bp, bq = pending_buy
            # Fill if market ask <= our buy price (someone willing to sell to us)
            if best_ask <= bp:
                fill_qty = min(bq, pos_limit - pos)
                if fill_qty > 0:
                    cash -= bp * fill_qty
                    pos += fill_qty
            pending_buy = None
        
        if pending_sell is not None:
            sp, sq = pending_sell
            # Fill if market bid >= our sell price (someone willing to buy from us)
            if best_bid >= sp:
                fill_qty = min(sq, pos_limit + pos)
                if fill_qty > 0:
                    cash += sp * fill_qty
                    pos -= fill_qty
            pending_sell = None
        
        # --- AC signal ---
        prev_up = False
        prev_down = False
        if prev_mid is not None:
            change = mid - prev_mid
            prev_up = change > 0
            prev_down = change < 0
        prev_mid = mid
        
        # --- MR taking ---
        if fd < -MR_TAKE_THR:
            buy_adj = MR_BUY_ADJ if prev_down else MR_BUY_ADJ * 0.8
        else:
            buy_adj = 0
        if fd > MR_TAKE_THR:
            sell_adj = MR_SELL_ADJ if prev_up else MR_SELL_ADJ * 0.8
        else:
            sell_adj = 0
        
        for ap, av in asks:
            if ap > wall_mid - 0.5 + buy_adj:
                break
            remaining = pos_limit - pos - buys
            if remaining <= 0:
                break
            qty = min(av, remaining)
            if qty > 0:
                cash -= ap * qty
                buys += qty
        
        for bp, bv in bids:
            if bp < wall_mid + 0.5 + sell_adj:
                break
            remaining = pos_limit + pos - sells
            if remaining <= 0:
                break
            qty = min(bv, remaining)
            if qty > 0:
                cash += bp * qty
                sells += qty
        
        pos += buys - sells
        
        # --- Passive quoting ---
        buy_price = int(bid_wall) + 1
        sell_price = int(ask_wall) - 1
        if buy_price >= wall_mid:
            buy_price = int(wall_mid) - 1
        if sell_price <= wall_mid:
            sell_price = int(wall_mid) + 1
        
        # Overbid
        for bp, _ in bids:
            overbid = int(bp) + 1
            if overbid < wall_mid and overbid > buy_price:
                buy_price = overbid
                break
            if bp < wall_mid:
                break
        
        # Underbid
        for ap, _ in asks:
            underbid = int(ap) - 1
            if underbid > wall_mid and underbid < sell_price:
                sell_price = underbid
                break
            if ap > wall_mid:
                break
        
        buy_cap = pos_limit - pos
        sell_cap = pos_limit + pos
        if buy_cap > 0:
            pending_buy = (buy_price, buy_cap)
        if sell_cap > 0:
            pending_sell = (sell_price, sell_cap)
    
    # Mark to market at last mid
    if prev_mid is not None:
        cash += pos * prev_mid
    
    return cash


def sim_pepper(timestamps, book_data, pos_limit=80):
    """Simulate PepperStrategy. Returns total PnL."""
    pos = 0
    cash = 0.0
    MAX_PER_TICK = 10
    SELL_SPREAD_THR = 16
    
    # For passive sell fill tracking
    pending_sell = None
    
    for i, ts in enumerate(timestamps):
        ob = book_data.get(ts)
        if not ob or not ob['asks']:
            continue
        
        asks = sorted(ob['asks'], key=lambda x: x[0])
        bids = sorted(ob['bids'], key=lambda x: -x[0]) if ob['bids'] else []
        
        best_ask = asks[0][0]
        best_bid = bids[0][0] if bids else None
        
        buys = 0
        
        # --- Fill pending passive sell from last tick ---
        if pending_sell is not None and best_bid is not None:
            sp, sq = pending_sell
            if best_bid >= sp:
                fill_qty = min(sq, pos)
                if fill_qty > 0:
                    cash += sp * fill_qty
                    pos -= fill_qty
            pending_sell = None
        
        # --- Aggressive buy (capped at 10/tick) ---
        tick_cap = MAX_PER_TICK
        for ap, av in asks:
            remaining = min(pos_limit - pos - buys, tick_cap - buys)
            if remaining <= 0:
                break
            qty = min(av, remaining)
            if qty > 0:
                cash -= ap * qty
                buys += qty
        
        pos += buys
        
        # --- Conditional passive sell ---
        if SELL_SPREAD_THR > 0 and best_bid is not None:
            spread = best_ask - best_bid
            if spread >= SELL_SPREAD_THR:
                sell_price = int(best_ask) - 1
                sell_qty = min(10, pos)
                if sell_qty > 0:
                    pending_sell = (sell_price, sell_qty)
    
    # Mark to market at last mid
    if pending_sell:
        pass  # unfilled, ignore
    last_ts = timestamps[-1]
    ob = book_data.get(last_ts)
    if ob and ob['bids'] and ob['asks']:
        last_mid = (ob['bids'][0][0] + ob['asks'][0][0]) / 2.0
        cash += pos * last_mid
    
    return cash


def run_scenario(label, books):
    results = {}
    for rnd in [1, 2]:
        for day_suffix in (['-2', '-1', '0'] if rnd == 1 else ['-1', '0', '1']):
            key = f"R{rnd}D{day_suffix}"
            prices_file = os.path.join(DATA, f'round{rnd}', f'prices_round_{rnd}_day_{day_suffix}.csv')
            raw = load_book(prices_file)
            
            if books == 'raw':
                book = raw
            else:
                book = scale_volumes(raw, books)
            
            osm_data = book.get('ASH_COATED_OSMIUM', {})
            pep_data = book.get('INTARIAN_PEPPER_ROOT', {})
            osm_ts = sorted(osm_data.keys())
            pep_ts = sorted(pep_data.keys())
            
            osm_pnl = sim_osmium(osm_ts, osm_data)
            pep_pnl = sim_pepper(pep_ts, pep_data)
            
            results[key] = (osm_pnl, pep_pnl)
    
    r1_osm = sum(results[k][0] for k in results if k.startswith('R1'))
    r1_pep = sum(results[k][1] for k in results if k.startswith('R1'))
    r2_osm = sum(results[k][0] for k in results if k.startswith('R2'))
    r2_pep = sum(results[k][1] for k in results if k.startswith('R2'))
    
    print(f"\n{'='*70}")
    print(f"  {label}")
    print(f"{'='*70}")
    print(f"{'Day':<10} {'Osmium':>12} {'Pepper':>12} {'Total':>12}")
    print(f"{'-'*46}")
    for key in sorted(results.keys()):
        o, p = results[key]
        print(f"  {key:<8} {o:>12,.0f} {p:>12,.0f} {o+p:>12,.0f}")
    print(f"{'-'*46}")
    print(f"  {'R1 total':<8} {r1_osm:>12,.0f} {r1_pep:>12,.0f} {r1_osm+r1_pep:>12,.0f}")
    print(f"  {'R2 total':<8} {r2_osm:>12,.0f} {r2_pep:>12,.0f} {r2_osm+r2_pep:>12,.0f}")
    print(f"  {'GRAND':<8} {r1_osm+r2_osm:>12,.0f} {r1_pep+r2_pep:>12,.0f} {r1_osm+r2_osm+r1_pep+r2_pep:>12,.0f}")
    
    return results


# Run both scenarios
baseline = run_scenario("BASELINE (1.00x volume)", 'raw')
scaled = run_scenario("+25% VOLUME (1.25x volume)", 1.25)

# Delta
print(f"\n{'='*70}")
print(f"  DELTA (+25% - baseline)")
print(f"{'='*70}")
print(f"{'Day':<10} {'Osmium':>12} {'Pepper':>12} {'Total':>12}")
print(f"{'-'*46}")
for key in sorted(baseline.keys()):
    do = scaled[key][0] - baseline[key][0]
    dp = scaled[key][1] - baseline[key][1]
    print(f"  {key:<8} {do:>+12,.0f} {dp:>+12,.0f} {do+dp:>+12,.0f}")

# Totals
b_total = sum(v[0]+v[1] for v in baseline.values())
s_total = sum(v[0]+v[1] for v in scaled.values())
b_osm = sum(v[0] for v in baseline.values())
s_osm = sum(v[0] for v in scaled.values())
b_pep = sum(v[1] for v in baseline.values())
s_pep = sum(v[1] for v in scaled.values())
print(f"{'-'*46}")
print(f"  {'TOTAL':<8} {s_osm-b_osm:>+12,.0f} {s_pep-b_pep:>+12,.0f} {s_total-b_total:>+12,.0f}")
print(f"\n  Osmium: {b_osm:,.0f} → {s_osm:,.0f} ({(s_osm-b_osm)/b_osm*100:+.1f}%)")
print(f"  Pepper: {b_pep:,.0f} → {s_pep:,.0f} ({(s_pep-b_pep)/b_pep*100:+.1f}%)")
print(f"  Total:  {b_total:,.0f} → {s_total:,.0f} ({(s_total-b_total)/b_total*100:+.1f}%)")

# Also show 50% and 2x for comparison
for factor, label in [(1.5, "+50%"), (2.0, "2x")]:
    res = run_scenario(f"{label} VOLUME ({factor}x)", factor)
    t = sum(v[0]+v[1] for v in res.values())
    o = sum(v[0] for v in res.values())
    p = sum(v[1] for v in res.values())
    print(f"\n  {label}: Osm={o:,.0f} ({(o-b_osm)/b_osm*100:+.1f}%), "
          f"Pep={p:,.0f} ({(p-b_pep)/b_pep*100:+.1f}%), "
          f"Total={t:,.0f} ({(t-b_total)/b_total*100:+.1f}%)")
