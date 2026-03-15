"""Asset loading helpers for images and animation frames."""

from pathlib import Path

import pygame

from game import config


def _resolve_asset_path(relative_path: str) -> Path:
    return config.ASSETS_ROOT / relative_path


def load_image(relative_path: str, *, use_alpha: bool = True) -> pygame.Surface:
    """Load an image from project root and return a pygame surface."""
    image_path = _resolve_asset_path(relative_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Missing image asset: {image_path}")

    image = pygame.image.load(str(image_path))
    return image.convert_alpha() if use_alpha else image.convert()


def load_animation_frames(
    *,
    side: str,
    fighter_name: str,
    folder_name: str,
    prefix: str,
    frame_count: int,
    direction_suffix: str,
    scale_multiplier: float = 1.0,
) -> list[pygame.Surface]:
    """Load an animation sequence like Idle0R.png..IdleN."""
    frames: list[pygame.Surface] = []
    for index in range(frame_count):
        relative_path = (
            f"{side}/{fighter_name}/{folder_name}/{prefix}{index}{direction_suffix}.png"
        )
        image = load_image(relative_path)
        if scale_multiplier != 1.0:
            image = _scale_surface(image, scale_multiplier)
        frames.append(image)
    return frames


def _scale_surface(surface: pygame.Surface, scale_multiplier: float) -> pygame.Surface:
    width = max(1, int(surface.get_width() * scale_multiplier))
    height = max(1, int(surface.get_height() * scale_multiplier))
    return pygame.transform.scale(surface, (width, height))
