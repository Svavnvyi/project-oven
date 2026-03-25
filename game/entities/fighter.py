"""Fighter entity and animation state."""

import random
from dataclasses import dataclass

import pygame

from game import config, sfx


@dataclass(frozen=True)
class AttackDamageSpec:
    """Sum of `dice_count` dice with `dice_sides` each, plus flat bonus."""

    dice_count: int
    dice_sides: int
    flat_bonus: int

    def roll(self) -> int:
        return (
            sum(random.randint(1, self.dice_sides) for _ in range(self.dice_count))
            + self.flat_bonus
        )


@dataclass(frozen=True)
class FighterStats:
    name: str
    max_hp: int
    strength: int
    side: str
    initiative: int
    attack1: AttackDamageSpec
    attack2: AttackDamageSpec


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
        self.initiative = stats.initiative
        self._stats = stats
        self.alive = True
        self.block_pending = False
        self.block_phase: str | None = None
        self.block_hold_start_ms = 0

        self.animations = animations
        self.state = "idle"
        self.frame_index = 0
        self.animation_cooldown_ms = animation_cooldown_ms
        self.update_time = pygame.time.get_ticks()

        self.image = self.animations[self.state][self.frame_index]
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.death_animation_finished = False
        self.visual_scale = 1.0
        self._fridge_attack2_visual = False
        self._fridge_attack2_start_ms = 0
        self._fridge_attack2_ramp_down = False
        self._fridge_attack2_ramp_down_start_ms = 0
        self._fridge_attack2_scale_at_attack_end = 1.0
        self._fridge_attack2_windup = False
        self._attack_animation_key = "attack"

    def is_attacking(self) -> bool:
        return self.state == "attack"

    def is_dying(self) -> bool:
        return self.state == "death"

    def _exit_block_animation(self) -> None:
        if self.state == "block":
            self.state = "idle"
            self.frame_index = 0
            self.block_phase = None
            idle = self.animations["idle"][0]
            c = self.rect.center
            self.image = idle
            self.rect = idle.get_rect(center=c)

    def request_attack(
        self,
        *,
        fridge_attack2_visual: bool = False,
        attack_animation_key: str = "attack",
        is_attack2: bool = False,
    ) -> bool:
        if (
            not self.alive
            or self.is_attacking()
            or self._fridge_attack2_windup
            or attack_animation_key not in self.animations
        ):
            return False
        self.block_pending = False
        self._exit_block_animation()
        self._fridge_attack2_ramp_down = False
        self._fridge_attack2_windup = False
        self._fridge_attack2_visual = False
        self.visual_scale = 1.0
        self.update_time = pygame.time.get_ticks()
        if fridge_attack2_visual and self.name == "Fridge":
            self._fridge_attack2_windup = True
            self._fridge_attack2_visual = True
            self._fridge_attack2_start_ms = pygame.time.get_ticks()
            self.state = "idle"
            self.frame_index = 0
            sfx.play_character_action(self.name, "attack2")
            return True
        self._attack_animation_key = attack_animation_key
        self.state = "attack"
        self.frame_index = 0
        sfx.play_character_action(
            self.name, "attack2" if is_attack2 else "attack"
        )
        return True

    def activate_block(self) -> bool:
        if (
            not self.alive
            or self.is_attacking()
            or self._fridge_attack2_windup
            or self.block_pending
        ):
            return False
        self.block_pending = True
        if "block" in self.animations:
            self.state = "block"
            self.frame_index = 0
            self.block_phase = "forward"
            self.update_time = pygame.time.get_ticks()
        sfx.play_character_action(self.name, "block")
        return True

    def roll_attack1_damage(self) -> int:
        return self._stats.attack1.roll()

    def roll_attack2_damage(self) -> int:
        return self._stats.attack2.roll()

    def take_damage(self, amount: int) -> None:
        if not self.alive:
            return
        incoming_damage = max(0, amount)
        was_blocking = self.block_pending
        if self.block_pending:
            incoming_damage = int((incoming_damage * 0.05) + 0.5)
            self.block_pending = False
        self.hp = max(0, self.hp - incoming_damage)
        if self.hp == 0:
            self.alive = False
            self.block_pending = False
            self.block_phase = None
            self._fridge_attack2_visual = False
            self._fridge_attack2_ramp_down = False
            self._fridge_attack2_windup = False
            self.visual_scale = 1.0
            self._attack_animation_key = "attack"
            if "death" in self.animations:
                self.state = "death"
                self.death_animation_finished = False
            else:
                self.state = "idle"
                self.death_animation_finished = True
            self.frame_index = 0
            self.update_time = pygame.time.get_ticks()
        elif was_blocking:
            self._exit_block_animation()

    def _update_block_animation(self, now_ms: int) -> None:
        frames = self.animations["block"]
        last_i = len(frames) - 1
        assert self.block_phase is not None

        if self.block_phase == "forward":
            if now_ms - self.update_time > self.animation_cooldown_ms:
                self.update_time = now_ms
                if self.frame_index < last_i:
                    self.frame_index += 1
                if self.frame_index == last_i:
                    self.block_phase = "hold"
                    self.block_hold_start_ms = now_ms
            surf = frames[self.frame_index]
            c = self.rect.center
            self.image = surf
            self.rect = surf.get_rect(center=c)
            return

        if self.block_phase == "hold":
            surf = frames[last_i]
            c = self.rect.center
            self.image = surf
            self.rect = surf.get_rect(center=c)
            if now_ms - self.block_hold_start_ms >= config.BLOCK_HOLD_MS:
                self.block_phase = "reverse"
                self.update_time = now_ms
            return

        if self.block_phase == "reverse":
            if now_ms - self.update_time > self.animation_cooldown_ms:
                self.update_time = now_ms
                if self.frame_index > 0:
                    self.frame_index -= 1
                else:
                    self.state = "idle"
                    self.frame_index = 0
                    self.block_phase = None
                    self.block_pending = False
                    idle = self.animations["idle"][0]
                    c = self.rect.center
                    self.image = idle
                    self.rect = idle.get_rect(center=c)
                    return
            surf = frames[self.frame_index]
            c = self.rect.center
            self.image = surf
            self.rect = surf.get_rect(center=c)

    def _fridge_attack2_scale_now(self, now_ms: int) -> float:
        ms = config.FRIDGE_ATTACK2_SCALE_RAMP_MS
        t = min(1.0, (now_ms - self._fridge_attack2_start_ms) / ms)
        cap = config.FRIDGE_ATTACK2_VISUAL_SCALE_MAX
        return min(cap, 1.0 + (cap - 1.0) * t)

    def _update_fridge_attack2_visual_scale(self, now_ms: int) -> None:
        if self._fridge_attack2_ramp_down:
            elapsed = now_ms - self._fridge_attack2_ramp_down_start_ms
            ms = config.FRIDGE_ATTACK2_SCALE_RAMP_MS
            if elapsed >= ms:
                self._fridge_attack2_ramp_down = False
                self.visual_scale = 1.0
            else:
                a = self._fridge_attack2_scale_at_attack_end
                self.visual_scale = a + (1.0 - a) * (elapsed / ms)
            return
        if self._fridge_attack2_windup:
            self.visual_scale = self._fridge_attack2_scale_now(now_ms)
            return
        if self.is_attacking() and self._fridge_attack2_visual:
            self.visual_scale = config.FRIDGE_ATTACK2_VISUAL_SCALE_MAX
            return
        self.visual_scale = 1.0

    def _scaled_draw_surfaces(self) -> tuple[pygame.Surface, pygame.Rect]:
        sc = self.visual_scale
        if abs(sc - 1.0) < 1e-4:
            return self.image, self.rect
        w, h = self.image.get_size()
        nw = max(1, int(round(w * sc)))
        nh = max(1, int(round(h * sc)))
        surf = pygame.transform.smoothscale(self.image, (nw, nh))
        r = surf.get_rect(center=self.rect.center)
        return surf, r

    def update(self, now_ms: int) -> None:
        if self._fridge_attack2_windup:
            frames = self.animations["idle"]
            if now_ms - self.update_time > self.animation_cooldown_ms:
                self.update_time = now_ms
                self.frame_index += 1
            if self.frame_index >= len(frames):
                self.frame_index = 0
            self.image = frames[self.frame_index]
            self._update_fridge_attack2_visual_scale(now_ms)
            if now_ms - self._fridge_attack2_start_ms >= config.FRIDGE_ATTACK2_SCALE_RAMP_MS:
                self._fridge_attack2_windup = False
                self.visual_scale = config.FRIDGE_ATTACK2_VISUAL_SCALE_MAX
                self._attack_animation_key = "attack"
                self.state = "attack"
                self.frame_index = 0
                self.update_time = now_ms
                self.image = self.animations[self._attack_animation_key][0]
            return

        if self.alive and self.block_pending and not self.is_attacking():
            if self.state == "block" and "block" in self.animations:
                self._update_block_animation(now_ms)
                self._update_fridge_attack2_visual_scale(now_ms)
                return
            self.image = self.animations[self.state][self.frame_index]
            self._update_fridge_attack2_visual_scale(now_ms)
            return

        frames = (
            self.animations[self._attack_animation_key]
            if self.state == "attack"
            else self.animations[self.state]
        )
        if now_ms - self.update_time > self.animation_cooldown_ms:
            self.update_time = now_ms
            self.frame_index += 1

        if self.frame_index >= len(frames):
            if self.is_dying():
                self.frame_index = len(frames) - 1
                self.death_animation_finished = True
            elif self.is_attacking():
                if self._fridge_attack2_visual:
                    self._fridge_attack2_scale_at_attack_end = (
                        config.FRIDGE_ATTACK2_VISUAL_SCALE_MAX
                    )
                    self._fridge_attack2_ramp_down = True
                    self._fridge_attack2_ramp_down_start_ms = now_ms
                    self._fridge_attack2_visual = False
                self.state = "idle"
                self.frame_index = 0
                self._attack_animation_key = "attack"
            else:
                self.frame_index = 0

        if self.state == "attack":
            self.image = self.animations[self._attack_animation_key][self.frame_index]
        else:
            self.image = self.animations[self.state][self.frame_index]
        self._update_fridge_attack2_visual_scale(now_ms)

    def draw(self, surface: pygame.Surface, clip_bottom_y: int | None = None) -> None:
        surf, draw_rect = self._scaled_draw_surfaces()
        if not self.is_attacking() or clip_bottom_y is None:
            surface.blit(surf, draw_rect)
            return

        visible_height = clip_bottom_y - draw_rect.top
        if visible_height <= 0:
            return

        if visible_height >= draw_rect.height:
            surface.blit(surf, draw_rect)
            return

        source_rect = pygame.Rect(0, 0, draw_rect.width, visible_height)
        target_rect = pygame.Rect(
            draw_rect.left, draw_rect.top, draw_rect.width, visible_height
        )
        surface.blit(surf, target_rect, source_rect)