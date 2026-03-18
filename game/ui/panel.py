"""Bottom panel rendering."""

from dataclasses import dataclass

import pygame


@dataclass(frozen=True)
class AttackButton:
    left: int
    top: int
    image: pygame.Surface
    pressed_image: pygame.Surface
    is_pressed: bool = False
    scale: float = 1.0

def draw_bottom_panel(
    screen: pygame.Surface,
    panel_image: pygame.Surface,
    screen_height: int,
    bottom_panel_height: int,
    attack_buttons: list[AttackButton],
) -> list[pygame.Rect]:
    panel_y = screen_height - bottom_panel_height
    screen.blit(panel_image, (0, panel_y))

    button_rects: list[pygame.Rect] = []
    for attack_button in attack_buttons:
        button_image = (
            attack_button.pressed_image
            if attack_button.is_pressed
            else attack_button.image
        )
        scaled_width = max(1, int(button_image.get_width() * attack_button.scale))
        scaled_height = max(1, int(button_image.get_height() * attack_button.scale))
        scaled_button_image = pygame.transform.scale(
            button_image,
            (scaled_width, scaled_height),
        )
        button_rect = scaled_button_image.get_rect(
            topleft=(attack_button.left, panel_y + attack_button.top)
        )
        screen.blit(scaled_button_image, button_rect.topleft)
        button_rects.append(button_rect)

    return button_rects
