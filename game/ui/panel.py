"""Bottom panel rendering."""

import pygame


def draw_bottom_panel(
    screen: pygame.Surface,
    panel_image: pygame.Surface,
    attack_button_image: pygame.Surface,
    screen_height: int,
    bottom_panel_height: int,
    attack_button_left: int,
    attack_button_top: int,
) -> pygame.Rect:
    panel_y = screen_height - bottom_panel_height
    screen.blit(panel_image, (0, panel_y))
    attack_button_rect = attack_button_image.get_rect(
        topleft=(attack_button_left, panel_y + attack_button_top)
    )
    screen.blit(attack_button_image, attack_button_rect)
    return attack_button_rect
