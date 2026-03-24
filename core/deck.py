"""Deck management: shuffle, draw, discard."""

from __future__ import annotations

from typing import Dict, List, Tuple

from .rng import Rng


def init_deck(cards_data: Dict[str, Dict]) -> List[str]:
    """
    Initialize deck from cards data.

    Args:
        cards_data: Dictionary mapping card_id to card data

    Returns:
        List of card IDs (deck)
    """
    return list(cards_data.keys())


def draw_cards(
    deck: List[str],
    hand: List[str],
    discard: List[str],
    target_hand_size: int,
    rng: Rng,
) -> Tuple[List[str], List[str], List[str]]:
    """
    Draw cards to fill hand to target size.

    Args:
        deck: Current deck
        hand: Current hand
        discard: Current discard pile
        target_hand_size: Target hand size
        rng: Random number generator

    Returns:
        Tuple of (new_deck, new_hand, new_discard)
    """
    new_deck = list(deck)
    new_hand = list(hand)
    new_discard = list(discard)

    # Shuffle discard into deck if deck is empty
    if not new_deck and new_discard:
        new_deck = new_discard
        new_discard = []
        rng.shuffle(new_deck)

    # Draw until hand is full
    while len(new_hand) < target_hand_size and new_deck:
        card = new_deck.pop(0)
        new_hand.append(card)

    return new_deck, new_hand, new_discard

