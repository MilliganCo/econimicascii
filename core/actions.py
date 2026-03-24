"""Action types for game state updates."""

from dataclasses import dataclass
from typing import Any, Dict

from .state import ResourceId


@dataclass(frozen=True)
class Action:
    """Base action class."""

    pass


@dataclass(frozen=True)
class PlayCardAction(Action):
    """Play a card from hand."""

    card_id: str
    params: Dict[str, Any]  # resource_id, qty, limit_price, etc.


@dataclass(frozen=True)
class SelectResourceAction(Action):
    """Select resource for viewing/actions."""

    resource_id: ResourceId


@dataclass(frozen=True)
class EndDayAction(Action):
    """End current day and process end-of-day logic."""

    pass


@dataclass(frozen=True)
class DrawCardsAction(Action):
    """Draw cards to fill hand (called at start of day)."""

    pass

