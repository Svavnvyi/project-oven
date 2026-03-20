"""Build assets/ui/main_menu.png: sky-blue menu with title, hex buttons, Fridge/Toaster art."""

import math
from pathlib import Path

import pygame


def _hexagon_points(rect: pygame.Rect, cut: int) -> list[tuple[int, int]]:
    """Horizontal hex with pointed left/right (flat top/bottom)."""
    x0, y0, w, h = rect.x, rect.y, rect.w, rect.h
    x1, y1 = x0 + w, y0 + h
    cy = y0 + h // 2
    cut = min(cut, w // 4)
    return [
        (x0 + cut, y0),
        (x1 - cut, y0),
        (x1, cy),
        (x1 - cut, y1),
        (x0 + cut, y1),
        (x0, cy),
    ]


def _draw_hex_button(
    surface: pygame.Surface,
    rect: pygame.Rect,
    label: str,
    font: pygame.font.Font,
) -> None:
    cut = 18
    inner = (45, 70, 130)
    outer = (25, 25, 28)
    highlight = (200, 210, 225)
    pts = _hexagon_points(rect, cut)
    pygame.draw.polygon(surface, inner, pts)
    pygame.draw.polygon(surface, outer, pts, 4)
    # Inner thin highlight (offset inset)
    inset = 3
    inner_rect = rect.inflate(-inset * 2, -inset * 2)
    inner_pts = _hexagon_points(inner_rect, max(6, cut - inset))
    pygame.draw.lines(surface, highlight, True, inner_pts, 2)

    text = font.render(label, True, (8, 8, 12))
    surface.blit(text, text.get_rect(center=rect.center))


def main() -> None:
    pygame.init()
    w, h = 1000, 660
    # Needed for convert_alpha when loading sprites
    pygame.display.set_mode((w, h))
    root = Path(__file__).resolve().parent.parent
    assets = root / "assets"

    surface = pygame.Surface((w, h))
    # Light sky blue
    surface.fill((173, 216, 230))

    # Title centered at top
    font_title = pygame.font.Font(None, 52)
    title = font_title.render("Konyhai karnevál", True, (15, 15, 20))
    surface.blit(title, title.get_rect(midtop=(w // 2, 28)))

    font_btn = pygame.font.Font(None, 34)
    # Middle-left stacked buttons (hitboxes match these rects)
    btn_new = pygame.Rect(48, 268, 292, 56)
    btn_char = pygame.Rect(48, 340, 292, 56)
    btn_up = pygame.Rect(48, 412, 292, 56)
    _draw_hex_button(surface, btn_new, "NEW GAME", font_btn)
    _draw_hex_button(surface, btn_char, "CHARACTER", font_btn)
    _draw_hex_button(surface, btn_up, "UPGRADE", font_btn)

    # Character sprites center-right
    try:
        fridge = pygame.image.load(str(assets / "Ally" / "Fridge" / "Idle" / "Idle0R.png")).convert_alpha()
        toast = pygame.image.load(
            str(assets / "Ally" / "Toaster" / "Idle" / "Idle_Toaster.png")
        ).convert_alpha()
        fw, fh = fridge.get_size()
        fridge_s = pygame.transform.scale(fridge, (int(fw * 0.85), int(fh * 0.85)))
        tw, th = toast.get_size()
        toast_s = pygame.transform.scale(toast, (int(tw * 0.72), int(th * 0.72)))
        fr = fridge_s.get_rect(midbottom=(620, 480))
        tr = toast_s.get_rect(midbottom=(780, 475))
        surface.blit(toast_s, tr)
        surface.blit(fridge_s, fr)
    except (FileNotFoundError, pygame.error) as e:
        print("Optional sprites skipped:", e)

    # Top-right settings-style icon
    cx, cy = w - 42, 44
    pygame.draw.circle(surface, (55, 110, 185), (cx, cy), 24)
    pygame.draw.circle(surface, (15, 15, 18), (cx, cy), 24, 3)
    pygame.draw.circle(surface, (220, 225, 235), (cx, cy), 10)
    for i in range(8):
        ang = i * math.pi / 4
        x1 = cx + int(14 * math.cos(ang))
        y1 = cy + int(14 * math.sin(ang))
        x2 = cx + int(6 * math.cos(ang))
        y2 = cy + int(6 * math.sin(ang))
        pygame.draw.line(surface, (230, 235, 245), (x2, y2), (x1, y1), 2)

    out = assets / "ui" / "main_menu.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(surface, str(out))
    print("Wrote", out)


if __name__ == "__main__":
    main()
