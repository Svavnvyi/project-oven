import math
from pathlib import Path

from kivy.uix.image import Image


class Player(Image):
    def __init__(self, **kwargs):
        fridge_path = Path(__file__).parent / "assets" / "fridge.png"
        super().__init__(
            source=str(fridge_path),
            allow_stretch=True,
            keep_ratio=True,
            size_hint=(None, None),
            size=(96, 96),
            pos=(0, 0),
            **kwargs,
        )
        self.speed = 280.0

    def update(self, dt, active_keys, bounds_width, bounds_height):
        move_x = 0.0
        move_y = 0.0

        if "a" in active_keys or "left" in active_keys:
            move_x -= 1.0
        if "d" in active_keys or "right" in active_keys:
            move_x += 1.0
        if "s" in active_keys or "down" in active_keys:
            move_y -= 1.0
        if "w" in active_keys or "up" in active_keys:
            move_y += 1.0

        magnitude = math.hypot(move_x, move_y)
        if magnitude:
            move_x /= magnitude
            move_y /= magnitude

        next_x = self.x + (move_x * self.speed * dt)
        next_y = self.y + (move_y * self.speed * dt)

        max_x = max(0.0, bounds_width - self.width)
        max_y = max(0.0, bounds_height - self.height)
        self.x = min(max(0.0, next_x), max_x)
        self.y = min(max(0.0, next_y), max_y)
