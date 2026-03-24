"""UI simulation test - simulates keyboard input and game actions."""

import json
import os
import sys
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame
from core.actions import DrawCardsAction, EndDayAction, PlayCardAction, SelectResourceAction
from core.reducer import apply_action
from ui.pygame_app import init_game


def load_json(path: str) -> dict:
    """Load JSON file."""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    full_path = os.path.join(base, path)
    with open(full_path, "r", encoding="utf-8") as f:
        return json.load(f)


class UISimulator:
    """Simulates UI interactions without pygame window."""

    def __init__(self, game_state, cards_data, events_data):
        self.game_state = game_state
        self.cards_data = cards_data
        self.events_data = events_data
        self.actions_log = []

    def simulate_key(self, key_name: str):
        """Simulate key press."""
        key_map = {
            "UP": pygame.K_UP,
            "DOWN": pygame.K_DOWN,
            "1": pygame.K_1,
            "2": pygame.K_2,
            "3": pygame.K_3,
            "4": pygame.K_4,
            "5": pygame.K_5,
            "E": pygame.K_e,
            "ENTER": pygame.K_RETURN,
        }

        if key_name not in key_map:
            return None

        key = key_map[key_name]

        # Resource selection
        if key == pygame.K_UP:
            idx = self._get_resource_index(self.game_state.selected_resource)
            rids = list(self.game_state.market.resources.keys())
            new_idx = (idx - 1) % len(rids)
            action = SelectResourceAction(resource_id=rids[new_idx])
        elif key == pygame.K_DOWN:
            idx = self._get_resource_index(self.game_state.selected_resource)
            rids = list(self.game_state.market.resources.keys())
            new_idx = (idx + 1) % len(rids)
            action = SelectResourceAction(resource_id=rids[new_idx])
        elif pygame.K_1 <= key <= pygame.K_5:
            card_idx = key - pygame.K_1
            if card_idx < len(self.game_state.hand):
                card_id = self.game_state.hand[card_idx]
                # Simple trade card
                if card_id in ["MKT_BUY", "MKT_SELL"]:
                    params = {
                        "resource_id": self.game_state.selected_resource,
                        "qty": 5,
                    }
                    action = PlayCardAction(card_id=card_id, params=params)
                else:
                    params = {}
                    action = PlayCardAction(card_id=card_id, params=params)
            else:
                return None
        elif key == pygame.K_e:
            action = EndDayAction()
        else:
            return None

        self.game_state = apply_action(self.game_state, action, self.cards_data, self.events_data)
        self.actions_log.append(f"Нажата клавиша: {key_name}")
        return action

    def _get_resource_index(self, rid):
        """Get index of resource in list."""
        rids = list(self.game_state.market.resources.keys())
        return rids.index(rid) if rid in rids else 0

    def simulate_full_game(self, max_days: int = 5):
        """Simulate a full game session."""
        print(f"\n=== Симуляция игры на {max_days} дней ===\n")

        day = 1
        while day <= max_days and self.game_state.player.gold > -200:
            print(f"--- День {self.game_state.day} ---")
            print(f"Золото: {self.game_state.player.gold}, Долг: {self.game_state.player.debt}")
            print(f"Действий осталось: {self.game_state.actions_left}")
            print(f"Рука: {len(self.game_state.hand)} карт")
            print(f"Выбранный ресурс: {self.game_state.selected_resource}")

            # Simulate some actions
            actions_this_day = 0
            max_actions = min(3, self.game_state.actions_left)

            # Try to play a card if available
            if self.game_state.hand and actions_this_day < max_actions:
                card_id = self.game_state.hand[0]
                card_data = self.cards_data.get(card_id, {})
                card_type = card_data.get("type", "")

                if card_type == "trade":
                    # Play market buy/sell
                    params = {
                        "resource_id": self.game_state.selected_resource,
                        "qty": 3,
                    }
                    action = PlayCardAction(card_id=card_id, params=params)
                    self.game_state = apply_action(
                        self.game_state, action, self.cards_data, self.events_data
                    )
                    actions_this_day += 1
                    print(f"  Играна карта: {card_data.get('name', card_id)}")

            # End day
            action = EndDayAction()
            self.game_state = apply_action(self.game_state, action, self.cards_data, self.events_data)
            day = self.game_state.day

            print(f"  День завершён")
            print()

            if self.game_state.player.gold < -200:
                print("БАНКРОТСТВО!")
                break
            if self.game_state.day > self.game_state.max_days:
                print("Игра завершена!")
                break

        print(f"\n=== Игра завершена на день {self.game_state.day} ===")
        print(f"Финальное золото: {self.game_state.player.gold}")
        print(f"Финальный долг: {self.game_state.player.debt}")
        print(f"Финальная репутация: {self.game_state.player.reputation}")


