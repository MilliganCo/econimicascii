"""Game state structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

ResourceId = str


@dataclass(frozen=True)
class Resource:
    """Market resource with price dynamics."""

    id: ResourceId
    name: str
    price: float
    fundamental: float
    liquidity: float
    volatility: float
    decay: float = 0.0  # daily inventory loss fraction


@dataclass(frozen=True)
class MarketState:
    """Market state with all resources and price history."""

    resources: Dict[ResourceId, Resource]
    history: Dict[ResourceId, List[float]] = field(default_factory=dict)


@dataclass(frozen=True)
class LimitOrder:
    """Limit order waiting for execution."""

    resource: ResourceId
    qty: int
    limit_price: float
    direction: int  # +1 buy, -1 sell
    ttl: int  # days until expiration


@dataclass(frozen=True)
class Contract:
    """Active contract requiring delivery."""

    name: str
    card_id: str
    requirements: Dict[ResourceId, int]
    days_left: int
    reward: int
    penalty: int
    rep_reward: int = 0
    deadline_extension: int = 0  # from couriers


@dataclass(frozen=True)
class ActiveEffect:
    """Temporary effect (insurance, hedge, etc.)."""

    effect_type: str  # "insurance", "hedge", "restructure", etc.
    duration_days: int
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TradeModifier:
    """Modifier for next trade (split order, quiet trade)."""

    slip_mult: float = 1.0
    impact_mult: float = 1.0
    remaining_trades: int = 0


@dataclass(frozen=True)
class PlayerState:
    """Player state: money, inventory, stats."""

    gold: int
    debt: int
    reputation: int
    inventory: Dict[ResourceId, int]
    storage_cap: int
    daily_overhead: int
    hand_size: int = 5  # max cards in hand
    fee_multiplier: float = 1.0  # from license
    vitriol_decay_mult: float = 1.0  # from sealed cellar


@dataclass(frozen=True)
class GameState:
    """Complete game state."""

    seed: int
    day: int
    max_days: int
    actions_left: int
    selected_resource: ResourceId
    player: PlayerState
    market: MarketState
    hand: List[str]  # card ids
    deck: List[str]
    discard: List[str]
    limit_orders: List[LimitOrder] = field(default_factory=list)
    contracts: List[Contract] = field(default_factory=list)
    active_effects: List[ActiveEffect] = field(default_factory=list)
    trade_modifier: Optional[TradeModifier] = None
    next_penalty_mult: float = 1.0  # from arbiter shield
    log: List[str] = field(default_factory=list)
    interest_multiplier: float = 1.0  # from events

