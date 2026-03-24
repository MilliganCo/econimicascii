"""Main entry point for Аэтерный Базар."""

import json
import os
import sys

from ui.pygame_app import GameApp, init_game


def load_json(path: str) -> dict:
    """Load JSON file."""
    base = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(base, path)
    with open(full_path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    """Main function."""
    try:
        # Load game data
        resources_json = load_json("data/resources.json")
        cards_json = load_json("data/cards.json")
        events_json = load_json("data/events.json")

        # Convert cards to dict
        cards_dict = {card["id"]: card for card in cards_json["cards"]}

        # Initialize game
        seed = 1337
        if len(sys.argv) > 1:
            try:
                seed = int(sys.argv[1])
            except ValueError:
                print(f"Неверный seed, используется {seed}")

        game_state = init_game(resources_json, cards_json, events_json, seed=seed)

        # Create and run app
        app = GameApp(game_state, cards_dict, events_json["events"])
        app.run()

    except FileNotFoundError as e:
        print(f"Ошибка: файл не найден - {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Ошибка: неверный JSON - {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

