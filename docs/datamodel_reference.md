# Datamodel Reference

## Trader Signature

```python
class Trader:
    def run(self, state: TradingState) -> tuple[dict[str, list[Order]], int, str]:
        # returns (orders, conversions, traderData)
```

## TradingState

| Field | Type | Notes |
|---|---|---|
| `traderData` | `str` | Serialized state from previous tick (you write this) |
| `timestamp` | `int` | Current timestamp (100 per tick) |
| `listings` | `Dict[Symbol, Listing]` | All tradeable products |
| `order_depths` | `Dict[Symbol, OrderDepth]` | Current LOB per product |
| `own_trades` | `Dict[Symbol, List[Trade]]` | Your fills from last tick |
| `market_trades` | `Dict[Symbol, List[Trade]]` | All other trades last tick |
| `position` | `Dict[Product, Position]` | Your current net position |
| `observations` | `Observation` | Market observations (conversion products etc.) |

## OrderDepth

```python
order_depth.buy_orders   # Dict[price -> volume]  (positive volume = buyers)
order_depth.sell_orders  # Dict[price -> volume]  (negative volume = sellers)

best_bid = max(order_depth.buy_orders.keys())
best_ask = min(order_depth.sell_orders.keys())
```

## Order

```python
Order(symbol, price, quantity)
# quantity > 0 = buy, quantity < 0 = sell
```

## Position Limits (R1)

| Product | Limit |
|---|---|
| `ASH_COATED_OSMIUM` | ±80 |
| `INTARIAN_PEPPER_ROOT` | ±80 |

## traderData Pattern

Use `json.dumps` / `json.loads` to persist state across ticks:

```python
import json

# Save
trader_data = json.dumps({"price_history": self._history})

# Load
state_data = json.loads(state.traderData) if state.traderData else {}
self._history = state_data.get("price_history", [])
```

## Key Rules

- Orders submitted each tick are filled at the next market-clearing step.
- You cannot partially fill — if your order price doesn't match, it expires.
- Position limits are hard-enforced by the simulator; breaching them rejects orders.
- `conversions` (second return value) is for cross-market conversion requests (R4+), set to `0` for R1.
