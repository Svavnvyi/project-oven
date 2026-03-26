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


def load_frames_from_paths(
    relative_paths: list[str], *, scale_multiplier: float = 1.0
) -> list[pygame.Surface]:
    """Load images in order (e.g. custom filenames like Cooking_Toaster_1.png)."""
    frames: list[pygame.Surface] = []
    for relative_path in relative_paths:
        image = load_image(relative_path)
        if scale_multiplier != 1.0:
            image = _scale_surface(image, scale_multiplier)
        frames.append(image)
    return frames


def load_ally_toaster_idle_frames(*, scale_multiplier: float = 1.0) -> list[pygame.Surface]:
    paths = [
        "Ally/Toaster/Idle/Idle_Toaster.png",
        "Ally/Toaster/Idle/Idle_Toaster_1.png",
        "Ally/Toaster/Idle/Idle_Toaster_2.png",
    ]
    return load_frames_from_paths(paths, scale_multiplier=scale_multiplier)


def load_ally_toaster_attack_frames(*, scale_multiplier: float = 1.0) -> list[pygame.Surface]:
    paths = [f"Ally/Toaster/Attack/Cooking_Toaster_{i}.png" for i in range(1, 10)]
    return load_frames_from_paths(paths, scale_multiplier=scale_multiplier)


def load_ally_toaster_attack2_frames(*, scale_multiplier: float = 1.0) -> list[pygame.Surface]:
    paths = [f"Ally/Toaster/Attack2/Cooking_Toaster_{i}.png" for i in range(0, 12)]
    return load_frames_from_paths(paths, scale_multiplier=scale_multiplier)


def load_ally_toaster_block_frames(*, scale_multiplier: float = 1.0) -> list[pygame.Surface]:
    paths = [f"Ally/Toaster/Block/Block{i}R.png" for i in range(0, 6)]
    return load_frames_from_paths(paths, scale_multiplier=scale_multiplier)


def load_ally_toaster_death_placeholder(idle_frames: list[pygame.Surface]) -> list[pygame.Surface]:
    """No death art: repeat first idle frame so death state is valid."""
    if not idle_frames:
        return []
    return [idle_frames[0]] * max(1, config.DEATH_FRAMES)


def load_ally_oven_idle_frames(*, scale_multiplier: float = 1.0) -> list[pygame.Surface]:
    return load_animation_frames(
        side="Ally",
        fighter_name="Oven",
        folder_name=config.IDLE_ANIMATION_FOLDER,
        prefix=config.IDLE_ANIMATION_PREFIX,
        frame_count=config.OVEN_IDLE_FRAMES,
        direction_suffix=config.RIGHT_FACING_SUFFIX,
        scale_multiplier=scale_multiplier,
    )


def duplicate_frames_for_fallback(source: list[pygame.Surface]) -> list[pygame.Surface]:
    """Return a shallow copy list for using the same visuals as another animation state."""
    return list(source)
