"""Card system: card effects and their application."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Dict, Optional, Tuple

from .market import execute_trade
from .rng import Rng
from .state import (
    ActiveEffect,
    Contract,
    GameState,
    LimitOrder,
    PlayerState,
    ResourceId,
    TradeModifier,
)


def apply_card_effect(
    game: GameState,
    card_id: str,
    card_data: Dict[str, Any],
    params: Dict[str, Any],
    rng: Rng,
) -> GameState:
    """
    Apply card effect to game state.

    Args:
        game: Current game state
        card_id: Card ID
        card_data: Full card data from JSON
        params: User-provided parameters (resource, qty, price, etc.)
        rng: Random number generator

    Returns:
        New game state after card effect
    """
    card_type = card_data.get("type", "")
    card_params = card_data.get("params", {})

    if card_type == "trade":
        return _apply_trade_card(game, card_id, card_params, params, rng)
    elif card_type == "order":
        return _apply_order_card(game, card_id, card_params, params)
    elif card_type == "contract":
        return _apply_contract_card(game, card_id, card_data, card_params, rng)
    elif card_type == "modifier":
        return _apply_modifier_card(game, card_id, card_params)
    elif card_type == "risk":
        return _apply_risk_card(game, card_id, card_params)
    elif card_type == "finance":
        return _apply_finance_card(game, card_id, card_params)
    elif card_type == "info":
        return _apply_info_card(game, card_id, card_params)
    elif card_type == "infra":
        return _apply_infra_card(game, card_id, card_params)
    elif card_type == "influence":
        return _apply_influence_card(game, card_id, card_params, params, rng)
    else:
        return game


def _apply_trade_card(
    game: GameState,
    card_id: str,
    card_params: Dict[str, Any],
    user_params: Dict[str, Any],
    rng: Rng,
) -> GameState:
    """Apply trade card (buy/sell)."""
    resource_id = user_params.get("resource_id")
    qty = user_params.get("qty", 1)

    if not resource_id or resource_id not in game.market.resources:
        return replace(game, log=["Ошибка: неверный ресурс"] + game.log)

    direction = card_params.get("direction", 1)
    slip_mult = card_params.get("slip_mult", 1.0)
    impact_mult = card_params.get("impact_mult", 1.0)
    discount_pct = card_params.get("discount_pct", 0.0)
    premium_pct = card_params.get("premium_pct", 0.0)
    fee_gold = card_params.get("fee_gold", 0)
    ignore_storage = card_params.get("ignore_storage_penalty", False)

    # Apply trade modifier if active
    modifier = game.trade_modifier
    if modifier and modifier.remaining_trades > 0:
        slip_mult *= modifier.slip_mult
        impact_mult *= modifier.impact_mult
        # Consume modifier
        new_modifier = replace(modifier, remaining_trades=modifier.remaining_trades - 1)
        if new_modifier.remaining_trades <= 0:
            new_modifier = None
    else:
        new_modifier = game.trade_modifier

    # Apply discount/premium
    if discount_pct > 0 and direction == 1:
        slip_mult *= (1.0 - discount_pct / 100.0)
    if premium_pct > 0 and direction == -1:
        slip_mult *= (1.0 + premium_pct / 100.0)

    # Check for hedge (only for sell orders)
    hedge_price = None
    if direction == -1:  # Sell
        for effect in game.active_effects:
            if effect.effect_type == "hedge":
                hedge_resource = effect.params.get("resource")
                hedge_max_qty = effect.params.get("max_qty", 999)
                if hedge_resource == resource_id and qty <= hedge_max_qty:
                    hedge_price = effect.params.get("fixed_price")
                    break

    # Execute trade
    if hedge_price is not None:
        # Use hedged price (fixed price, no slippage/impact)
        exec_price = hedge_price
        # Still apply market impact for realism
        new_market, _ = execute_trade(
            game.market, resource_id, qty, direction, 0.0, impact_mult
        )
    else:
        new_market, exec_price = execute_trade(
            game.market, resource_id, qty, direction, slip_mult, impact_mult
        )

    # Calculate cost/revenue
    total_cost = int(exec_price * qty)
    if direction == 1:  # Buy
        # Check if we have enough gold
        if game.player.gold < total_cost + fee_gold:
            return replace(game, log=["Недостаточно золота"] + game.log)
        new_gold = game.player.gold - total_cost - fee_gold
        new_inventory = dict(game.player.inventory)
        new_inventory[resource_id] = new_inventory.get(resource_id, 0) + qty
    else:  # Sell
        # Check if we have enough inventory
        current_inv = game.player.inventory.get(resource_id, 0)
        if current_inv < qty:
            return replace(game, log=["Недостаточно товара"] + game.log)
        new_gold = game.player.gold + total_cost - fee_gold
        new_inventory = dict(game.player.inventory)
        new_inventory[resource_id] = current_inv - qty

    # Storage penalty (unless ignored)
    storage_penalty = 0
    if not ignore_storage:
        total_inv = sum(new_inventory.values())
        if total_inv > game.player.storage_cap:
            overflow = total_inv - game.player.storage_cap
            storage_penalty = 2 * overflow
            new_gold -= storage_penalty

    new_player = replace(game.player, gold=new_gold, inventory=new_inventory)
    action_name = "Покупка" if direction == 1 else "Продажа"
    log_msg = f"{action_name} {qty}x {resource_id} @ {exec_price:.0f}"
    if fee_gold > 0:
        log_msg += f" (комиссия {fee_gold})"
    if storage_penalty > 0:
        log_msg += f" (штраф за склад {storage_penalty})"

    return replace(
        game,
        market=new_market,
        player=new_player,
        trade_modifier=new_modifier,
        log=[log_msg] + game.log,
    )


def _apply_order_card(
    game: GameState,
    card_id: str,
    card_params: Dict[str, Any],
    user_params: Dict[str, Any],
) -> GameState:
    """Apply limit order card."""
    resource_id = user_params.get("resource_id")
    qty = user_params.get("qty", 1)
    limit_price = user_params.get("limit_price", 0.0)

    if not resource_id or resource_id not in game.market.resources:
        return replace(game, log=["Ошибка: неверный ресурс"] + game.log)

    if limit_price <= 0:
        return replace(game, log=["Ошибка: неверная цена"] + game.log)

    direction = card_params.get("direction", 1)
    ttl = card_params.get("ttl", 3)

    order = LimitOrder(
        resource=resource_id,
        qty=qty,
        limit_price=limit_price,
        direction=direction,
        ttl=ttl,
    )

    new_orders = list(game.limit_orders) + [order]
    order_type = "Покупка" if direction == 1 else "Продажа"
    log_msg = f"Лимитный ордер: {order_type} {qty}x {resource_id} @ {limit_price:.0f}"

    return replace(game, limit_orders=new_orders, log=[log_msg] + game.log)


def _apply_contract_card(
    game: GameState,
    card_id: str,
    card_data: Dict[str, Any],
    card_params: Dict[str, Any],
    rng: Rng,
) -> GameState:
    """Apply contract card."""
    requirements = card_params.get("requirements", {})
    days = card_params.get("days", 3)
    reward = card_params.get("reward", 0)
    penalty = card_params.get("penalty", 0)
    rep_reward = card_params.get("rep_reward", 0)

    # Handle random contract (guild tender)
    if "RANDOM" in requirements:
        # Random resource and quantity
        rids = list(game.market.resources.keys())
        rid = rng.choice(rids)
        qty = rng.randint(5, 15)
        requirements = {rid: qty}

    # Apply deadline extension from couriers
    deadline_ext = 0
    for effect in game.active_effects:
        if effect.effect_type == "couriers":
            deadline_ext = effect.params.get("deadline_extension", 0)
            break

    contract = Contract(
        name=card_data.get("name", "Контракт"),
        card_id=card_id,
        requirements=requirements,
        days_left=days + deadline_ext,
        reward=reward,
        penalty=penalty,
        rep_reward=rep_reward,
        deadline_extension=deadline_ext,
    )

    new_contracts = list(game.contracts) + [contract]
    req_str = ", ".join(f"{k}:{v}" for k, v in requirements.items())
    log_msg = f"Контракт принят: {contract.name} ({req_str}, {days} дней)"

    return replace(game, contracts=new_contracts, log=[log_msg] + game.log)


def _apply_modifier_card(
    game: GameState,
    card_id: str,
    card_params: Dict[str, Any],
) -> GameState:
    """Apply modifier card (affects next trade)."""
    slip_mult = card_params.get("slip_mult", 1.0)
    impact_mult = card_params.get("impact_mult", 1.0)
    duration_trades = card_params.get("duration_trades", 1)
    rep_cost = card_params.get("rep_cost", 0)

    # Check reputation cost
    if rep_cost > 0 and game.player.reputation < rep_cost:
        return replace(game, log=["Недостаточно репутации"] + game.log)

    modifier = TradeModifier(
        slip_mult=slip_mult,
        impact_mult=impact_mult,
        remaining_trades=duration_trades,
    )

    new_reputation = game.player.reputation - rep_cost
    new_player = replace(game.player, reputation=new_reputation)

    log_msg = f"Модификатор активен: следующий(ие) {duration_trades} сделки с улучшенными условиями"

    return replace(game, player=new_player, trade_modifier=modifier, log=[log_msg] + game.log)


def _apply_risk_card(
    game: GameState,
    card_id: str,
    card_params: Dict[str, Any],
) -> GameState:
    """Apply risk management card."""
    if card_id == "INSURANCE":
        duration = card_params.get("duration_days", 2)
        loss_mult = card_params.get("loss_mult", 0.3)
        effect = ActiveEffect(
            effect_type="insurance",
            duration_days=duration,
            params={"loss_mult": loss_mult},
        )
        new_effects = list(game.active_effects) + [effect]
        return replace(
            game,
            active_effects=new_effects,
            log=["Страховка активна: риск потерь снижен"] + game.log,
        )

    elif card_id == "HEDGE":
        duration = card_params.get("duration_days", 2)
        max_qty = card_params.get("max_qty", 8)
        resource_id = game.selected_resource
        current_price = game.market.resources[resource_id].price
        effect = ActiveEffect(
            effect_type="hedge",
            duration_days=duration,
            params={"resource": resource_id, "fixed_price": current_price, "max_qty": max_qty},
        )
        new_effects = list(game.active_effects) + [effect]
        return replace(
            game,
            active_effects=new_effects,
            log=[f"Хедж активен: цена {resource_id} зафиксирована @ {current_price:.0f}"] + game.log,
        )

    elif card_id == "ARBITER":
        penalty_mult = card_params.get("next_penalty_mult", 0.5)
        return replace(
            game,
            next_penalty_mult=penalty_mult,
            log=["Арбитражный щит активен: следующий штраф снижен"] + game.log,
        )

    return game


def _apply_finance_card(
    game: GameState,
    card_id: str,
    card_params: Dict[str, Any],
) -> GameState:
    """Apply finance card."""
    if card_id == "GUILD_LOAN":
        gold = card_params.get("gold", 0)
        debt = card_params.get("debt", 0)
        rep_cost = card_params.get("rep_cost", 0)

        if game.player.reputation < rep_cost:
            return replace(game, log=["Недостаточно репутации"] + game.log)

        new_gold = game.player.gold + gold
        new_debt = game.player.debt + debt
        new_reputation = game.player.reputation - rep_cost
        new_player = replace(
            game.player, gold=new_gold, debt=new_debt, reputation=new_reputation
        )

        return replace(
            game,
            player=new_player,
            log=[f"Залог получен: +{gold} золота, долг +{debt}"] + game.log,
        )

    elif card_id == "RESTRUCTURE":
        overhead_mult = card_params.get("overhead_mult", 0.7)
        duration = card_params.get("duration_days", 3)
        debt_increase_pct = card_params.get("debt_increase_pct", 5)

        new_debt = int(game.player.debt * (1.0 + debt_increase_pct / 100.0))
        effect = ActiveEffect(
            effect_type="restructure",
            duration_days=duration,
            params={"overhead_mult": overhead_mult},
        )

        new_effects = list(game.active_effects) + [effect]
        new_player = replace(game.player, debt=new_debt)

        return replace(
            game,
            player=new_player,
            active_effects=new_effects,
            log=[f"Реструктуризация: расходы снижены на {duration} дней"] + game.log,
        )

    return game


def _apply_info_card(
    game: GameState,
    card_id: str,
    card_params: Dict[str, Any],
) -> GameState:
    """Apply info card (oracle forecast)."""
    if card_id == "ORACLE":
        resource_id = game.selected_resource
        resource = game.market.resources[resource_id]
        log_msg = (
            f"Оракульский прогноз для {resource_id}: "
            f"Фундаментал={resource.fundamental:.0f}, "
            f"Волатильность={resource.volatility:.3f}"
        )
        return replace(game, log=[log_msg] + game.log)

    return game


def _apply_infra_card(
    game: GameState,
    card_id: str,
    card_params: Dict[str, Any],
) -> GameState:
    """Apply infrastructure card."""
    if card_id == "STORAGE_UP":
        cap_plus = card_params.get("cap_plus", 20)
        cost_plus = card_params.get("daily_cost_plus", 2)
        new_cap = game.player.storage_cap + cap_plus
        new_overhead = game.player.daily_overhead + cost_plus
        new_player = replace(game.player, storage_cap=new_cap, daily_overhead=new_overhead)
        return replace(
            game,
            player=new_player,
            log=[f"Склад расширен: +{cap_plus} вместимость"] + game.log,
        )

    elif card_id == "SEALED_CELLAR":
        decay_mult = card_params.get("vitriol_decay_mult", 0.4)
        cost_plus = card_params.get("daily_cost_plus", 3)
        new_decay_mult = game.player.vitriol_decay_mult * decay_mult
        new_overhead = game.player.daily_overhead + cost_plus
        new_player = replace(
            game.player, vitriol_decay_mult=new_decay_mult, daily_overhead=new_overhead
        )
        return replace(
            game,
            player=new_player,
            log=["Герметичный погреб построен: порча витриола снижена"] + game.log,
        )

    elif card_id == "SCRIBE":
        hand_plus = card_params.get("hand_plus", 1)
        cost_plus = card_params.get("daily_cost_plus", 3)
        new_hand_size = game.player.hand_size + hand_plus
        new_overhead = game.player.daily_overhead + cost_plus
        new_player = replace(game.player, hand_size=new_hand_size, daily_overhead=new_overhead)
        return replace(
            game,
            player=new_player,
            log=[f"Писарь нанят: рука +{hand_plus}"] + game.log,
        )

    elif card_id == "COURIERS":
        deadline_plus = card_params.get("contract_deadline_plus", 1)
        cost_gold = card_params.get("cost_gold", 90)

        if game.player.gold < cost_gold:
            return replace(game, log=["Недостаточно золота"] + game.log)

        effect = ActiveEffect(
            effect_type="couriers",
            duration_days=999,  # Permanent until end of game
            params={"deadline_extension": deadline_plus},
        )

        # Apply to existing contracts
        new_contracts = []
        for contract in game.contracts:
            new_contracts.append(
                replace(contract, days_left=contract.days_left + deadline_plus)
            )

        new_effects = list(game.active_effects) + [effect]
        new_gold = game.player.gold - cost_gold
        new_player = replace(game.player, gold=new_gold)

        return replace(
            game,
            player=new_player,
            contracts=new_contracts,
            active_effects=new_effects,
            log=[f"Курьерская сеть: дедлайны контрактов +{deadline_plus} день"] + game.log,
        )

    elif card_id == "LICENSE":
        fee_mult = card_params.get("fee_mult", 0.9)
        cost_gold = card_params.get("cost_gold", 120)
        rep_cost = card_params.get("rep_cost", 1)

        if game.player.gold < cost_gold:
            return replace(game, log=["Недостаточно золота"] + game.log)
        if game.player.reputation < rep_cost:
            return replace(game, log=["Недостаточно репутации"] + game.log)

        new_fee_mult = game.player.fee_multiplier * fee_mult
        new_gold = game.player.gold - cost_gold
        new_reputation = game.player.reputation - rep_cost
        new_player = replace(
            game.player, gold=new_gold, reputation=new_reputation, fee_multiplier=new_fee_mult
        )

        return replace(
            game,
            player=new_player,
            log=["Лицензия гильдии получена: комиссии снижены"] + game.log,
        )

    return game


def _apply_influence_card(
    game: GameState,
    card_id: str,
    card_params: Dict[str, Any],
    user_params: Dict[str, Any],
    rng: Rng,
) -> GameState:
    """Apply influence card (rumors)."""
    if card_id == "RUMORS":
        resource_id = user_params.get("resource_id", game.selected_resource)
        f_shift_pct = card_params.get("f_shift_pct", 7)
        vol_plus = card_params.get("vol_plus", 0.01)
        rep_cost = card_params.get("rep_cost", 2)

        if game.player.reputation < rep_cost:
            return replace(game, log=["Недостаточно репутации"] + game.log)

        if resource_id not in game.market.resources:
            return replace(game, log=["Ошибка: неверный ресурс"] + game.log)

        resource = game.market.resources[resource_id]
        new_fundamental = resource.fundamental * (1.0 + f_shift_pct / 100.0)
        new_volatility = resource.volatility + vol_plus

        # 30% chance of reverse effect
        if rng.random() < 0.3:
            new_fundamental = resource.fundamental * (1.0 - f_shift_pct / 100.0)
            log_msg = f"Слухи обернулись против тебя: {resource_id} упал"
        else:
            log_msg = f"Слухи распространяются: {resource_id} растёт"

        new_resource = replace(
            resource, fundamental=max(1.0, new_fundamental), volatility=max(0.001, new_volatility)
        )
        new_resources = dict(game.market.resources)
        new_resources[resource_id] = new_resource
        new_market = replace(game.market, resources=new_resources)

        new_reputation = game.player.reputation - rep_cost
        new_player = replace(game.player, reputation=new_reputation)

        return replace(
            game,
            market=new_market,
            player=new_player,
            log=[log_msg] + game.log,
        )

    return game

