"""Main game orchestration: input, update, render."""

import pygame

from game import assets, config
from game.entities.fighter import Fighter, FighterStats
from game.ui.panel import draw_bottom_panel


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
        self.attack_button_rect: pygame.Rect | None = None
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
        return Fighter(
            x=self.ALLY_SPAWN_X,
            y=self.FIGHTER_SPAWN_Y,
            stats=stats,
            animations={"idle": idle_frames, "attack": attack_frames},
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
        return Fighter(
            x=self.OPPONENT_SPAWN_X,
            y=self.FIGHTER_SPAWN_Y,
            stats=stats,
            animations={"idle": idle_frames},
            animation_cooldown_ms=config.ANIMATION_COOLDOWN_MS,
        )

    def handle_input(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif (
                event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
                and self.attack_button_rect is not None
                and self.attack_button_rect.collidepoint(event.pos)
            ):
                self.ally_fighter.request_attack()

    def update(self) -> None:
        now_ms = pygame.time.get_ticks()
        for fighter in self.fighters:
            fighter.update(now_ms)

    def render(self) -> None:
        self.screen.blit(self.background_image, (0, 0))
        panel_top_y = config.SCREEN_HEIGHT - config.BOTTOM_PANEL_HEIGHT
        self.attack_button_rect = draw_bottom_panel(
            self.screen,
            self.panel_image,
            self.attack_button_image,
            config.SCREEN_HEIGHT,
            config.BOTTOM_PANEL_HEIGHT,
            config.ATTACK_BUTTON_LEFT,
            config.ATTACK_BUTTON_TOP,
        )
        for fighter in self.fighters:
            fighter.draw(self.screen, clip_bottom_y=panel_top_y)
        pygame.display.flip()

    def run(self) -> None:
        while self.running:
            self.clock.tick(config.FPS)
            self.handle_input()
            self.update()
            self.render()
        pygame.quit()
