"""Healthbar rendering helpers."""

import pygame


def draw_healthbar(
    surface: pygame.Surface,
    *,
    fighter_rect: pygame.Rect,
    hp: int,
    max_hp: int,
    width: int,
    height: int,
    offset_x: int,
    offset_y: int,
    border_color: tuple[int, int, int],
    empty_color: tuple[int, int, int],
    fill_color: tuple[int, int, int],
) -> None:
    if max_hp <= 0:
        ratio = 0.0
    else:
        ratio = max(0.0, min(1.0, hp / max_hp))

    bar_x = fighter_rect.centerx - (width // 2) + offset_x
    bar_y = fighter_rect.bottom + offset_y
    bar_rect = pygame.Rect(bar_x, bar_y, width, height)

    pygame.draw.rect(surface, empty_color, bar_rect)

    fill_width = int(width * ratio)
    if fill_width > 0:
        fill_rect = pygame.Rect(bar_x, bar_y, fill_width, height)
        pygame.draw.rect(surface, fill_color, fill_rect)

    pygame.draw.rect(surface, border_color, bar_rect, 2)
