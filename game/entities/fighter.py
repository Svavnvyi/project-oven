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
        animations: dict[str, list[pygame.Surface]],
        animation_cooldown_ms: int = config.ANIMATION_COOLDOWN_MS,
    ) -> None:
        self.name = stats.name
        self.max_hp = stats.max_hp
        self.hp = stats.max_hp
        self.strength = stats.strength
        self.side = stats.side
        self.alive = True

        self.animations = animations
        self.state = "idle"
        self.frame_index = 0
        self.animation_cooldown_ms = animation_cooldown_ms
        self.update_time = pygame.time.get_ticks()

        self.image = self.animations[self.state][self.frame_index]
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)

    def is_attacking(self) -> bool:
        return self.state == "attack"

    def request_attack(self) -> bool:
        if self.is_attacking() or "attack" not in self.animations:
            return False
        self.state = "attack"
        self.frame_index = 0
        self.update_time = pygame.time.get_ticks()
        return True

    def update(self, now_ms: int) -> None:
        frames = self.animations[self.state]
        if now_ms - self.update_time > self.animation_cooldown_ms:
            self.update_time = now_ms
            self.frame_index += 1

        if self.frame_index >= len(frames):
            if self.is_attacking():
                self.state = "idle"
            self.frame_index = 0

        self.image = self.animations[self.state][self.frame_index]

    def draw(self, surface: pygame.Surface, clip_bottom_y: int | None = None) -> None:
        if not self.is_attacking() or clip_bottom_y is None:
            surface.blit(self.image, self.rect)
            return

        visible_height = clip_bottom_y - self.rect.top
        if visible_height <= 0:
            return

        if visible_height >= self.rect.height:
            surface.blit(self.image, self.rect)
            return

        source_rect = pygame.Rect(0, 0, self.rect.width, visible_height)
        target_rect = pygame.Rect(self.rect.left, self.rect.top, self.rect.width, visible_height)
        surface.blit(self.image, target_rect, source_rect)
