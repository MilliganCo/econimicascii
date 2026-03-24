"""Basic tests for game mechanics."""

import json
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.state import GameState, MarketState, PlayerState, Resource
from core.rng import Rng
from core.market import execute_trade, end_of_day_market
from core.events import apply_event
from core.deck import init_deck, draw_cards


def load_json(path: str) -> dict:
    """Load JSON file."""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    full_path = os.path.join(base, path)
    with open(full_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_market_trade():
    """Test market trade execution."""
    print("Тест: выполнение сделки на рынке")
    resource = Resource(
        id="TEST_RESOURCE",
        name="Тестовый ресурс",
        price=100.0,
        fundamental=100.0,
        liquidity=50.0,
        volatility=0.02,
        decay=0.0,
    )
    market = MarketState(resources={"TEST_RESOURCE": resource}, history={})
    rng = Rng(12345)

    # Buy 10 units
    new_market, exec_price = execute_trade(market, "TEST_RESOURCE", 10, 1, 1.0, 1.0)
    assert new_market.resources["TEST_RESOURCE"].price > resource.price, "Цена должна вырасти после покупки"
    assert exec_price > resource.price, "Цена исполнения должна быть выше текущей"
    print(f"  ✓ Покупка: цена выросла с {resource.price:.2f} до {new_market.resources['TEST_RESOURCE'].price:.2f}")
    print(f"  ✓ Цена исполнения: {exec_price:.2f}")

    # Sell 5 units
    new_market2, exec_price2 = execute_trade(new_market, "TEST_RESOURCE", 5, -1, 1.0, 1.0)
    assert new_market2.resources["TEST_RESOURCE"].price < new_market.resources["TEST_RESOURCE"].price, "Цена должна упасть после продажи"
    print(f"  ✓ Продажа: цена упала до {new_market2.resources['TEST_RESOURCE'].price:.2f}")
    print("  ✓ Тест пройден\n")


def test_market_evolution():
    """Test market price evolution."""
    print("Тест: эволюция рынка")
    resource = Resource(
        id="TEST_RESOURCE",
        name="Тестовый ресурс",
        price=100.0,
        fundamental=110.0,  # Higher fundamental
        liquidity=50.0,
        volatility=0.02,
        decay=0.0,
    )
    market = MarketState(resources={"TEST_RESOURCE": resource}, history={})
    rng = Rng(12345)

    # Evolve market
    new_market = end_of_day_market(market, rng)
    new_price = new_market.resources["TEST_RESOURCE"].price

    # Price should move toward fundamental (mean reversion)
    assert abs(new_price - resource.fundamental) < abs(resource.price - resource.fundamental), \
        "Цена должна двигаться к фундаменталу"
    print(f"  ✓ Цена двигается к фундаменталу: {resource.price:.2f} -> {new_price:.2f} (фундаментал: {resource.fundamental:.2f})")
    print("  ✓ Тест пройден\n")


def test_event_application():
    """Test event application."""
    print("Тест: применение событий")
    resource = Resource(
        id="AETHER_DUST",
        name="Эфирный Прах",
        price=180.0,
        fundamental=180.0,
        liquidity=70.0,
        volatility=0.035,
        decay=0.0,
    )
    market = MarketState(resources={"AETHER_DUST": resource}, history={})
    player = PlayerState(
        gold=500, debt=200, reputation=0, storage_cap=40, daily_overhead=10, inventory={}
    )
    game = GameState(
        seed=12345,
        day=1,
        max_days=30,
        actions_left=3,
        selected_resource="AETHER_DUST",
        player=player,
        market=market,
        hand=[],
        deck=[],
        discard=[],
        log=[],
    )

    event = {
        "id": "MAGES_PARADE",
        "name": "Парад магов",
        "log": "Парад магов: эфирный прах сметают на ритуалы.",
        "effects": [
            {"resource": "AETHER_DUST", "delta_fundamental_pct": 0.06, "delta_liquidity_pct": -0.10, "delta_volatility_abs": 0.008}
        ]
    }

    rng = Rng(12345)
    new_game = apply_event(game, event, rng)

    new_resource = new_game.market.resources["AETHER_DUST"]
    assert new_resource.fundamental > resource.fundamental, "Фундаментал должен вырасти"
    assert new_resource.liquidity < resource.liquidity, "Ликвидность должна упасть"
    assert new_resource.volatility > resource.volatility, "Волатильность должна вырасти"

    print(f"  ✓ Фундаментал: {resource.fundamental:.2f} -> {new_resource.fundamental:.2f}")
    print(f"  ✓ Ликвидность: {resource.liquidity:.2f} -> {new_resource.liquidity:.2f}")
    print(f"  ✓ Волатильность: {resource.volatility:.4f} -> {new_resource.volatility:.4f}")
    print("  ✓ Тест пройден\n")


def test_deck_management():
    """Test deck and hand management."""
    print("Тест: управление колодой")
    cards_json = load_json("data/cards.json")
    cards_dict = {card["id"]: card for card in cards_json["cards"]}

    deck = init_deck(cards_dict)
    assert len(deck) == 30, f"Колода должна содержать 30 карт, получено {len(deck)}"

    rng = Rng(12345)
    rng.shuffle(deck)

    hand = []
    discard = []
    new_deck, new_hand, new_discard = draw_cards(deck, hand, discard, 5, rng)

    assert len(new_hand) == 5, f"Рука должна содержать 5 карт, получено {len(new_hand)}"
    assert len(new_deck) == 25, f"Колода должна содержать 25 карт, получено {len(new_deck)}"

    print(f"  ✓ Колода инициализирована: {len(deck)} карт")
    print(f"  ✓ Добор карт: рука {len(new_hand)}, колода {len(new_deck)}")
    print("  ✓ Тест пройден\n")


if __name__ == "__main__":
    print("Запуск базовых тестов...\n")
    test_market_trade()
    test_market_evolution()
    test_event_application()
    test_deck_management()
    print("Все базовые тесты пройдены! ✓")

