"""Black-Scholes pricing for IMC Prosperity vouchers.

Stdlib only — uses statistics.NormalDist instead of scipy.stats so it runs
on the IMC Lambda runtime without extra dependencies.

Adapted from CMU Physics's P3 trader (chrispyroberts/imc-prosperity-3,
ROUND 3/big_volcano_man.py L18-82). MIT-style attribution: see
docs/round_3/research/02b_cmu.md.
"""
from math import log, sqrt
from statistics import NormalDist

_N = NormalDist()


class BlackScholes:
    @staticmethod
    def call_price(spot: float, strike: float, tte: float, vol: float) -> float:
        d1 = (log(spot) - log(strike) + 0.5 * vol * vol * tte) / (vol * sqrt(tte))
        d2 = d1 - vol * sqrt(tte)
        return spot * _N.cdf(d1) - strike * _N.cdf(d2)

    @staticmethod
    def put_price(spot: float, strike: float, tte: float, vol: float) -> float:
        d1 = (log(spot / strike) + 0.5 * vol * vol * tte) / (vol * sqrt(tte))
        d2 = d1 - vol * sqrt(tte)
        return strike * _N.cdf(-d2) - spot * _N.cdf(-d1)

    @staticmethod
    def delta(spot: float, strike: float, tte: float, vol: float) -> float:
        d1 = (log(spot) - log(strike) + 0.5 * vol * vol * tte) / (vol * sqrt(tte))
        return _N.cdf(d1)

    @staticmethod
    def gamma(spot: float, strike: float, tte: float, vol: float) -> float:
        d1 = (log(spot) - log(strike) + 0.5 * vol * vol * tte) / (vol * sqrt(tte))
        return _N.pdf(d1) / (spot * vol * sqrt(tte))

    @staticmethod
    def vega(spot: float, strike: float, tte: float, vol: float) -> float:
        d1 = (log(spot) - log(strike) + 0.5 * vol * vol * tte) / (vol * sqrt(tte))
        return _N.pdf(d1) * spot * sqrt(tte) / 100

    @staticmethod
    def implied_vol(
        call: float, spot: float, strike: float, tte: float,
        max_iter: int = 200, tol: float = 1e-10,
    ) -> float:
        """Bisection IV solver. Returns vol in (0, 1]."""
        lo, hi = 0.001, 1.0
        vol = (lo + hi) / 2.0
        for _ in range(max_iter):
            est = BlackScholes.call_price(spot, strike, tte, vol)
            diff = est - call
            if abs(diff) < tol:
                break
            if diff > 0:
                hi = vol
            else:
                lo = vol
            vol = (lo + hi) / 2.0
        return vol
