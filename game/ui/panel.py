"""Bottom panel rendering."""

import pygame


def draw_bottom_panel(
    screen: pygame.Surface,
    panel_image: pygame.Surface,
    screen_height: int,
    bottom_panel_height: int,
) -> None:
    panel_y = screen_height - bottom_panel_height
    screen.blit(panel_image, (0, panel_y))
