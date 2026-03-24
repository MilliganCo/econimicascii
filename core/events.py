"""Event system: daily events affecting the market."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Dict, List

from .rng import Rng
from .state import GameState, MarketState


def apply_event(game: GameState, event: Dict[str, Any], rng: Rng) -> GameState:
    """
    Apply event effects to market and game state.

    Args:
        game: Current game state
        event: Event dictionary from JSON
        rng: Random number generator

    Returns:
        New game state with event effects applied
    """
    resources = dict(game.market.resources)
    interest_mult = game.interest_multiplier

    # Extract meta effects (like interest_mult)
    if "meta" in event and isinstance(event["meta"], dict):
        interest_mult = float(event["meta"].get("interest_mult", interest_mult))

    def apply_effect_to_resource(rid: str, eff: Dict[str, Any]) -> None:
        """Apply effect to a specific resource."""
        r = resources[rid]
        df = float(eff.get("delta_fundamental_pct", 0.0))
        dl = float(eff.get("delta_liquidity_pct", 0.0))
        dv = float(eff.get("delta_volatility_abs", 0.0))

        new_f = max(1.0, r.fundamental * (1.0 + df))
        new_l = max(5.0, r.liquidity * (1.0 + dl))
        new_v = max(0.001, r.volatility + dv)

        resources[rid] = replace(r, fundamental=new_f, liquidity=new_l, volatility=new_v)

    rids = list(resources.keys())

    # Apply all effects
    for eff in event.get("effects", []):
        target = eff.get("resource", "*")
        if target == "*":
            # Apply to all resources
            for rid in rids:
                apply_effect_to_resource(rid, eff)
        elif target == "RANDOM_ONE":
            # Apply to random resource
            rid = rng.choice(rids)
            apply_effect_to_resource(rid, eff)
        else:
            # Apply to specific resource
            if target in resources:
                apply_effect_to_resource(target, eff)

    new_market = replace(game.market, resources=resources)
    event_log = event.get("log", event.get("name", "Событие дня"))
    new_log = [event_log] + game.log

    return replace(game, market=new_market, log=new_log, interest_multiplier=interest_mult)

