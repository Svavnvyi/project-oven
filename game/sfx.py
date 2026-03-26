"""Character action sound effects (wav under assets/sfx/<Name>/)."""

from __future__ import annotations

from typing import Literal

import pygame

from game import config

ActionKind = Literal["attack", "attack2", "block"]

_FILENAME: dict[ActionKind, str] = {
    "attack": "Attack.wav",
    "attack2": "Attack2.wav",
    "block": "Block.wav",
}

_sound_cache: dict[str, pygame.mixer.Sound] = {}


def play_character_action(character_name: str, action: ActionKind) -> None:
    """Play one-shot SFX if the file exists; ignores missing files and load errors."""
    rel = _FILENAME[action]
    path = config.ASSETS_ROOT / "sfx" / character_name / rel
    if not path.is_file():
        return
    key = str(path.resolve())
    sound = _sound_cache.get(key)
    if sound is None:
        try:
            sound = pygame.mixer.Sound(key)
        except pygame.error:
            return
        sound.set_volume(config.SFX_VOLUME)
        _sound_cache[key] = sound
    if character_name == "Fridge" and action in ("attack", "attack2"):
        sound.play(maxtime=config.FRIDGE_ATTACK_SFX_MAX_MS)
    else:
        sound.play()
