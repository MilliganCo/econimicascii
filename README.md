# Аэтерный Базар

> Public source preview: see [PUBLICATION.md](PUBLICATION.md) for actual checks, known failures and runtime limits.

Карточная экономическая стратегия в фэнтези-сеттинге. Ты играешь трейдером на рынке редких товаров, где твои крупные сделки влияют на цены.

## Особенности

- **6 ресурсов** с уникальными характеристиками рынка
- **30 карт** различных типов: торговля, контракты, риск-менеджмент, инфраструктура
- **Реагирующий рынок**: твои сделки влияют на цены через проскальзывание и impact
- **События дня**: случайные события меняют рынок каждый день
- **ASCII интерфейс**: классический терминальный вид

## Установка

1. Установите зависимости:
```bash
pip install pygame-ce
```

Или используйте зависимости из `pyproject.toml`:
```bash
pip install -e .
```

## Запуск

```bash
python main.py
```

Можно указать seed для воспроизводимости:
```bash
python main.py 12345
```

## Управление

- **↑/↓** - выбор ресурса
- **1-9** - игра карты из руки
- **Enter** - подтвердить действие
- **E** - завершить день
- **Q** - выход

## Цель игры

Выжить 30 дней, не обанкротившись. Управляй обязательствами (аренда, проценты), выполняй контракты и используй карты для максимизации прибыли.

## Тестирование

Запуск всех тестов:
```bash
python run_tests.py
```

Или отдельные тесты:
```bash
python tests/test_basic.py          # Базовые тесты механики
python tests/test_all_cards.py     # Тесты всех карт
python tests/test_ui_simulation.py  # Симуляция UI взаимодействий
```

## Структура проекта

- `core/` - игровая логика (без UI)
- `ui/` - pygame ASCII интерфейс
- `data/` - JSON файлы с данными (ресурсы, карты, события)
- `tests/` - тестовые файлы
- `main.py` - точка входа
- `run_tests.py` - запуск всех тестов

## Лицензия

MIT



## Public source status — 2026-10-29

See [PUBLICATION.md](PUBLICATION.md) for the current verification scope, prototype limitations and runtime boundaries. Earlier audit checklists describe historical work.