def test_ui_simulation():
    """Test UI simulation."""
    print("Тест: симуляция UI взаимодействий")

    # Load game data
    resources_json = load_json("data/resources.json")
    cards_json = load_json("data/cards.json")
    events_json = load_json("data/events.json")

    # Initialize game
    game_state = init_game(resources_json, cards_json, events_json, seed=12345)
    cards_dict = {card["id"]: card for card in cards_json["cards"]}

    # Create simulator
    simulator = UISimulator(game_state, cards_dict, events_json["events"])

    # Test resource selection
    print("1. Тест выбора ресурсов:")
    initial_resource = simulator.game_state.selected_resource
    simulator.simulate_key("DOWN")
    assert simulator.game_state.selected_resource != initial_resource, "Ресурс должен измениться"
    print("  ✓ Выбор ресурса работает")

    simulator.simulate_key("UP")
    assert simulator.game_state.selected_resource == initial_resource, "Ресурс должен вернуться"
    print("  ✓ Возврат к предыдущему ресурсу работает")

    # Test card playing
    print("\n2. Тест игры карт:")
    initial_gold = simulator.game_state.player.gold
    initial_actions = simulator.game_state.actions_left

    if simulator.game_state.hand:
        card_id = simulator.game_state.hand[0]
        card_data = cards_dict.get(card_id, {})
        if card_data.get("type") == "trade":
            params = {
                "resource_id": simulator.game_state.selected_resource,
                "qty": 1,
            }
            action = PlayCardAction(card_id=card_id, params=params)
            simulator.game_state = apply_action(
                simulator.game_state, action, cards_dict, events_json["events"]
            )
            assert simulator.game_state.actions_left < initial_actions, "Действие должно быть потрачено"
            print(f"  ✓ Карта {card_data.get('name', card_id)} сыграна")
            print(f"  ✓ Действий осталось: {simulator.game_state.actions_left}")

    # Test end day
    print("\n3. Тест завершения дня:")
    initial_day = simulator.game_state.day
    action = EndDayAction()
    simulator.game_state = apply_action(
        simulator.game_state, action, cards_dict, events_json["events"]
    )
    assert simulator.game_state.day > initial_day, "День должен увеличиться"
    assert simulator.game_state.actions_left == 3, "Действия должны восстановиться"
    print(f"  ✓ День завершён: {initial_day} -> {simulator.game_state.day}")
    print(f"  ✓ Действия восстановлены: {simulator.game_state.actions_left}")

    print("\n✓ Все UI тесты пройдены!\n")


def test_full_game_simulation():
    """Test full game simulation."""
    print("Тест: полная симуляция игры")

    # Load game data
    resources_json = load_json("data/resources.json")
    cards_json = load_json("data/cards.json")
    events_json = load_json("data/events.json")

    # Initialize game
    game_state = init_game(resources_json, cards_json, events_json, seed=54321)
    cards_dict = {card["id"]: card for card in cards_json["cards"]}

    # Create simulator
    simulator = UISimulator(game_state, cards_dict, events_json["events"])

    # Run simulation
    simulator.simulate_full_game(max_days=5)

    print("\n✓ Симуляция игры завершена!\n")


if __name__ == "__main__":
    # Initialize pygame (required for key constants)
    pygame.init()

    print("=" * 60)
    print("ТЕСТЫ СИМУЛЯЦИИ UI")
    print("=" * 60)

    test_ui_simulation()
    test_full_game_simulation()

    pygame.quit()
    print("Все тесты завершены!")

