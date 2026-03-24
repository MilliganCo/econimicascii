"""Run all tests."""

import sys
import os

# Add tests directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """Run all test suites."""
    print("=" * 60)
    print("ЗАПУСК ВСЕХ ТЕСТОВ")
    print("=" * 60)
    print()

    # Run basic tests
    print("1. Базовые тесты механики игры:")
    print("-" * 60)
    try:
        from tests.test_basic import (
            test_market_trade,
            test_market_evolution,
            test_event_application,
            test_deck_management,
        )
        test_market_trade()
        test_market_evolution()
        test_event_application()
        test_deck_management()
        print("✓ Базовые тесты пройдены\n")
    except Exception as e:
        print(f"✗ Ошибка в базовых тестах: {e}\n")
        import traceback
        traceback.print_exc()

    # Run card tests
    print("2. Тесты всех карт:")
    print("-" * 60)
    try:
        from tests.test_all_cards import (
            test_trade_cards,
            test_order_cards,
            test_contract_cards,
            test_risk_cards,
            test_infra_cards,
        )
        test_trade_cards()
        test_order_cards()
        test_contract_cards()
        test_risk_cards()
        test_infra_cards()
        print("✓ Тесты карт пройдены\n")
    except Exception as e:
        print(f"✗ Ошибка в тестах карт: {e}\n")
        import traceback
        traceback.print_exc()

    # Run UI simulation tests
    print("3. Тесты симуляции UI:")
    print("-" * 60)
    try:
        import pygame
        pygame.init()
        from tests.test_ui_simulation import test_ui_simulation, test_full_game_simulation
        test_ui_simulation()
        test_full_game_simulation()
        pygame.quit()
        print("✓ Тесты UI пройдены\n")
    except Exception as e:
        print(f"✗ Ошибка в тестах UI: {e}\n")
        import traceback
        traceback.print_exc()
        try:
            pygame.quit()
        except:
            pass

    print("=" * 60)
    print("ВСЕ ТЕСТЫ ЗАВЕРШЕНЫ")
    print("=" * 60)


if __name__ == "__main__":
    main()

