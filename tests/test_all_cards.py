"""Test all card types to ensure they work correctly."""

import json
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.actions import PlayCardAction
from core.cards import apply_card_effect
from core.rng import Rng
from ui.pygame_app import init_game


def load_json(path: str) -> dict:
    """Load JSON file."""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    full_path = os.path.join(base, path)
    with open(full_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_trade_cards():
    """Test trade cards."""
    print("Тест: карты торговли")
    resources_json = load_json("data/resources.json")
    cards_json = load_json("data/cards.json")
    events_json = load_json("data/events.json")

    game_state = init_game(resources_json, cards_json, events_json, seed=12345)
    cards_dict = {card["id"]: card for card in cards_json["cards"]}
    rng = Rng(12345)

    trade_cards = ["MKT_BUY", "MKT_SELL", "BULK_BUY", "BULK_SELL", "URGENT_BUY", "JUNK_DUMP"]

    for card_id in trade_cards:
        if card_id not in cards_dict:
            continue

        card_data = cards_dict[card_id]
        params = {
            "resource_id": game_state.selected_resource,
            "qty": 5,
        }

        try:
            new_state = apply_card_effect(game_state, card_id, card_data, params, rng)
            print(f"  ✓ {card_data.get('name', card_id)}: работает")
        except Exception as e:
            print(f"  ✗ {card_data.get('name', card_id)}: ошибка - {e}")

    print()


def test_order_cards():
    """Test limit order cards."""
    print("Тест: лимитные ордера")
    resources_json = load_json("data/resources.json")
    cards_json = load_json("data/cards.json")
    events_json = load_json("data/events.json")

    game_state = init_game(resources_json, cards_json, events_json, seed=12345)
    cards_dict = {card["id"]: card for card in cards_json["cards"]}
    rng = Rng(12345)

    order_cards = ["LMT_BUY", "LMT_SELL"]

    for card_id in order_cards:
        if card_id not in cards_dict:
            continue

        card_data = cards_dict[card_id]
        resource = game_state.market.resources[game_state.selected_resource]
        params = {
            "resource_id": game_state.selected_resource,
            "qty": 5,
            "limit_price": resource.price * 0.9 if card_data["params"]["direction"] == 1 else resource.price * 1.1,
        }

        try:
            new_state = apply_card_effect(game_state, card_id, card_data, params, rng)
            assert len(new_state.limit_orders) > 0, "Ордер должен быть создан"
            print(f"  ✓ {card_data.get('name', card_id)}: работает")
        except Exception as e:
            print(f"  ✗ {card_data.get('name', card_id)}: ошибка - {e}")

    print()


def test_contract_cards():
    """Test contract cards."""
    print("Тест: контракты")
    resources_json = load_json("data/resources.json")
    cards_json = load_json("data/cards.json")
    events_json = load_json("data/events.json")

    game_state = init_game(resources_json, cards_json, events_json, seed=12345)
    cards_dict = {card["id"]: card for card in cards_json["cards"]}
    rng = Rng(12345)

    contract_cards = ["C_IRONWOOD", "C_AETHER", "C_SILK", "C_SCALE", "C_VITRIOL", "C_SALT"]

    for card_id in contract_cards:
        if card_id not in cards_dict:
            continue

        card_data = cards_dict[card_id]
        params = {}

        try:
            new_state = apply_card_effect(game_state, card_id, card_data, params, rng)
            assert len(new_state.contracts) > 0, "Контракт должен быть создан"
            print(f"  ✓ {card_data.get('name', card_id)}: работает")
        except Exception as e:
            print(f"  ✗ {card_data.get('name', card_id)}: ошибка - {e}")

    print()


def test_risk_cards():
    """Test risk management cards."""
    print("Тест: риск-менеджмент")
    resources_json = load_json("data/resources.json")
    cards_json = load_json("data/cards.json")
    events_json = load_json("data/events.json")

    game_state = init_game(resources_json, cards_json, events_json, seed=12345)
    cards_dict = {card["id"]: card for card in cards_json["cards"]}
    rng = Rng(12345)

    risk_cards = ["INSURANCE", "HEDGE", "ARBITER"]

    for card_id in risk_cards:
        if card_id not in cards_dict:
            continue

        card_data = cards_dict[card_id]
        params = {}

        try:
            new_state = apply_card_effect(game_state, card_id, card_data, params, rng)
            if card_id == "INSURANCE" or card_id == "HEDGE":
                assert len(new_state.active_effects) > 0, "Эффект должен быть активен"
            print(f"  ✓ {card_data.get('name', card_id)}: работает")
        except Exception as e:
            print(f"  ✗ {card_data.get('name', card_id)}: ошибка - {e}")

    print()


def test_infra_cards():
    """Test infrastructure cards."""
    print("Тест: инфраструктура")
    resources_json = load_json("data/resources.json")
    cards_json = load_json("data/cards.json")
    events_json = load_json("data/events.json")

    game_state = init_game(resources_json, cards_json, events_json, seed=12345)
    cards_dict = {card["id"]: card for card in cards_json["cards"]}
    rng = Rng(12345)

    infra_cards = ["STORAGE_UP", "SEALED_CELLAR", "SCRIBE", "LICENSE"]

    for card_id in infra_cards:
        if card_id not in cards_dict:
            continue

        card_data = cards_dict[card_id]
        params = {}

        try:
            new_state = apply_card_effect(game_state, card_id, card_data, params, rng)
            print(f"  ✓ {card_data.get('name', card_id)}: работает")
        except Exception as e:
            print(f"  ✗ {card_data.get('name', card_id)}: ошибка - {e}")

    print()


if __name__ == "__main__":
    print("=" * 60)
    print("ТЕСТЫ ВСЕХ КАРТ")
    print("=" * 60)
    print()

    test_trade_cards()
    test_order_cards()
    test_contract_cards()
    test_risk_cards()
    test_infra_cards()

    print("Все тесты карт завершены!")

