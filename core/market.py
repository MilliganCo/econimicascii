"""Market model: slippage, impact, price evolution."""

from __future__ import annotations

from dataclasses import replace
from typing import Tuple

from .rng import Rng
from .state import MarketState, ResourceId

# Market constants
S = 0.10  # slippage sensitivity (per q/L)
K = 0.06  # impact sensitivity (per q/L)
A = 0.18  # mean reversion strength
F_VOL = 0.003  # fundamental drift (fraction)


def execute_trade(
    market: MarketState,
    rid: ResourceId,
    qty: int,
    direction: int,
    slip_mult: float = 1.0,
    impact_mult: float = 1.0,
) -> Tuple[MarketState, float]:
    """
    Execute a trade with slippage and market impact.

    Args:
        market: Current market state
        rid: Resource ID
        qty: Quantity to trade
        direction: +1 for buy, -1 for sell
        slip_mult: Multiplier for slippage (default 1.0)
        impact_mult: Multiplier for impact (default 1.0)

    Returns:
        Tuple of (new market state, execution price)
    """
    rm = market.resources[rid]
    q = max(0, qty)
    L = max(1.0, rm.liquidity)
    P = rm.price

    # Slippage: execution price moves against you
    slip = S * slip_mult * (q / L)
    exec_price = P * (1.0 + slip * direction)

    # Impact: price moves permanently after trade
    impact = K * impact_mult * (q / L) * direction
    new_price = P * (1.0 + impact)
    new_price = max(1.0, new_price)

    new_rm = replace(rm, price=new_price)
    new_res = dict(market.resources)
    new_res[rid] = new_rm
    return replace(market, resources=new_res), exec_price


def end_of_day_market(market: MarketState, rng: Rng) -> MarketState:
    """
    Evolve market: fundamental drift, mean reversion, noise.

    Args:
        market: Current market state
        rng: Random number generator

    Returns:
        New market state with evolved prices
    """
    new_resources: dict[ResourceId, Resource] = {}
    new_history: dict[ResourceId, list[float]] = {
        k: list(v) for k, v in market.history.items()
    }

    for rid, rm in market.resources.items():
        # Fundamental drift (slow random walk)
        F = rm.fundamental + rng.gauss(0.0, max(1.0, rm.fundamental) * F_VOL)

        # Mean reversion toward fundamental
        P = rm.price + A * (F - rm.price)

        # Noise (volatility)
        P = P + rng.gauss(0.0, max(1.0, P) * rm.volatility)
        P = max(1.0, P)

        new_rm = replace(rm, price=P, fundamental=max(1.0, F))
        new_resources[rid] = new_rm

        # Update history
        new_history.setdefault(rid, []).append(P)

    return replace(market, resources=new_resources, history=new_history)

