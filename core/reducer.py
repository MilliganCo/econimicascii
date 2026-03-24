"""Main reducer: applies actions to game state."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Dict, List

from .actions import Action, DrawCardsAction, EndDayAction, PlayCardAction, SelectResourceAction
from .cards import apply_card_effect
from .deck import draw_cards, init_deck
from .events import apply_event
from .market import end_of_day_market, execute_trade
from .rng import Rng
from .state import (
    ActiveEffect,
    Contract,
    GameState,
    LimitOrder,
    PlayerState,
    Resource,
    ResourceId,
)


def clamp_int(x: float) -> int:
    """Clamp float to non-negative int."""
    return int(x) if x >= 0 else 0


def apply_action(game: GameState, action: Action, cards_data: Dict[str, Any], events_data: List[Dict[str, Any]]) -> GameState:
    """
    Apply action to game state.

    Args:
        game: Current game state
        action: Action to apply
        cards_data: Cards data from JSON (dict mapping card_id to card data)
        events_data: Events list from JSON

    Returns:
        New game state
    """
    rng = Rng(game.seed + game.day * 9973)

    if isinstance(action, PlayCardAction):
        return _apply_play_card(game, action, cards_data, rng)
    elif isinstance(action, SelectResourceAction):
        return _apply_select_resource(game, action)
    elif isinstance(action, EndDayAction):
        return _apply_end_day(game, events_data, rng)
    elif isinstance(action, DrawCardsAction):
        return _apply_draw_cards(game, rng)
    else:
        return game


def _apply_play_card(
    game: GameState, action: PlayCardAction, cards_data: Dict[str, Any], rng: Rng
) -> GameState:
    """Play a card from hand."""
    if action.card_id not in game.hand:
        return replace(game, log=["Карта не в руке"] + game.log)

    if game.actions_left <= 0:
        return replace(game, log=["Нет действий на этот день"] + game.log)

    card_data = cards_data.get(action.card_id)
    if not card_data:
        return replace(game, log=["Неизвестная карта"] + game.log)

    # Apply card effect
    new_game = apply_card_effect(game, action.card_id, card_data, action.params, rng)

    # Remove card from hand and add to discard
    new_hand = [c for c in new_game.hand if c != action.card_id]
    new_discard = list(new_game.discard) + [action.card_id]

    # Consume action
    new_actions = new_game.actions_left - 1

    return replace(
        new_game,
        hand=new_hand,
        discard=new_discard,
        actions_left=new_actions,
    )


def _apply_select_resource(game: GameState, action: SelectResourceAction) -> GameState:
    """Select resource for viewing/actions."""
    if action.resource_id in game.market.resources:
        return replace(game, selected_resource=action.resource_id)
    return game


def _apply_draw_cards(game: GameState, rng: Rng) -> GameState:
    """Draw cards to fill hand."""
    new_deck, new_hand, new_discard = draw_cards(
        game.deck, game.hand, game.discard, game.player.hand_size, rng
    )
    return replace(game, deck=new_deck, hand=new_hand, discard=new_discard)


def _apply_end_day(game: GameState, events_data: List[Dict[str, Any]], rng: Rng) -> GameState:
    """Process end of day: events, market evolution, contracts, economy."""
    # 1) Pick and apply event
    event = rng.choice(events_data)
    game = apply_event(game, event, rng)

    # 2) Process limit orders
    game = _process_limit_orders(game, rng)

    # 3) Process contracts (check completion, decrement days)
    game = _process_contracts(game, rng)

    # 4) Process active effects (decrement duration, apply effects)
    game = _process_active_effects(game)

    # 5) Inventory decay
    game = _process_inventory_decay(game)

    # 6) Storage penalty
    game = _process_storage_penalty(game)

    # 7) Economy: overhead, interest, fees
    game = _process_economy(game)

    # 8) Market evolution
    game = replace(game, market=end_of_day_market(game.market, rng))

    # 9) Next day setup
    new_day = game.day + 1
    new_actions = 3
    game = replace(game, day=new_day, actions_left=new_actions)

    # 10) Draw cards for new day
    game = _apply_draw_cards(game, rng)

    return game


def _process_limit_orders(game: GameState, rng: Rng) -> GameState:
    """Check and execute limit orders."""
    new_orders = []
    new_game = game

    for order in game.limit_orders:
        resource = game.market.resources[order.resource]
        new_ttl = order.ttl - 1

        # Check if order executes
        executed = False
        if order.direction == 1:  # Buy order
            if resource.price <= order.limit_price:
                executed = True
        else:  # Sell order
            if resource.price >= order.limit_price:
                executed = True

        if executed:
            # Execute order
            new_market, exec_price = execute_trade(
                new_game.market, order.resource, order.qty, order.direction
            )

            # Update player
            total_cost = int(exec_price * order.qty)
            if order.direction == 1:  # Buy
                if new_game.player.gold >= total_cost:
                    new_gold = new_game.player.gold - total_cost
                    new_inventory = dict(new_game.player.inventory)
                    new_inventory[order.resource] = (
                        new_inventory.get(order.resource, 0) + order.qty
                    )
                    new_player = replace(new_game.player, gold=new_gold, inventory=new_inventory)
                    new_game = replace(new_game, market=new_market, player=new_player)
                    new_game = replace(
                        new_game,
                        log=[f"Лимитный ордер исполнен: покупка {order.qty}x {order.resource} @ {exec_price:.0f}"]
                        + new_game.log,
                    )
                else:
                    # Not enough gold, keep order
                    new_orders.append(replace(order, ttl=new_ttl))
            else:  # Sell
                current_inv = new_game.player.inventory.get(order.resource, 0)
                if current_inv >= order.qty:
                    new_gold = new_game.player.gold + total_cost
                    new_inventory = dict(new_game.player.inventory)
                    new_inventory[order.resource] = current_inv - order.qty
                    new_player = replace(new_game.player, gold=new_gold, inventory=new_inventory)
                    new_game = replace(new_game, market=new_market, player=new_player)
                    new_game = replace(
                        new_game,
                        log=[f"Лимитный ордер исполнен: продажа {order.qty}x {order.resource} @ {exec_price:.0f}"]
                        + new_game.log,
                    )
                else:
                    # Not enough inventory, keep order
                    new_orders.append(replace(order, ttl=new_ttl))
        else:
            # Order not executed, decrement TTL
            if new_ttl > 0:
                new_orders.append(replace(order, ttl=new_ttl))

    return replace(new_game, limit_orders=new_orders)


def _process_contracts(game: GameState, rng: Rng) -> GameState:
    """Process contracts: check completion, apply rewards/penalties."""
    new_contracts = []
    new_game = game
    new_player = game.player

    for contract in game.contracts:
        new_days_left = contract.days_left - 1

        # Check if contract is fulfilled
        fulfilled = True
        for rid, required_qty in contract.requirements.items():
            if rid == "*":
                # Mixed contract: check total inventory value
                total_value = sum(
                    new_game.market.resources.get(r, Resource("", "", 0, 0, 0, 0)).price * qty
                    for r, qty in new_game.player.inventory.items()
                )
                target_value = required_qty * 100  # Approximate value
                if total_value < target_value:
                    fulfilled = False
                    break
            elif rid == "RANDOM":
                # Should not happen, but handle gracefully
                fulfilled = False
                break
            else:
                current_qty = new_game.player.inventory.get(rid, 0)
                if current_qty < required_qty:
                    fulfilled = False
                    break

        if fulfilled:
            # Contract completed
            reward = contract.reward
            rep_reward = contract.rep_reward

            # Consume inventory
            new_inventory = dict(new_game.player.inventory)
            for rid, required_qty in contract.requirements.items():
                if rid not in ("*", "RANDOM") and rid in new_inventory:
                    new_inventory[rid] = max(0, new_inventory[rid] - required_qty)

            new_gold = new_game.player.gold + reward
            new_reputation = new_game.player.reputation + rep_reward
            new_player = replace(
                new_player, gold=new_gold, reputation=new_reputation, inventory=new_inventory
            )
            new_game = replace(new_game, player=new_player)
            new_game = replace(
                new_game,
                log=[f"Контракт выполнен: {contract.name} (+{reward} золота)"]
                + new_game.log,
            )
        elif new_days_left <= 0:
            # Contract failed
            penalty = contract.penalty
            penalty_mult = new_game.next_penalty_mult
            actual_penalty = int(penalty * penalty_mult)

            new_gold = new_game.player.gold - actual_penalty
            new_player = replace(new_player, gold=new_gold)
            new_game = replace(new_game, player=new_player, next_penalty_mult=1.0)
            new_game = replace(
                new_game,
                log=[f"Контракт провален: {contract.name} (штраф {actual_penalty})"]
                + new_game.log,
            )
        else:
            # Contract still active
            new_contracts.append(replace(contract, days_left=new_days_left))

    return replace(new_game, contracts=new_contracts)


def _process_active_effects(game: GameState) -> GameState:
    """Process active effects: decrement duration."""
    new_effects = []
    for effect in game.active_effects:
        new_duration = effect.duration_days - 1
        if new_duration > 0:
            new_effects.append(replace(effect, duration_days=new_duration))
        else:
            # Effect expired
            if effect.effect_type == "insurance":
                game = replace(game, log=["Страховка истекла"] + game.log)
            elif effect.effect_type == "hedge":
                game = replace(game, log=["Хедж истёк"] + game.log)
            elif effect.effect_type == "restructure":
                game = replace(game, log=["Реструктуризация завершена"] + game.log)

    return replace(game, active_effects=new_effects)


def _process_inventory_decay(game: GameState) -> GameState:
    """Process inventory decay (Vitriol)."""
    new_inventory = dict(game.player.inventory)
    decay_mult = game.player.vitriol_decay_mult

    # Check for insurance
    insurance_active = False
    loss_mult = 1.0
    for effect in game.active_effects:
        if effect.effect_type == "insurance":
            insurance_active = True
            loss_mult = effect.params.get("loss_mult", 1.0)
            break

    for rid, qty in list(new_inventory.items()):
        resource = game.market.resources.get(rid)
        if resource and resource.decay > 0.0 and qty > 0:
            decay_rate = resource.decay * decay_mult * loss_mult
            lost = clamp_int(qty * decay_rate)
            if lost > 0:
                new_inventory[rid] = max(0, qty - lost)
                msg = f"Порча: {resource.name} -{lost}"
                if insurance_active:
                    msg += " (страховка снизила потери)"
                game = replace(game, log=[msg] + game.log)

    new_player = replace(game.player, inventory=new_inventory)
    return replace(game, player=new_player)


def _process_storage_penalty(game: GameState) -> GameState:
    """Process storage overflow penalty."""
    total_inv = sum(game.player.inventory.values())
    if total_inv > game.player.storage_cap:
        overflow = total_inv - game.player.storage_cap
        penalty = 2 * overflow
        new_gold = game.player.gold - penalty
        new_player = replace(game.player, gold=new_gold)
        return replace(
            game,
            player=new_player,
            log=[f"Переполнен склад: штраф {penalty}"] + game.log,
        )
    return game


def _process_economy(game: GameState) -> GameState:
    """Process daily economy: overhead, interest, fees."""
    # Calculate overhead (may be reduced by restructure)
    overhead_mult = 1.0
    for effect in game.active_effects:
        if effect.effect_type == "restructure":
            overhead_mult = effect.params.get("overhead_mult", 1.0)

    overhead = int(game.player.daily_overhead * overhead_mult)

    # Interest on debt
    interest_rate = 0.02 * game.interest_multiplier
    interest = clamp_int(game.player.debt * interest_rate)

    expenses = overhead + interest
    new_gold = game.player.gold - expenses

    log_msg = f"День {game.day}: расходы {expenses} (накладные {overhead}, проценты {interest})"
    new_player = replace(game.player, gold=new_gold)

    return replace(game, player=new_player, log=[log_msg] + game.log)

