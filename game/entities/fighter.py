"""Fighter entity and animation state."""

import random
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
        self.block_pending = False

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

    def is_dying(self) -> bool:
        return self.state == "death"

    def request_attack(self) -> bool:
        if (
            not self.alive
            or self.block_pending
            or self.is_attacking()
            or "attack" not in self.animations
        ):
            return False
        self.state = "attack"
        self.frame_index = 0
        self.update_time = pygame.time.get_ticks()
        return True

    def activate_block(self) -> bool:
        if not self.alive:
            return False
        self.block_pending = True
        # Freeze whichever frame is currently visible while block is active.
        return True

    @staticmethod
    def roll_attack_damage() -> int:
        return sum(
            random.randint(1, config.FRIDGE_DAMAGE_DICE_SIDES)
            for _ in range(config.FRIDGE_DAMAGE_DICE_COUNT)
        ) + config.FRIDGE_DAMAGE_FLAT_BONUS

    def take_damage(self, amount: int) -> None:
        if not self.alive:
            return
        incoming_damage = max(0, amount)
        if self.block_pending:
            incoming_damage = int((incoming_damage * 0.05) + 0.5)
            self.block_pending = False
        self.hp = max(0, self.hp - incoming_damage)
        if self.hp == 0:
            self.alive = False
            self.block_pending = False
            self.state = "death" if "death" in self.animations else "idle"
            self.frame_index = 0
            self.update_time = pygame.time.get_ticks()

    def update(self, now_ms: int) -> None:
        if self.alive and self.block_pending:
            self.image = self.animations[self.state][self.frame_index]
            return

        frames = self.animations[self.state]
        if now_ms - self.update_time > self.animation_cooldown_ms:
            self.update_time = now_ms
            self.frame_index += 1

        if self.frame_index >= len(frames):
            if self.is_dying():
                self.frame_index = len(frames) - 1
            elif self.is_attacking():
                self.state = "idle"
                self.frame_index = 0
            else:
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
