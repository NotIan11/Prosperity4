import json, pandas as pd, numpy as np, matplotlib.pyplot as plt
from io import StringIO

RUN_ID = '1777182637074'
DAYS = [('day-0', 'Day 0'), ('day+1', 'Day 1'), ('day+2', 'Day 2')]

fig, axes = plt.subplots(3, 1, figsize=(14, 14))
fig.suptitle('Round 3 Backtest — HYDROGEL, VELVETFRUIT & Net PnL per day', fontsize=13, y=0.99)

for (day_tag, day_label), ax in zip(DAYS, axes):
    path = f'runs/backtest-{RUN_ID}-round3-{day_tag}/submission.log'
    with open(path) as f:
        data = json.load(f)
    df = pd.read_csv(StringIO(data['activitiesLog']), sep=';')

    hy = df[df['product'] == 'HYDROGEL_PACK'].sort_values('timestamp').reset_index(drop=True)
    vf = df[df['product'] == 'VELVETFRUIT_EXTRACT'].sort_values('timestamp').reset_index(drop=True)

    t_hy = hy['timestamp'].values
    hy_pnl = hy['profit_and_loss'].values
    hy_mid = hy['mid_price'].values

    t_vf = vf['timestamp'].values
    vf_pnl = vf['profit_and_loss'].values
    vf_mid = vf['mid_price'].values

    # Net PnL aligned on HYDROGEL timestamps
    vf_pnl_aligned = (
        vf.set_index('timestamp')['profit_and_loss']
        .reindex(t_hy)
        .ffill()
        .fillna(0)
        .values
    )
    net_pnl = hy_pnl + vf_pnl_aligned

    # PnL on left axis
    ax.plot(t_hy, hy_pnl, color='#2171b5', lw=1.5, label=f'HYDROGEL PnL (final: {hy_pnl[-1]:+,.0f})')
    ax.plot(t_vf, vf_pnl, color='#238b45', lw=1.5, label=f'VELVETFRUIT PnL (final: {vf_pnl[-1]:+,.0f})')
    ax.plot(t_hy, net_pnl, color='black', lw=1.8, ls='--', label=f'Net PnL (final: {net_pnl[-1]:+,.0f})')
    ax.axhline(0, color='gray', lw=0.7, ls='--')
    ax.set_ylabel('PnL', fontsize=9)
    ax.set_xlabel('Timestamp', fontsize=8)

    # Mid price on right axis (faded)
    ax2 = ax.twinx()
    ax2.plot(t_hy, hy_mid, color='#6baed6', lw=0.8, alpha=0.4, label='HYDROGEL mid')
    ax2.plot(t_vf, vf_mid, color='#74c476', lw=0.8, alpha=0.4, label='VELVETFRUIT mid')
    ax2.set_ylabel('Mid price', fontsize=8, alpha=0.6)
    ax2.tick_params(axis='y', labelcolor='gray', labelsize=7)

    # Trade markers plotted on PnL curve
    hy_pnl_lookup = hy.set_index('timestamp')['profit_and_loss']
    vf_pnl_lookup = vf.set_index('timestamp')['profit_and_loss']

    hy_buys  = [(t['timestamp'], t['price']) for t in data['tradeHistory']
                if t['symbol'] == 'HYDROGEL_PACK' and t['buyer'] == 'SUBMISSION']
    hy_sells = [(t['timestamp'], t['price']) for t in data['tradeHistory']
                if t['symbol'] == 'HYDROGEL_PACK' and t['seller'] == 'SUBMISSION']
    vf_buys  = [(t['timestamp'], t['price']) for t in data['tradeHistory']
                if t['symbol'] == 'VELVETFRUIT_EXTRACT' and t['buyer'] == 'SUBMISSION']
    vf_sells = [(t['timestamp'], t['price']) for t in data['tradeHistory']
                if t['symbol'] == 'VELVETFRUIT_EXTRACT' and t['seller'] == 'SUBMISSION']

    for trades, color, marker, label_pfx, lookup in [
        (hy_buys,  '#2171b5', '^', 'HY',  hy_pnl_lookup),
        (hy_sells, '#2171b5', 'v', 'HY',  hy_pnl_lookup),
        (vf_buys,  '#238b45', '^', 'VF',  vf_pnl_lookup),
        (vf_sells, '#238b45', 'v', 'VF',  vf_pnl_lookup),
    ]:
        if not trades:
            continue
        ts_list = [t for t, _ in trades]
        pnl_vals = [lookup.get(t, np.nan) for t in ts_list]
        side = 'buys' if marker == '^' else 'sells'
        ax.scatter(ts_list, pnl_vals, color=color, marker=marker,
                   s=50, zorder=6, label=f'{label_pfx} {side} ({len(trades)})')

    lines1, lbl1 = ax.get_legend_handles_labels()
    lines2, lbl2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, lbl1 + lbl2, fontsize=7, loc='upper left', ncol=2)
    ax.set_title(
        f'{day_label} — HYDROGEL: {hy_pnl[-1]:+,.0f}  |  VELVETFRUIT: {vf_pnl[-1]:+,.0f}  |  Net: {net_pnl[-1]:+,.0f}',
        fontsize=9
    )
    ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('notebooks/r3_plots/backtest_pnl_per_day.png', dpi=150, bbox_inches='tight')
print('Saved notebooks/r3_plots/backtest_pnl_per_day.png')
