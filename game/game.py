"""Main game orchestration: input, update, render."""

import random

import pygame

from game import assets, config
from game.entities.fighter import Fighter, FighterStats
from game.ui.healthbar import draw_healthbar, draw_cooldownbar
from game.ui.panel import draw_bottom_panel, AttackButton


class Game:
    ALLY_SPAWN_X = 100
    OPPONENT_SPAWN_X = 900
    FIGHTER_SPAWN_Y = 380

    def __init__(self) -> None:
        pygame.init()
        self.clock = pygame.time.Clock()
        self.screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        pygame.display.set_caption(config.WINDOW_TITLE)

        self.running = True
        self.background_image = assets.load_image(config.BACKGROUND_IMAGE_PATH)
        self.panel_image = assets.load_image(config.PANEL_IMAGE_PATH)
        self.attack_button_image = assets.load_image(config.ATTACK_BUTTON_IMAGE_PATH)
        self.attack_button_pressed_image = assets.load_image(
            config.ATTACK_BUTTON_PRESSED_IMAGE_PATH
        )
        self.attack_button2_image = assets.load_image(config.ATTACK_BUTTON2_IMAGE_PATH)
        self.attack_button2_pressed_image = assets.load_image(
            config.ATTACK_BUTTON2_PRESSED_IMAGE_PATH
        )
        self.block_button_image = assets.load_image(config.BLOCK_BUTTON_IMAGE_PATH)
        self.block_button_pressed_image = assets.load_image(
            config.BLOCK_BUTTON_PRESSED_IMAGE_PATH
        )
        self.attack_button_rects: list[pygame.Rect] = []
        self.pressed_button_index: int | None = None
        self.cursor_is_hand = False
        self.current_turn = config.ALLY_SIDE
        self.opponent_attack_due_ms = 0
        self.ally_attack2_cooldown_turns_remaining = 0
        self.ally_fighter = self._build_ally_fridge()
        self.opponent_fighter = self._build_opponent_fridge()
        self.fighters = [self.ally_fighter, self.opponent_fighter]

    def _build_ally_fridge(self) -> Fighter:
        stats = FighterStats(
            name="Fridge",
            max_hp=150,
            strength=20,
            side=config.ALLY_SIDE,
        )
        idle_frames = assets.load_animation_frames(
            side=stats.side,
            fighter_name=stats.name,
            folder_name=config.IDLE_ANIMATION_FOLDER,
            prefix=config.IDLE_ANIMATION_PREFIX,
            frame_count=config.IDLE_FRAMES,
            direction_suffix=config.RIGHT_FACING_SUFFIX,
            scale_multiplier=config.IDLE_SCALE_MULTIPLIER,
        )
        attack_frames = assets.load_animation_frames(
            side=stats.side,
            fighter_name=stats.name,
            folder_name=config.ATTACK_ANIMATION_FOLDER,
            prefix=config.ATTACK_ANIMATION_PREFIX,
            frame_count=config.ATTACK_FRAMES,
            direction_suffix=config.RIGHT_FACING_SUFFIX,
        )
        death_frames = assets.load_animation_frames(
            side=stats.side,
            fighter_name=stats.name,
            folder_name=config.DEATH_ANIMATION_FOLDER,
            prefix=config.DEATH_ANIMATION_FOLDER,
            frame_count=config.DEATH_FRAMES,
            direction_suffix=config.RIGHT_FACING_SUFFIX,
        )
        return Fighter(
            x=self.ALLY_SPAWN_X,
            y=self.FIGHTER_SPAWN_Y,
            stats=stats,
            animations={"idle": idle_frames, "attack": attack_frames, "death": death_frames},
            animation_cooldown_ms=config.ANIMATION_COOLDOWN_MS,
        )

    def _build_opponent_fridge(self) -> Fighter:
        stats = FighterStats(
            name="Fridge",
            max_hp=150,
            strength=20,
            side=config.OPPONENT_SIDE,
        )
        idle_frames = assets.load_animation_frames(
            side=stats.side,
            fighter_name=stats.name,
            folder_name=config.IDLE_ANIMATION_FOLDER,
            prefix=config.IDLE_ANIMATION_PREFIX,
            frame_count=config.IDLE_FRAMES,
            direction_suffix=config.LEFT_FACING_SUFFIX,
            scale_multiplier=config.IDLE_SCALE_MULTIPLIER,
        )
        attack_frames = assets.load_animation_frames(
            side=stats.side,
            fighter_name=stats.name,
            folder_name=config.ATTACK_ANIMATION_FOLDER,
            prefix=config.ATTACK_ANIMATION_PREFIX,
            frame_count=config.ATTACK_FRAMES,
            direction_suffix=config.LEFT_FACING_SUFFIX,
        )
        death_frames = assets.load_animation_frames(
            side=stats.side,
            fighter_name=stats.name,
            folder_name=config.DEATH_ANIMATION_FOLDER,
            prefix=config.DEATH_ANIMATION_FOLDER,
            frame_count=config.DEATH_FRAMES,
            direction_suffix=config.LEFT_FACING_SUFFIX,
        )
        return Fighter(
            x=self.OPPONENT_SPAWN_X,
            y=self.FIGHTER_SPAWN_Y,
            stats=stats,
            animations={"idle": idle_frames, "attack": attack_frames, "death": death_frames},
            animation_cooldown_ms=config.ANIMATION_COOLDOWN_MS,
        )

    def handle_input(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.pressed_button_index = None
                if not self._is_combat_active() or self.current_turn != config.ALLY_SIDE:
                    continue
                for index, button_rect in enumerate(self.attack_button_rects):
                    if button_rect.collidepoint(event.pos):
                        self.pressed_button_index = index
                        if index == 2:
                            if self.ally_fighter.activate_block():
                                self._handoff_to_opponent_turn()
                        elif index == 1:
                            if (
                                self.ally_attack2_cooldown_turns_remaining == 0
                                and self.ally_fighter.alive
                                and self.opponent_fighter.alive
                                and self.ally_fighter.request_attack()
                            ):
                                damage = self._roll_attack2_damage()
                                self.opponent_fighter.take_damage(damage)
                                self.ally_attack2_cooldown_turns_remaining = (
                                    config.ATTACK2_COOLDOWN_ALLY_TURNS
                                )
                                if self._is_combat_active():
                                    self._handoff_to_opponent_turn()
                        elif (
                            self.ally_fighter.alive
                            and self.opponent_fighter.alive
                            and self.ally_fighter.request_attack()
                        ):
                            damage = self.ally_fighter.roll_attack_damage()
                            self.opponent_fighter.take_damage(damage)
                            if self._is_combat_active():
                                self._handoff_to_opponent_turn()
                        break
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.pressed_button_index = None

    def update(self) -> None:
        now_ms = pygame.time.get_ticks()
        if (
            self._is_combat_active()
            and self.current_turn == config.OPPONENT_SIDE
            and now_ms >= self.opponent_attack_due_ms
        ):
            should_block = random.random() < config.OPPONENT_BLOCK_CHANCE
            if should_block:
                self.opponent_fighter.activate_block()
            elif self.opponent_fighter.request_attack():
                damage = self.opponent_fighter.roll_attack_damage()
                self.ally_fighter.take_damage(damage)
            if self._is_combat_active():
                self._handoff_to_ally_turn()
        for fighter in self.fighters:
            fighter.update(now_ms)

    def render(self) -> None:
        self.screen.blit(self.background_image, (0, 0))
        panel_top_y = config.SCREEN_HEIGHT - config.BOTTOM_PANEL_HEIGHT
        self.attack_button_rects = draw_bottom_panel(
            self.screen,
            self.panel_image,
            config.SCREEN_HEIGHT,
            config.BOTTOM_PANEL_HEIGHT,
            [
                AttackButton(
                    config.ATTACK_BUTTON_LEFT,
                    config.ATTACK_BUTTON_TOP,
                    self.attack_button_image,
                    self.attack_button_pressed_image,
                    self.pressed_button_index == 0,
                    config.ATTACK_BUTTON_SCALE,
                ),
                AttackButton(
                    config.ATTACK_BUTTON2_LEFT,
                    config.ATTACK_BUTTON2_TOP,
                    self.attack_button2_image,
                    self.attack_button2_pressed_image,
                    self.pressed_button_index == 1,
                    config.ATTACK_BUTTON2_SCALE,
                ),
                AttackButton(
                    config.BLOCK_BUTTON_LEFT,
                    config.BLOCK_BUTTON_TOP,
                    self.block_button_image,
                    self.block_button_pressed_image,
                    self.pressed_button_index == 2,
                    config.BLOCK_BUTTON_SCALE,
                ),
            ],
        )
        self._update_hover_cursor()
        for fighter in self.fighters:
            fighter.draw(self.screen, clip_bottom_y=panel_top_y)
            offset_x = (
                config.HEALTHBAR_OFFSET_X + 10
                if fighter.side == config.ALLY_SIDE
                else -config.HEALTHBAR_OFFSET_X - 40
            )
            draw_healthbar(
                self.screen,
                fighter_rect=fighter.rect,
                hp=fighter.hp,
                max_hp=fighter.max_hp,
                width=config.HEALTHBAR_WIDTH,
                height=config.HEALTHBAR_HEIGHT,
                offset_x=offset_x,
                offset_y=config.HEALTHBAR_OFFSET_Y,
                border_color=config.HEALTHBAR_BORDER_COLOR,
                empty_color=config.HEALTHBAR_EMPTY_COLOR,
                fill_color=config.HEALTHBAR_FILL_COLOR,
            )
            if fighter.side == config.ALLY_SIDE:
                draw_cooldownbar(
                    self.screen,
                    fighter_rect=fighter.rect,
                    ratio=self._get_attack2_cooldown_ratio(),
                    width=config.HEALTHBAR_WIDTH,
                    height=config.COOLDOWNBAR_HEIGHT,
                    offset_x=offset_x,
                    offset_y=(
                        config.HEALTHBAR_OFFSET_Y
                        + config.HEALTHBAR_HEIGHT
                        + config.COOLDOWNBAR_OFFSET_Y
                    ),
                    border_color=config.COOLDOWNBAR_BORDER_COLOR,
                    empty_color=config.COOLDOWNBAR_EMPTY_COLOR,
                    fill_color=config.COOLDOWNBAR_FILL_COLOR,
                )
        self._draw_turn_indicator()
        pygame.display.flip()

    def _update_hover_cursor(self) -> None:
        mouse_position = pygame.mouse.get_pos()
        should_use_hand = any(
            button_rect.collidepoint(mouse_position) for button_rect in self.attack_button_rects
        )
        if should_use_hand == self.cursor_is_hand:
            return
        try:
            cursor_type = (
                pygame.SYSTEM_CURSOR_HAND
                if should_use_hand
                else pygame.SYSTEM_CURSOR_ARROW
            )
            pygame.mouse.set_cursor(cursor_type)
            self.cursor_is_hand = should_use_hand
        except pygame.error:
            # Keep gameplay running if system cursor switching is unsupported.
            return

    def _draw_turn_indicator(self) -> None:
        left = config.TURN_INDICATOR_LEFT
        top = config.TURN_INDICATOR_TOP
        size = config.TURN_INDICATOR_SIZE
        line_width = config.TURN_INDICATOR_LINE_WIDTH

        if self.current_turn == config.ALLY_SIDE:
            color = config.TURN_INDICATOR_TICK_COLOR
            pygame.draw.line(
                self.screen,
                color,
                (left, top + int(size * 0.6)),
                (left + int(size * 0.35), top + size),
                line_width,
            )
            pygame.draw.line(
                self.screen,
                color,
                (left + int(size * 0.35), top + size),
                (left + size, top),
                line_width,
            )
            return

        color = config.TURN_INDICATOR_X_COLOR
        pygame.draw.line(
            self.screen,
            color,
            (left, top),
            (left + size, top + size),
            line_width,
        )
        pygame.draw.line(
            self.screen,
            color,
            (left + size, top),
            (left, top + size),
            line_width,
        )

    def _handoff_to_opponent_turn(self) -> None:
        self.current_turn = config.OPPONENT_SIDE
        self.opponent_attack_due_ms = pygame.time.get_ticks() + config.OPPONENT_ATTACK_INTERVAL_MS

    def _handoff_to_ally_turn(self) -> None:
        self.current_turn = config.ALLY_SIDE
        if self.ally_attack2_cooldown_turns_remaining > 0:
            self.ally_attack2_cooldown_turns_remaining -= 1

    def _roll_attack2_damage(self) -> int:
        return sum(
            random.randint(1, config.ATTACK2_DAMAGE_DICE_SIDES)
            for _ in range(config.ATTACK2_DAMAGE_DICE_COUNT)
        ) + config.ATTACK2_DAMAGE_FLAT_BONUS

    def _get_attack2_cooldown_ratio(self) -> float:
        if config.ATTACK2_COOLDOWN_ALLY_TURNS <= 0:
            return 1.0
        remaining = max(0, self.ally_attack2_cooldown_turns_remaining)
        return max(
            0.0,
            min(
                1.0,
                (config.ATTACK2_COOLDOWN_ALLY_TURNS - remaining)
                / config.ATTACK2_COOLDOWN_ALLY_TURNS,
            ),
        )

    def _is_combat_active(self) -> bool:
        return self.ally_fighter.alive and self.opponent_fighter.alive

    def run(self) -> None:
        while self.running:
            self.clock.tick(config.FPS)
            self.handle_input()
            self.update()
            self.render()
        pygame.quit()
