"""Fighter entity and animation state."""

from dataclasses import dataclass

import pygame

from game import config


@dataclass(frozen=True)
class FighterStats:
    name: str
    max_hp: int
    strength: int
    side: str


class Fighter:
    def __init__(
        self,
        *,
        x: int,
        y: int,
        stats: FighterStats,
        animations: list[pygame.Surface],
        animation_cooldown_ms: int = config.ANIMATION_COOLDOWN_MS,
    ) -> None:
        self.name = stats.name
        self.max_hp = stats.max_hp
        self.hp = stats.max_hp
        self.strength = stats.strength
        self.side = stats.side
        self.alive = True

        self.animation_frames = animations
        self.frame_index = 0
        self.animation_cooldown_ms = animation_cooldown_ms
        self.update_time = pygame.time.get_ticks()

        self.image = self.animation_frames[self.frame_index]
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)

    def update(self, now_ms: int) -> None:
        self.image = self.animation_frames[self.frame_index]
        if now_ms - self.update_time > self.animation_cooldown_ms:
            self.update_time = now_ms
            self.frame_index += 1

        if self.frame_index >= len(self.animation_frames):
            self.frame_index = 0

    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(self.image, self.rect)
