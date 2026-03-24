"""Main pygame application."""

from typing import Any, Dict, List, Optional

import pygame

from core.actions import Action, DrawCardsAction, EndDayAction, PlayCardAction, SelectResourceAction
from core.deck import init_deck
from core.reducer import apply_action
from core.state import GameState, PlayerState, Resource, ResourceId
from core.rng import Rng

from .render import render_game


class GameApp:
    """Main game application."""

    def __init__(self, game_state: GameState, cards_data: Dict[str, Dict], events_data: List[Dict]):
        self.game_state = game_state
        self.cards_data = cards_data
        self.events_data = events_data
        self.selected_card_idx = -1
        self.input_mode: Optional[str] = None  # "qty", "price", "resource"
        self.input_buffer = ""
        self.input_params: Dict[str, Any] = {}

        pygame.init()
        pygame.display.set_caption("Аэтерный Базар (ASCII)")
        self.font = pygame.font.SysFont("Consolas", 16) or pygame.font.SysFont("Courier New", 16)
        self.char_w, _ = self.font.size("M")
        self.line_h = self.font.get_linesize()

        from .ascii_grid import H, W

        self.screen = pygame.display.set_mode((W * self.char_w, H * self.line_h))
        self.clock = pygame.time.Clock()

    def run(self) -> None:
        """Main game loop."""
        running = True

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    action = self._handle_key(event.key)
                    if action:
                        self.game_state = apply_action(
                            self.game_state, action, self.cards_data, self.events_data
                        )

                        # Check win/lose conditions
                        if self.game_state.player.gold < -200:
                            self.game_state = self._add_log(
                                self.game_state, "БАНКРОТСТВО: золото слишком низкое."
                            )
                        if self.game_state.day > self.game_state.max_days:
                            self.game_state = self._add_log(
                                self.game_state, "КОНЕЦ: ты пережил сезон базара."
                            )

            self._render()
            self.clock.tick(30)

        pygame.quit()

    def _handle_key(self, key: int) -> Optional[Action]:
        """Handle keyboard input."""
        if self.input_mode:
            return self._handle_input_mode(key)

        # Resource selection
        if key == pygame.K_UP:
            idx = self._get_resource_index(self.game_state.selected_resource)
            rids = list(self.game_state.market.resources.keys())
            new_idx = (idx - 1) % len(rids)
            return SelectResourceAction(resource_id=rids[new_idx])

        if key == pygame.K_DOWN:
            idx = self._get_resource_index(self.game_state.selected_resource)
            rids = list(self.game_state.market.resources.keys())
            new_idx = (idx + 1) % len(rids)
            return SelectResourceAction(resource_id=rids[new_idx])

        # Card selection
        if pygame.K_1 <= key <= pygame.K_9:
            card_idx = key - pygame.K_1
            if card_idx < len(self.game_state.hand):
                self.selected_card_idx = card_idx
                card_id = self.game_state.hand[card_idx]
                return self._prepare_card_action(card_id)

        # End day
        if key == pygame.K_e:
            return EndDayAction()

        # Quit
        if key == pygame.K_q:
            return None  # Will exit in main loop

        return None

    def _get_resource_index(self, rid: ResourceId) -> int:
        """Get index of resource in list."""
        rids = list(self.game_state.market.resources.keys())
        return rids.index(rid) if rid in rids else 0

    def _prepare_card_action(self, card_id: str) -> Optional[Action]:
        """Prepare card action based on card type."""
        card_data = self.cards_data.get(card_id, {})
        card_type = card_data.get("type", "")

        # Simple cards that don't need input
        if card_type in ("info", "risk", "finance", "infra", "modifier"):
            # Some cards need resource selection
            if card_type == "influence":
                params = {"resource_id": self.game_state.selected_resource}
            else:
                params = {}
            return PlayCardAction(card_id=card_id, params=params)

        # Trade cards need quantity
        if card_type == "trade":
            self.input_mode = "qty"
            self.input_buffer = ""
            self.input_params = {"resource_id": self.game_state.selected_resource}
            return None  # Will be handled in input mode

        # Order cards need quantity and price
        if card_type == "order":
            self.input_mode = "qty"
            self.input_buffer = ""
            self.input_params = {"resource_id": self.game_state.selected_resource}
            return None

        # Contract cards are simple
        if card_type == "contract":
            return PlayCardAction(card_id=card_id, params={})

        return None

    def _handle_input_mode(self, key: int) -> Optional[Action]:
        """Handle input mode for card parameters."""
        if key == pygame.K_RETURN or key == pygame.K_KP_ENTER:
            # Confirm input
            try:
                value = int(self.input_buffer) if self.input_buffer else 0
                if self.input_mode == "qty":
                    self.input_params["qty"] = value
                    card_id = self.game_state.hand[self.selected_card_idx]
                    card_data = self.cards_data.get(card_id, {})
                    if card_data.get("type") == "order":
                        # Need price input
                        self.input_mode = "price"
                        self.input_buffer = ""
                        return None
                    else:
                        # Trade card, ready to play
                        self.input_mode = None
                        return PlayCardAction(card_id=card_id, params=self.input_params)
                elif self.input_mode == "price":
                    self.input_params["limit_price"] = float(value)
                    card_id = self.game_state.hand[self.selected_card_idx]
                    self.input_mode = None
                    return PlayCardAction(card_id=card_id, params=self.input_params)
            except ValueError:
                pass
            self.input_mode = None
            return None

        if key == pygame.K_ESCAPE:
            self.input_mode = None
            self.input_buffer = ""
            self.input_params = {}
            return None

        # Number input
        if pygame.K_0 <= key <= pygame.K_9:
            self.input_buffer += chr(key)
            return None

        if key == pygame.K_BACKSPACE:
            self.input_buffer = self.input_buffer[:-1]
            return None

        return None

    def _render(self) -> None:
        """Render game to screen."""
        self.screen.fill((0, 0, 0))

        lines = render_game(self.game_state, self.cards_data, self.selected_card_idx)

        # Show input prompt if in input mode
        if self.input_mode:
            prompt = f"Введите {self.input_mode}: {self.input_buffer}_"
            lines[-1] = prompt[:120]

        for i, line in enumerate(lines):
            surf = self.font.render(line, True, (220, 220, 220))
            self.screen.blit(surf, (0, i * self.line_h))

        pygame.display.flip()

    def _add_log(self, state: GameState, msg: str) -> GameState:
        """Add message to log."""
        from dataclasses import replace
        return replace(state, log=[msg] + state.log)


