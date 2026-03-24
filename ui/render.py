"""Render game state to ASCII grid."""

from typing import Dict, List

from core.state import GameState

from .ascii_grid import W, draw_rect, grid_to_lines, new_grid, put_text, sparkline_chart


def render_game(game: GameState, cards_data: Dict[str, Dict], selected_card_idx: int = -1) -> List[str]:
    """
    Render complete game state to ASCII lines.

    Args:
        game: Current game state
        cards_data: Cards data for display names
        selected_card_idx: Index of selected card in hand (-1 if none)

    Returns:
        List of strings (lines) to display
    """
    grid = new_grid()

    # Header
    header = (
        f"АЭТЕРНЫЙ БАЗАР  |  День {game.day}/{game.max_days}  |  "
        f"Золото: {game.player.gold}  Долг: {game.player.debt}  Реп: {game.player.reputation}  "
        f"Действия: {game.actions_left}"
    )
    put_text(grid, 0, 0, header[:W])
    controls = (
        "Up/Down: ресурс  |  1-9: карта  |  Enter: подтвердить  |  E: день  |  Q: выход"
    )
    put_text(grid, 0, 1, controls[:W])

    # Panels
    draw_rect(grid, 0, 3, 44, 18, "Рынок")
    draw_rect(grid, 44, 3, 46, 18, "График")
    draw_rect(grid, 90, 3, 30, 18, "Рука")
    draw_rect(grid, 0, 21, 90, 8, "Позиции")
    draw_rect(grid, 0, 29, 120, 11, "Лог")

    # Market table
    _render_market_table(grid, game)

    # Chart
    _render_chart(grid, game)

    # Hand
    _render_hand(grid, game, cards_data, selected_card_idx)

    # Positions (orders and contracts)
    _render_positions(grid, game)

    # Log
    _render_log(grid, game)

    return grid_to_lines(grid)


def _render_market_table(grid: List[List[str]], game: GameState) -> None:
    """Render market resource table."""
    lines = []
    lines.append("ID            Цена   Δ    Ликв   Вол   Инв")
    lines.append("-" * 42)

    for rid, r in game.market.resources.items():
        hist = game.market.history.get(rid, [])
        delta = 0.0
        if len(hist) >= 2:
            delta = hist[-1] - hist[-2]
        inv = game.player.inventory.get(rid, 0)
        sel = ">" if rid == game.selected_resource else " "
        lines.append(
            f"{sel}{rid:<12} {r.price:>6.0f} {delta:>+5.0f} {r.liquidity:>6.0f} {r.volatility:>5.3f} {inv:>4}"
        )

    x0, y0 = 2, 5
    for i, s in enumerate(lines[:14]):
        put_text(grid, x0, y0 + i, s[:40])


def _render_chart(grid: List[List[str]], game: GameState) -> None:
    """Render price chart for selected resource."""
    sel = game.market.resources[game.selected_resource]
    hist = game.market.history.get(game.selected_resource, [])
    title = (
        f"{sel.name} ({game.selected_resource})  "
        f"P={sel.price:.0f}  F={sel.fundamental:.0f}  L={sel.liquidity:.0f}"
    )
    put_text(grid, 46, 5, title[:42])

    chart = sparkline_chart(hist[-80:], width=42, height=12)
    for i, row in enumerate(chart):
        put_text(grid, 46, 7 + i, row)


def _render_hand(grid: List[List[str]], game: GameState, cards_data: Dict[str, Dict], selected_idx: int) -> None:
    """Render hand of cards."""
    x0, y0 = 92, 5
    put_text(grid, x0, y0, "Рука карт:")
    y0 += 1

    for i, card_id in enumerate(game.hand[:9]):  # Show up to 9 cards
        card_data = cards_data.get(card_id, {})
        card_name = card_data.get("name", card_id)
        marker = ">" if i == selected_idx else f"{i+1}"
        line = f"{marker} {card_name[:24]}"
        put_text(grid, x0, y0 + i, line)

    if len(game.hand) > 9:
        put_text(grid, x0, y0 + 9, f"... и ещё {len(game.hand) - 9}")


def _render_positions(grid: List[List[str]], game: GameState) -> None:
    """Render limit orders and contracts."""
    x0, y0 = 2, 23
    put_text(grid, x0, y0, "Лимитные ордера:")
    y0 += 1

    if not game.limit_orders:
        put_text(grid, x0, y0, "  (нет)")
    else:
        for i, order in enumerate(game.limit_orders[:5]):
            direction = "Покупка" if order.direction == 1 else "Продажа"
            line = (
                f"  {direction} {order.qty}x {order.resource} "
                f"@ {order.limit_price:.0f} (TTL: {order.ttl})"
            )
            put_text(grid, x0, y0 + i, line[:86])

    y0 = 23 + 4
    put_text(grid, x0, y0, "Контракты:")
    y0 += 1

    if not game.contracts:
        put_text(grid, x0, y0, "  (нет)")
    else:
        for i, contract in enumerate(game.contracts[:5]):
            req_str = ", ".join(f"{k}:{v}" for k, v in list(contract.requirements.items())[:2])
            if len(contract.requirements) > 2:
                req_str += "..."
            line = f"  {contract.name[:20]} ({req_str}) {contract.days_left}д"
            put_text(grid, x0, y0 + i, line[:86])


def _render_log(grid: List[List[str]], game: GameState) -> None:
    """Render game log."""
    x0, y0 = 2, 31
    for i, msg in enumerate(game.log[:9]):
        put_text(grid, x0, y0 + i, msg[:116])

