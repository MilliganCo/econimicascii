"""ASCII grid rendering utilities."""

from typing import List


W = 120  # Grid width in characters
H = 40   # Grid height in characters


def new_grid() -> List[List[str]]:
    """Create new empty grid."""
    return [[" "] * W for _ in range(H)]


def put_text(grid: List[List[str]], x: int, y: int, s: str) -> None:
    """Put text at position (x, y) in grid."""
    if y < 0 or y >= H:
        return
    for i, ch in enumerate(s):
        xx = x + i
        if 0 <= xx < W:
            grid[y][xx] = ch


def draw_rect(grid: List[List[str]], x: int, y: int, w: int, h: int, title: str | None = None) -> None:
    """Draw rectangle border with optional title."""
    if w < 2 or h < 2:
        return
    # Top/bottom
    put_text(grid, x, y, "+" + "-" * (w - 2) + "+")
    put_text(grid, x, y + h - 1, "+" + "-" * (w - 2) + "+")
    # Sides
    for yy in range(y + 1, y + h - 1):
        put_text(grid, x, yy, "|")
        put_text(grid, x + w - 1, yy, "|")
    if title:
        t = f"[{title}]"
        put_text(grid, x + 2, y, t[: max(0, w - 4)])


def sparkline_chart(values: List[float], width: int, height: int) -> List[str]:
    """
    Generate ASCII sparkline chart.

    Args:
        values: List of price values
        width: Chart width in characters
        height: Chart height in characters

    Returns:
        List of strings (lines) representing the chart
    """
    if width <= 2 or height <= 2:
        return [" " * width for _ in range(height)]

    if not values:
        return [" " * width for _ in range(height)]

    # Sample last `width-2` points
    plot_w = width - 2
    src = values[-plot_w:]
    if len(src) < plot_w:
        src = [src[0]] * (plot_w - len(src)) + src if src else [0.0] * plot_w

    lo = min(src)
    hi = max(src)
    if hi - lo < 1e-9:
        hi = lo + 1.0

    canvas = [[" "] * width for _ in range(height)]
    # Bottom axis
    for x in range(width):
        canvas[height - 1][x] = "-"
    canvas[height - 1][0] = "+"
    canvas[height - 1][width - 1] = "+"

    # Plot points
    for i, v in enumerate(src):
        t = (v - lo) / (hi - lo) if hi > lo else 0.0
        yy = (height - 2) - int(round(t * (height - 2)))
        xx = 1 + i
        if 0 <= yy < height - 1 and 0 <= xx < width - 1:
            canvas[yy][xx] = "*"

    return ["".join(row) for row in canvas]


def grid_to_lines(grid: List[List[str]]) -> List[str]:
    """Convert grid to list of strings."""
    return ["".join(row) for row in grid]