def init_game(
    resources_json: Dict, cards_json: Dict, events_json: List[Dict], seed: int = 12345
) -> GameState:
    """Initialize game state from JSON data."""
    from dataclasses import replace

    from core.deck import init_deck
    from core.state import MarketState, Resource

    resources: Dict[ResourceId, Resource] = {}
    history: Dict[ResourceId, List[float]] = {}

    for r in resources_json["resources"]:
        rr = Resource(
            id=r["id"],
            name=r["name"],
            price=float(r["price"]),
            fundamental=float(r.get("fundamental", r["price"])),
            liquidity=float(r["liquidity"]),
            volatility=float(r["volatility"]),
            decay=float(r.get("decay", 0.0)),
        )
        resources[rr.id] = rr
        history[rr.id] = [rr.price]

    market = MarketState(resources=resources, history=history)

    inv = {rid: 0 for rid in resources.keys()}
    player = PlayerState(
        gold=500, debt=200, reputation=0, storage_cap=40, daily_overhead=10, inventory=inv
    )

    selected = list(resources.keys())[0]

    # Initialize deck
    cards_dict = {card["id"]: card for card in cards_json["cards"]}
    deck = init_deck(cards_dict)
    rng = Rng(seed)
    rng.shuffle(deck)

    # Draw initial hand
    from core.deck import draw_cards

    deck, hand, discard = draw_cards(deck, [], [], player.hand_size, rng)

    game = GameState(
        seed=seed,
        day=1,
        max_days=30,
        actions_left=3,
        selected_resource=selected,
        player=player,
        market=market,
        hand=hand,
        deck=deck,
        discard=discard,
        log=["Добро пожаловать на Аэтерный Базар."],
    )
    return game

