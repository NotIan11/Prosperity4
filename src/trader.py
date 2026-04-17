import json
from typing import Dict, List

from datamodel import Order, TradingState
from strategies.mean_reversion import MeanReversionStrategy
from strategies.osmium import OsmiumStrategy

PRODUCTS = {
    "ASH_COATED_OSMIUM": OsmiumStrategy("ASH_COATED_OSMIUM", position_limit=80),
    "INTARIAN_PEPPER_ROOT": MeanReversionStrategy(
        "INTARIAN_PEPPER_ROOT",
        position_limit=80,
        window=2,
        spread=1,
        order_size=15,
        soft_limit_frac=0.5,
    ),
}


class Trader:
    def run(self, state: TradingState) -> tuple[Dict[str, List[Order]], int, str]:
        orders: Dict[str, List[Order]] = {}

        for symbol, strategy in PRODUCTS.items():
            if symbol in state.order_depths:
                orders[symbol] = strategy.run(state)

        return orders, 0, ""
