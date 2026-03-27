"""Main game orchestration: input, update, render."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Literal

import pygame

from game import assets, config
from game.entities.fighter import AttackDamageSpec, Fighter, FighterStats
from game.ui.healthbar import draw_cooldownbar, draw_healthbar
from game.ui.panel import AttackButton, draw_bottom_panel

AppState = Literal["main_menu", "character_screen", "upgrade_screen", "playing"]


@dataclass
class CharacterPortraitSlot:
    name: str
    frames: list[pygame.Surface]
    rect: pygame.Rect
    frame_index: int = 0
    last_update_ms: int = 0


class Game:
    ALLY_SPAWN_X = 100
    OPPONENT_SPAWN_X = 900
    FIGHTER_SPAWN_Y = 380

    @property
    def win_coins(self) -> int:
        """Meta currency (wins); shown in HUD and spent on upgrades."""
        return self.player_wins

    def __init__(self) -> None:
        pygame.init()
        self.clock = pygame.time.Clock()
        self.screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        pygame.display.set_caption(config.WINDOW_TITLE)

        self.running = True
        self.app_state: AppState = "main_menu"
        self.selected_ally: str | None = "Fridge"

        self.main_menu_image = assets.load_image(config.MAIN_MENU_IMAGE_PATH)
        if self.main_menu_image.get_size() != (
            config.SCREEN_WIDTH,
            config.SCREEN_HEIGHT,
        ):
            self.main_menu_image = pygame.transform.smoothscale(
                self.main_menu_image,
                (config.SCREEN_WIDTH, config.SCREEN_HEIGHT),
            )
        _mm_w, _mm_h = self.main_menu_image.get_size()
        _px = self.main_menu_image.get_at(
            (_mm_w // 2, min(24, _mm_h - 1))
        )
        self._character_screen_background_color = (
            int(_px[0]),
            int(_px[1]),
            int(_px[2]),
        )
        self.main_menu_new_game_rect = pygame.Rect(*config.MAIN_MENU_NEW_GAME_BUTTON)
        self.main_menu_character_rect = pygame.Rect(*config.MAIN_MENU_CHARACTER_BUTTON)
        #self.main_menu_upgrade_rect = pygame.Rect(*config.MAIN_MENU_UPGRADE_BUTTON)

        self.player_wins = 0
        self.upgrade_purchase_counts: dict[str, int] = {
            "attack": 0,
            "hp": 0,
            "cooldown": 0,
        }
        self.meta_attack_flat = 0
        self.meta_hp_bonus = 0
        self.meta_cooldown_reduction = 0
        self.opponent_hp_mult = 1.0
        self.opponent_attack_mult = 1.0
        self.opponent_interval_mult = 1.0
        self.opponent_scaling_switch_on = True
        self.opponent_scaling_switch_rect = pygame.Rect(0, 0, 0, 0)

        self.upgrade_option_rects: dict[str, pygame.Rect] = {}
        total_w = (
            3 * config.UPGRADE_OPTION_BUTTON_WIDTH + 2 * config.UPGRADE_OPTION_GAP
        )
        start_x = (config.SCREEN_WIDTH - total_w) // 2
        for i, key in enumerate(("attack", "hp", "cooldown")):
            x = start_x + i * (
                config.UPGRADE_OPTION_BUTTON_WIDTH + config.UPGRADE_OPTION_GAP
            )
            self.upgrade_option_rects[key] = pygame.Rect(
                x,
                config.UPGRADE_OPTION_ROW_Y,
                config.UPGRADE_OPTION_BUTTON_WIDTH,
                config.UPGRADE_OPTION_BUTTON_HEIGHT,
            )

        self.upgrade_title_font = pygame.font.Font(None, 40)
        self.upgrade_small_font = pygame.font.Font(None, 22)

        self.background_image = assets.load_image(config.BACKGROUND_IMAGE_PATH)
        self.panel_image = assets.load_image(config.PANEL_IMAGE_PATH)
        self.attack_button_image = assets.load_image(config.ATTACK_BUTTON_IMAGE_PATH)
        self.attack_button_pressed_image = assets.load_image(
            config.ATTACK_BUTTON_PRESSED_IMAGE_PATH
        )
        self.attack_button2_image = assets.load_image(config.ATTACK_BUTTON2_IMAGE_PATH)
        self.attack_button2_pressed_image = assets.load_image(
            config.ATTACK_BUTTON2_PRESSED_IMAGE_PATH
        )
        self.block_button_image = assets.load_image(config.BLOCK_BUTTON_IMAGE_PATH)
        self.block_button_pressed_image = assets.load_image(
            config.BLOCK_BUTTON_PRESSED_IMAGE_PATH
        )
        self.attack_button_rects: list[pygame.Rect] = []
        self.pressed_button_index: int | None = None
        self.cursor_is_hand = False
        self.current_turn = config.ALLY_SIDE
        self.opponent_attack_due_ms = 0
        self.ally_attack2_cooldown_turns_remaining = 0
        self.game_over = False
        self.winner_side: str | None = None
        self.restart_button_rect: pygame.Rect | None = None
        self._restart_first_click_ms: int | None = None
        self._restart_pending_nav_ms: int | None = None
        self.restart_font = pygame.font.Font(None, 44)
        self.character_back_font = pygame.font.Font(None, 36)

        self.ally_fighter: Fighter | None = None
        self.opponent_fighter: Fighter | None = None
        self.fighters: list[Fighter] = []

        self._character_portrait_slots: list[CharacterPortraitSlot] = []
        self.character_back_button_rect = pygame.Rect(0, 0, 0, 0)
        self._load_character_portraits()

        raw_coin = assets.load_image(config.WIN_COIN_IMAGE_PATH)
        ch = raw_coin.get_height()
        cw = raw_coin.get_width()
        if ch > 0 and config.WIN_COIN_HUD_HEIGHT < ch:
            scale = config.WIN_COIN_HUD_HEIGHT / ch
            nw = max(1, int(cw * scale))
            nh = max(1, int(ch * scale))
            self.win_coin_hud_image = pygame.transform.smoothscale(raw_coin, (nw, nh))
        else:
            self.win_coin_hud_image = raw_coin
        self._win_coin_granted_this_match = False

        pygame.mixer.init()
        _music_path = config.ASSETS_ROOT / config.BACKGROUND_MUSIC_RELATIVE_PATH
        if _music_path.is_file():
            try:
                pygame.mixer.music.load(str(_music_path))
                pygame.mixer.music.set_volume(config.BACKGROUND_MUSIC_VOLUME)
                pygame.mixer.music.play(-1)
            except pygame.error as exc:
                print(f"Background music could not play: {exc}")
        else:
            print(f"Background music file not found: {_music_path}")

    @staticmethod
    def _load_ally_idle_frames_for_portrait(ally_name: str) -> list[pygame.Surface]:
        sm = config.IDLE_SCALE_MULTIPLIER
        if ally_name == "Fridge":
            return assets.load_animation_frames(
                side=config.ALLY_SIDE,
                fighter_name="Fridge",
                folder_name=config.IDLE_ANIMATION_FOLDER,
                prefix=config.IDLE_ANIMATION_PREFIX,
                frame_count=config.IDLE_FRAMES,
                direction_suffix=config.RIGHT_FACING_SUFFIX,
                scale_multiplier=sm,
            )
        if ally_name == "Toaster":
            return assets.load_ally_toaster_idle_frames(scale_multiplier=sm)
        if ally_name == "Oven":
            return assets.load_ally_oven_idle_frames(scale_multiplier=sm)
        raise ValueError(f"Unknown portrait ally: {ally_name!r}")

    @staticmethod
    def _scale_portrait_frames_to_max_height(
        frames: list[pygame.Surface],
    ) -> list[pygame.Surface]:
        if not frames:
            return frames
        h0 = frames[0].get_height()
        if h0 <= config.CHARACTER_PORTRAIT_MAX_HEIGHT:
            return frames
        scale = config.CHARACTER_PORTRAIT_MAX_HEIGHT / h0
        out: list[pygame.Surface] = []
        for f in frames:
            nw = max(1, int(f.get_width() * scale))
            nh = max(1, int(f.get_height() * scale))
            out.append(pygame.transform.smoothscale(f, (nw, nh)))
        return out

    def _load_character_portraits(self) -> None:
        self._character_portrait_slots = []
        scaled_slots: list[tuple[str, list[pygame.Surface]]] = []
        for name in config.CHARACTER_PORTRAIT_ALLIES:
            raw_frames = self._load_ally_idle_frames_for_portrait(name)
            frames = self._scale_portrait_frames_to_max_height(raw_frames)
            scaled_slots.append((name, frames))

        total_width = sum(
            frames[0].get_width() for _, frames in scaled_slots
        ) + config.CHARACTER_PORTRAIT_GAP * (len(scaled_slots) - 1)
        x = (config.SCREEN_WIDTH - total_width) // 2
        y = config.CHARACTER_PORTRAIT_TOP_MARGIN
        t0 = pygame.time.get_ticks()
        for name, frames in scaled_slots:
            rect = frames[0].get_rect(topleft=(x, y))
            self._character_portrait_slots.append(
                CharacterPortraitSlot(
                    name=name,
                    frames=frames,
                    rect=rect,
                    frame_index=0,
                    last_update_ms=t0,
                )
            )
            x += frames[0].get_width() + config.CHARACTER_PORTRAIT_GAP

        bw = config.CHARACTER_BACK_BUTTON_WIDTH
        bh = config.CHARACTER_BACK_BUTTON_HEIGHT
        bx = (config.SCREEN_WIDTH - bw) // 2
        by = config.SCREEN_HEIGHT - config.CHARACTER_BACK_BUTTON_BOTTOM_MARGIN - bh
        self.character_back_button_rect = pygame.Rect(bx, by, bw, bh)

    def _update_character_portrait_animations(self, now_ms: int) -> None:
        for slot in self._character_portrait_slots:
            if len(slot.frames) <= 1:
                continue
            cooldown_ms = (
                config.TOASTER_IDLE_ANIMATION_COOLDOWN_MS
                if slot.name == "Toaster"
                else config.CHARACTER_PORTRAIT_ANIM_COOLDOWN_MS
            )
            if now_ms - slot.last_update_ms >= cooldown_ms:
                slot.last_update_ms = now_ms
                slot.frame_index = (slot.frame_index + 1) % len(slot.frames)

    def _draw_win_coins_hud(self) -> None:
        """Top-right: scaled coin icon + numeric amount (uses upgrade_small_font)."""
        text_s = self.upgrade_small_font.render(
            str(self.win_coins), True, config.WIN_COINS_HUD_COLOR
        )
        iw, ih = self.win_coin_hud_image.get_size()
        tw, th = text_s.get_size()
        gap = config.WIN_COIN_HUD_GAP
        total_h = max(ih, th)
        y_base = config.WIN_COINS_HUD_MARGIN_Y
        y_text = y_base + (total_h - th) // 2
        y_icon = y_base + (total_h - ih) // 2
        right_x = config.SCREEN_WIDTH - config.WIN_COINS_HUD_MARGIN_X
        text_rect = text_s.get_rect(topright=(right_x, y_text))
        icon_x = text_rect.left - gap - iw
        self.screen.blit(self.win_coin_hud_image, (icon_x, y_icon))
        self.screen.blit(text_s, text_rect)

    def _draw_opponent_scaling_switch(self) -> None:
        """Top-right below win coins: ON/OFF label + clickable track (thumb)."""
        text_s = self.upgrade_small_font.render(
            str(self.win_coins), True, config.WIN_COINS_HUD_COLOR
        )
        iw, ih = self.win_coin_hud_image.get_size()
        tw, th = text_s.get_size()
        total_h = max(ih, th)
        y_base = config.WIN_COINS_HUD_MARGIN_Y
        y_switch = y_base + total_h + config.OPPONENT_SCALING_SWITCH_TOP_GAP
        right_x = config.SCREEN_WIDTH - config.WIN_COINS_HUD_MARGIN_X
        track_w = config.OPPONENT_SCALING_SWITCH_TRACK_W
        track_h = config.OPPONENT_SCALING_SWITCH_TRACK_H
        m = config.OPPONENT_SCALING_SWITCH_THUMB_MARGIN
        label_text = "ON" if self.opponent_scaling_switch_on else "OFF"
        label_s = self.upgrade_small_font.render(
            label_text, True, config.OPPONENT_SCALING_SWITCH_LABEL_COLOR
        )
        lw, lh = label_s.get_size()
        gap = 6
        total_w = lw + gap + track_w
        left_x = right_x - total_w
        track_y = y_switch + max(0, (lh - track_h) // 2)
        track_rect = pygame.Rect(left_x + lw + gap, track_y, track_w, track_h)
        self.opponent_scaling_switch_rect = pygame.Rect(
            left_x, y_switch, total_w, max(lh, track_h)
        )
        self.screen.blit(label_s, (left_x, y_switch))
        track_color = (
            config.OPPONENT_SCALING_SWITCH_TRACK_ON
            if self.opponent_scaling_switch_on
            else config.OPPONENT_SCALING_SWITCH_TRACK_OFF
        )
        pygame.draw.rect(self.screen, track_color, track_rect)
        pygame.draw.rect(self.screen, (28, 28, 32), track_rect, 1)
        thumb_side = max(8, track_h - 2 * m)
        thumb_x = (
            track_rect.right - m - thumb_side
            if self.opponent_scaling_switch_on
            else track_rect.left + m
        )
        thumb_y = track_rect.centery - thumb_side // 2
        thumb_color = (
            config.OPPONENT_SCALING_SWITCH_THUMB_ON
            if self.opponent_scaling_switch_on
            else config.OPPONENT_SCALING_SWITCH_THUMB_OFF
        )
        pygame.draw.rect(
            self.screen,
            thumb_color,
            pygame.Rect(thumb_x, thumb_y, thumb_side, thumb_side),
        )

    def _ally_attack2_cooldown_max_turns(self) -> int:
        return max(
            1,
            config.ATTACK2_COOLDOWN_ALLY_TURNS - self.meta_cooldown_reduction,
        )

    def _build_ally_fridge(self) -> Fighter:
        stats = FighterStats(
            name="Fridge",
            max_hp=config.FRIDGE_ALLY_MAX_HP + self.meta_hp_bonus,
            strength=config.FRIDGE_ALLY_STRENGTH,
            side=config.ALLY_SIDE,
            initiative=config.FRIDGE_ALLY_INITIATIVE,
            attack1=AttackDamageSpec(
                config.FRIDGE_ATTACK1_DICE_COUNT,
                config.FRIDGE_ATTACK1_DICE_SIDES,
                config.FRIDGE_ATTACK1_FLAT_BONUS + self.meta_attack_flat,
            ),
            attack2=AttackDamageSpec(
                config.FRIDGE_ATTACK2_DICE_COUNT,
                config.FRIDGE_ATTACK2_DICE_SIDES,
                config.FRIDGE_ATTACK2_FLAT_BONUS + self.meta_attack_flat,
            ),
        )
        idle_frames = assets.load_animation_frames(
            side=stats.side,
            fighter_name=stats.name,
            folder_name=config.IDLE_ANIMATION_FOLDER,
            prefix=config.IDLE_ANIMATION_PREFIX,
            frame_count=config.IDLE_FRAMES,
            direction_suffix=config.RIGHT_FACING_SUFFIX,
            scale_multiplier=config.IDLE_SCALE_MULTIPLIER,
        )
        attack_frames = assets.load_animation_frames(
            side=stats.side,
            fighter_name=stats.name,
            folder_name=config.ATTACK_ANIMATION_FOLDER,
            prefix=config.ATTACK_ANIMATION_PREFIX,
            frame_count=config.ATTACK_FRAMES,
            direction_suffix=config.RIGHT_FACING_SUFFIX,
        )
        death_frames = assets.load_animation_frames(
            side=stats.side,
            fighter_name=stats.name,
            folder_name=config.DEATH_ANIMATION_FOLDER,
            prefix=config.DEATH_ANIMATION_FOLDER,
            frame_count=config.DEATH_FRAMES,
            direction_suffix=config.RIGHT_FACING_SUFFIX,
        )
        block_frames = assets.load_animation_frames(
            side=stats.side,
            fighter_name=stats.name,
            folder_name=config.BLOCK_ANIMATION_FOLDER,
            prefix=config.BLOCK_ANIMATION_PREFIX,
            frame_count=config.FRIDGE_BLOCK_FRAMES,
            direction_suffix=config.RIGHT_FACING_SUFFIX,
            scale_multiplier=config.IDLE_SCALE_MULTIPLIER,
        )
        return Fighter(
            x=self.ALLY_SPAWN_X,
            y=self.FIGHTER_SPAWN_Y,
            stats=stats,
            animations={
                "idle": idle_frames,
                "attack": attack_frames,
                "death": death_frames,
                "block": block_frames,
            },
            animation_cooldown_ms=config.ANIMATION_COOLDOWN_MS,
        )

    def _build_ally_oven(self) -> Fighter:
        stats = FighterStats(
            name="Oven",
            max_hp=config.OVEN_ALLY_MAX_HP + self.meta_hp_bonus,
            strength=config.OVEN_ALLY_STRENGTH,
            side=config.ALLY_SIDE,
            initiative=config.OVEN_ALLY_INITIATIVE,
            attack1=AttackDamageSpec(
                config.OVEN_ATTACK1_DICE_COUNT,
                config.OVEN_ATTACK1_DICE_SIDES,
                config.OVEN_ATTACK1_FLAT_BONUS + self.meta_attack_flat,
            ),
            attack2=AttackDamageSpec(
                config.OVEN_ATTACK2_DICE_COUNT,
                config.OVEN_ATTACK2_DICE_SIDES,
                config.OVEN_ATTACK2_FLAT_BONUS + self.meta_attack_flat,
            ),
        )
        idle_frames = assets.load_ally_oven_idle_frames(
            scale_multiplier=config.IDLE_SCALE_MULTIPLIER,
        )
        attack_frames = assets.duplicate_frames_for_fallback(idle_frames)
        death_frames = assets.duplicate_frames_for_fallback(idle_frames)
        return Fighter(
            x=self.ALLY_SPAWN_X,
            y=self.FIGHTER_SPAWN_Y,
            stats=stats,
            animations={"idle": idle_frames, "attack": attack_frames, "death": death_frames},
            animation_cooldown_ms=config.ANIMATION_COOLDOWN_MS,
        )

    def _build_ally_toaster(self) -> Fighter:
        stats = FighterStats(
            name="Toaster",
            max_hp=config.TOASTER_ALLY_MAX_HP,
            strength=config.TOASTER_ALLY_STRENGTH,
            side=config.ALLY_SIDE,
            initiative=config.TOASTER_ALLY_INITIATIVE,
            attack1=AttackDamageSpec(
                config.TOASTER_ATTACK1_DICE_COUNT,
                config.TOASTER_ATTACK1_DICE_SIDES,
                config.TOASTER_ATTACK1_FLAT_BONUS,
            ),
            attack2=AttackDamageSpec(
                config.TOASTER_ATTACK2_DICE_COUNT,
                config.TOASTER_ATTACK2_DICE_SIDES,
                config.TOASTER_ATTACK2_FLAT_BONUS,
            ),
        )
        idle_frames = assets.load_ally_toaster_idle_frames(
            scale_multiplier=config.IDLE_SCALE_MULTIPLIER,
        )
        attack_frames = assets.load_ally_toaster_attack_frames(
            scale_multiplier=config.IDLE_SCALE_MULTIPLIER,
        )
        attack2_frames = assets.load_ally_toaster_attack2_frames(
            scale_multiplier=config.IDLE_SCALE_MULTIPLIER,
        )
        block_frames = assets.load_ally_toaster_block_frames(
            scale_multiplier=config.IDLE_SCALE_MULTIPLIER,
        )
        death_frames = assets.load_ally_toaster_death_placeholder(idle_frames)
        return Fighter(
            x=self.ALLY_SPAWN_X,
            y=self.FIGHTER_SPAWN_Y - 5,
            stats=stats,
            animations={
                "idle": idle_frames,
                "attack": attack_frames,
                "attack2": attack2_frames,
                "block": block_frames,
                "death": death_frames,
            },
            animation_cooldown_ms=config.ANIMATION_COOLDOWN_MS,
            idle_animation_cooldown_ms=config.TOASTER_IDLE_ANIMATION_COOLDOWN_MS,
        )

    def _build_ally_from_selection(self) -> Fighter:
        key = (self.selected_ally or "Fridge").strip()
        if key == "Oven":
            return self._build_ally_oven()
        if key == "Toaster":
            return self._build_ally_toaster()
        return self._build_ally_fridge()

    def _build_opponent_fridge(self) -> Fighter:
        attack1 = AttackDamageSpec(
            config.OPPONENT_ATTACK1_DICE_COUNT,
            config.OPPONENT_ATTACK1_DICE_SIDES,
            config.OPPONENT_ATTACK1_FLAT_BONUS,
        )
        attack2 = AttackDamageSpec(
            config.OPPONENT_ATTACK2_DICE_COUNT,
            config.OPPONENT_ATTACK2_DICE_SIDES,
            config.OPPONENT_ATTACK2_FLAT_BONUS,
        )
        hp_base = config.OPPONENT_FRIDGE_MAX_HP
        if random.random() < config.OPPONENT_FRIDGE_TOASTER_STAT_REPLACE_CHANCE:
            if random.random() < config.OPPONENT_FRIDGE_TOASTER_REPLACE_NEITHER_CHANCE:
                pass
            else:
                which = random.choice(("attack1", "attack2"))
                if which == "attack1":
                    attack1 = AttackDamageSpec(
                        config.TOASTER_ATTACK1_DICE_COUNT,
                        config.TOASTER_ATTACK1_DICE_SIDES,
                        config.TOASTER_ATTACK1_FLAT_BONUS,
                    )
                else:
                    attack2 = AttackDamageSpec(
                        config.TOASTER_ATTACK2_DICE_COUNT,
                        config.TOASTER_ATTACK2_DICE_SIDES,
                        config.TOASTER_ATTACK2_FLAT_BONUS,
                    )
        max_hp = max(1, int(hp_base * self.opponent_hp_mult + 0.5))
        stats = FighterStats(
            name="Fridge",
            max_hp=max_hp,
            strength=config.OPPONENT_FRIDGE_STRENGTH,
            side=config.OPPONENT_SIDE,
            initiative=config.OPPONENT_INITIATIVE,
            attack1=attack1,
            attack2=attack2,
        )
        idle_frames = assets.load_animation_frames(
            side=stats.side,
            fighter_name=stats.name,
            folder_name=config.IDLE_ANIMATION_FOLDER,
            prefix=config.IDLE_ANIMATION_PREFIX,
            frame_count=config.IDLE_FRAMES,
            direction_suffix=config.LEFT_FACING_SUFFIX,
            scale_multiplier=config.IDLE_SCALE_MULTIPLIER,
        )
        attack_frames = assets.load_animation_frames(
            side=stats.side,
            fighter_name=stats.name,
            folder_name=config.ATTACK_ANIMATION_FOLDER,
            prefix=config.ATTACK_ANIMATION_PREFIX,
            frame_count=config.ATTACK_FRAMES,
            direction_suffix=config.LEFT_FACING_SUFFIX,
        )
        death_frames = assets.load_animation_frames(
            side=stats.side,
            fighter_name=stats.name,
            folder_name=config.DEATH_ANIMATION_FOLDER,
            prefix=config.DEATH_ANIMATION_FOLDER,
            frame_count=config.DEATH_FRAMES,
            direction_suffix=config.LEFT_FACING_SUFFIX,
        )
        block_frames = assets.load_animation_frames(
            side=stats.side,
            fighter_name=stats.name,
            folder_name=config.BLOCK_ANIMATION_FOLDER,
            prefix=config.BLOCK_ANIMATION_PREFIX,
            frame_count=config.FRIDGE_BLOCK_FRAMES,
            direction_suffix=config.LEFT_FACING_SUFFIX,
            scale_multiplier=config.IDLE_SCALE_MULTIPLIER,
        )
        return Fighter(
            x=self.OPPONENT_SPAWN_X,
            y=self.FIGHTER_SPAWN_Y,
            stats=stats,
            animations={
                "idle": idle_frames,
                "attack": attack_frames,
                "death": death_frames,
                "block": block_frames,
            },
            animation_cooldown_ms=config.ANIMATION_COOLDOWN_MS,
        )

    def _start_new_game(self) -> None:
        self._reset_game_state()
        self.app_state = "playing"

    def _return_to_main_menu(self) -> None:
        self.app_state = "main_menu"
        self.pressed_button_index = None

    @staticmethod
    def _hexagon_points(rect: pygame.Rect, cut: int) -> list[tuple[int, int]]:
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

    def _draw_hex_menu_button(
        self,
        rect: pygame.Rect,
        label: str,
        font: pygame.font.Font,
    ) -> None:
        cut = 18
        inner = (45, 70, 130)
        outer = (25, 25, 28)
        highlight = (200, 210, 225)
        pts = self._hexagon_points(rect, cut)
        pygame.draw.polygon(self.screen, inner, pts)
        pygame.draw.polygon(self.screen, outer, pts, 4)
        inset = 3
        inner_rect = rect.inflate(-inset * 2, -inset * 2)
        inner_pts = self._hexagon_points(inner_rect, max(6, cut - inset))
        pygame.draw.lines(self.screen, highlight, True, inner_pts, 2)
        text = font.render(label, True, (8, 8, 12))
        self.screen.blit(text, text.get_rect(center=rect.center))

    def _upgrade_cost_for(self, key: str) -> int:
        return config.UPGRADE_BASE_COST + self.upgrade_purchase_counts.get(key, 0)

    def _try_purchase_upgrade(self, key: str) -> None:
        cost = self._upgrade_cost_for(key)
        if self.player_wins < cost:
            return
        if key == "cooldown":
            max_reduction = max(0, config.ATTACK2_COOLDOWN_ALLY_TURNS - 1)
            if self.meta_cooldown_reduction >= max_reduction:
                return
        self.player_wins -= cost
        self.upgrade_purchase_counts[key] = self.upgrade_purchase_counts.get(key, 0) + 1
        if key == "attack":
            self.meta_attack_flat += config.ALLY_UPGRADE_ATTACK_FLAT_PER
        elif key == "hp":
            self.meta_hp_bonus += config.ALLY_UPGRADE_HP_PER
        elif key == "cooldown":
            max_reduction = max(0, config.ATTACK2_COOLDOWN_ALLY_TURNS - 1)
            self.meta_cooldown_reduction = min(
                self.meta_cooldown_reduction + 1,
                max_reduction,
            )
        self._apply_opponent_random_buff()

    def _reset_ally_meta_and_opponent_scaling(self) -> None:
        """Reset ally upgrade stats and opponent multipliers. Does not change player_wins."""
        self.meta_attack_flat = 0
        self.meta_hp_bonus = 0
        self.meta_cooldown_reduction = 0
        self.upgrade_purchase_counts = {"attack": 0, "hp": 0, "cooldown": 0}
        self.opponent_hp_mult = 1.0
        self.opponent_attack_mult = 1.0
        self.opponent_interval_mult = 1.0

    def _reset_opponent_scaling_mults_only(self) -> None:
        self.opponent_hp_mult = 1.0
        self.opponent_attack_mult = 1.0
        self.opponent_interval_mult = 1.0

    def _toggle_opponent_scaling_switch(self) -> None:
        self.opponent_scaling_switch_on = not self.opponent_scaling_switch_on
        if not self.opponent_scaling_switch_on:
            self._reset_opponent_scaling_mults_only()

    def _apply_opponent_random_buff(self) -> None:
        if not self.opponent_scaling_switch_on:
            return
        choices = ["hp", "attack", "interval"]
        choice = random.choice(choices)
        if choice == "hp":
            self.opponent_hp_mult *= config.OPPONENT_BUFF_MULT
        elif choice == "attack":
            self.opponent_attack_mult *= config.OPPONENT_BUFF_MULT
        else:
            self.opponent_interval_mult *= config.OPPONENT_INTERVAL_FASTER_MULT
            self.opponent_interval_mult = max(0.35, self.opponent_interval_mult)

    def handle_input(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                continue
            if self.app_state == "main_menu":
                self._handle_input_main_menu(event)
            elif self.app_state == "character_screen":
                self._handle_input_character_screen(event)
            elif self.app_state == "upgrade_screen":
                self._handle_input_upgrade_screen(event)
            elif self.app_state == "playing":
                self._handle_input_playing(event)

    def _handle_input_main_menu(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.main_menu_new_game_rect.collidepoint(event.pos):
                self._start_new_game()
            elif self.main_menu_character_rect.collidepoint(event.pos):
                self.app_state = "character_screen"

    def _handle_input_character_screen(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._return_to_main_menu()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.opponent_scaling_switch_rect.collidepoint(event.pos):
                self._toggle_opponent_scaling_switch()
                return
            if self.character_back_button_rect.collidepoint(event.pos):
                self._return_to_main_menu()
                return
            for slot in self._character_portrait_slots:
                if slot.rect.collidepoint(event.pos):
                    self.selected_ally = slot.name
                    self._return_to_main_menu()
                    return

    def _handle_input_upgrade_screen(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._return_to_main_menu()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.opponent_scaling_switch_rect.collidepoint(event.pos):
                self._toggle_opponent_scaling_switch()
                return
            if self.character_back_button_rect.collidepoint(event.pos):
                self._return_to_main_menu()
                return
            for key, rect in self.upgrade_option_rects.items():
                if rect.collidepoint(event.pos):
                    self._try_purchase_upgrade(key)
                    return

    def _handle_input_playing(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.opponent_scaling_switch_rect.collidepoint(event.pos):
                self._toggle_opponent_scaling_switch()
                return
        if self.ally_fighter is None or self.opponent_fighter is None:
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.pressed_button_index = None
            if self.game_over:
                if (
                    self.restart_button_rect is not None
                    and self.restart_button_rect.collidepoint(event.pos)
                ):
                    now_ms = pygame.time.get_ticks()
                    if (
                        self._restart_first_click_ms is not None
                        and now_ms - self._restart_first_click_ms
                        < config.RESTART_DOUBLE_CLICK_MS
                    ):
                        self._restart_pending_nav_ms = None
                        self._restart_first_click_ms = None
                        self._reset_ally_meta_and_opponent_scaling()
                        self._go_to_character_select_after_game_over()
                    else:
                        self._restart_first_click_ms = now_ms
                        self._restart_pending_nav_ms = (
                            now_ms + config.RESTART_SINGLE_CLICK_DELAY_MS
                        )
                return
            if not self._is_combat_active() or self.current_turn != config.ALLY_SIDE:
                return
            for index, button_rect in enumerate(self.attack_button_rects):
                if button_rect.collidepoint(event.pos):
                    self.pressed_button_index = index
                    if index == 2:
                        if self.ally_fighter.activate_block():
                            self._handoff_to_opponent_turn()
                    elif index == 1:
                        # Attack2: same 5 Ally-turn cooldown for Fridge, Oven, and Toaster
                        if (
                            self.ally_attack2_cooldown_turns_remaining == 0
                            and self.ally_fighter.alive
                            and self.opponent_fighter.alive
                            and self.ally_fighter.request_attack(
                                fridge_attack2_visual=self.ally_fighter.name
                                == "Fridge",
                                attack_animation_key=(
                                    "attack2"
                                    if self.ally_fighter.name == "Toaster"
                                    else "attack"
                                ),
                                is_attack2=True,
                            )
                        ):
                            damage = self.ally_fighter.roll_attack2_damage()
                            self._apply_damage_to_all_opponents(damage)
                            self.ally_attack2_cooldown_turns_remaining = (
                                self._ally_attack2_cooldown_max_turns()
                            )
                            if self._is_combat_active():
                                self._handoff_to_opponent_turn()
                    elif index == 0:
                        if (
                            self.ally_fighter.alive
                            and self.opponent_fighter.alive
                            and self.ally_fighter.request_attack()
                        ):
                            damage = self.ally_fighter.roll_attack1_damage()
                            self._apply_damage_to_all_opponents(damage)
                            if self._is_combat_active():
                                self._handoff_to_opponent_turn()
                    break
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.pressed_button_index = None

    def update(self) -> None:
        now_ms = pygame.time.get_ticks()
        if self.app_state in ("character_screen", "upgrade_screen"):
            self._update_character_portrait_animations(now_ms)

        if self.app_state != "playing":
            return

        if self.game_over:
            now_ms = pygame.time.get_ticks()
            if (
                self._restart_pending_nav_ms is not None
                and now_ms >= self._restart_pending_nav_ms
            ):
                self._restart_pending_nav_ms = None
                self._restart_first_click_ms = None
                self._go_to_character_select_after_game_over()
            return

        if self.winner_side is None:
            if self._is_side_wiped(config.ALLY_SIDE):
                self.winner_side = config.OPPONENT_SIDE
                self.pressed_button_index = None
            elif self._is_side_wiped(config.OPPONENT_SIDE):
                self.winner_side = config.ALLY_SIDE
                self.pressed_button_index = None
                if not self._win_coin_granted_this_match:
                    self.player_wins += 1
                    self._win_coin_granted_this_match = True
                    self._apply_opponent_random_buff()

        if self.ally_fighter is None or self.opponent_fighter is None:
            return

        now_ms = pygame.time.get_ticks()
        if (
            self._is_combat_active()
            and self.current_turn == config.OPPONENT_SIDE
            and now_ms >= self.opponent_attack_due_ms
        ):
            action_roll = random.random()
            attack_threshold = config.OPPONENT_ATTACK_CHANCE
            attack2_threshold = attack_threshold + config.OPPONENT_ATTACK2_CHANCE

            if action_roll < attack_threshold and self.opponent_fighter.request_attack():
                damage = self.opponent_fighter.roll_attack1_damage()
                damage = max(1, int(damage * self.opponent_attack_mult + 0.5))
                self.ally_fighter.take_damage(damage)
            elif action_roll < attack2_threshold and self.opponent_fighter.request_attack(
                fridge_attack2_visual=self.opponent_fighter.name == "Fridge",
                is_attack2=True,
            ):
                damage = self.opponent_fighter.roll_attack2_damage()
                damage = max(1, int(damage * self.opponent_attack_mult + 0.5))
                self.ally_fighter.take_damage(damage)
            else:
                self.opponent_fighter.activate_block()
            if self._is_combat_active():
                self._handoff_to_ally_turn()
        for fighter in self.fighters:
            fighter.update(now_ms)

        if (
            self.winner_side is not None
            and not self.game_over
            and self._losing_side_death_animations_complete()
        ):
            self.game_over = True

    def render(self) -> None:
        if self.app_state == "main_menu":
            self.screen.blit(self.main_menu_image, (0, 0))
            self._draw_win_coins_hud()
            self._update_hover_cursor()
        elif self.app_state == "character_screen":
            self._render_character_screen()
            self._update_hover_cursor()
        elif self.app_state == "upgrade_screen":
            self._render_upgrade_screen()
            self._update_hover_cursor()
        elif self.app_state == "playing":
            self._render_playing()
            self._update_hover_cursor()
        pygame.display.flip()

    def _render_character_screen(self) -> None:
        self.screen.fill(self._character_screen_background_color)
        self._draw_win_coins_hud()
        self._draw_opponent_scaling_switch()
        for slot in self._character_portrait_slots:
            self.screen.blit(slot.frames[slot.frame_index], slot.rect)
        mouse_pos = pygame.mouse.get_pos()
        for slot in self._character_portrait_slots:
            if slot.rect.collidepoint(mouse_pos):
                pygame.draw.rect(
                    self.screen,
                    config.CHARACTER_PORTRAIT_HOVER_BORDER_COLOR,
                    slot.rect,
                    config.CHARACTER_PORTRAIT_HOVER_BORDER_WIDTH,
                )
                break
        pygame.draw.rect(
            self.screen,
            config.CHARACTER_BACK_BUTTON_BG_COLOR,
            self.character_back_button_rect,
        )
        pygame.draw.rect(
            self.screen,
            config.CHARACTER_BACK_BUTTON_BORDER_COLOR,
            self.character_back_button_rect,
            config.CHARACTER_BACK_BUTTON_BORDER_WIDTH,
        )
        label = self.character_back_font.render("VISSZA", True, config.CHARACTER_BACK_BUTTON_TEXT_COLOR)
        self.screen.blit(label, label.get_rect(center=self.character_back_button_rect.center))

    def _render_upgrade_screen(self) -> None:
        self.screen.fill((0, 0, 0))
        self._draw_win_coins_hud()
        sub = self.upgrade_small_font.render(
            "Cost per upgrade: 2 + P wins (P = times bought that upgrade)",
            True,
            (180, 180, 190),
        )
        self.screen.blit(sub, sub.get_rect(midtop=(config.SCREEN_WIDTH // 2, 44)))

        for slot in self._character_portrait_slots:
            self.screen.blit(slot.frames[slot.frame_index], slot.rect)

        labels = {
            "attack": "ATTACK",
            "hp": "HP",
            "cooldown": "COOLDOWN",
        }
        for key, rect in self.upgrade_option_rects.items():
            self._draw_hex_menu_button(rect, labels[key], self.character_back_font)
            cost = self._upgrade_cost_for(key)
            affordable = self.player_wins >= cost
            col = (160, 220, 160) if affordable else (200, 100, 100)
            cost_s = self.upgrade_small_font.render(f"{cost} wins", True, col)
            self.screen.blit(
                cost_s,
                cost_s.get_rect(midtop=(rect.centerx, rect.bottom + 6)),
            )

        pygame.draw.rect(
            self.screen,
            config.CHARACTER_BACK_BUTTON_BG_COLOR,
            self.character_back_button_rect,
        )
        pygame.draw.rect(
            self.screen,
            config.CHARACTER_BACK_BUTTON_BORDER_COLOR,
            self.character_back_button_rect,
            config.CHARACTER_BACK_BUTTON_BORDER_WIDTH,
        )
        back = self.character_back_font.render(
            "VISSZA", True, config.CHARACTER_BACK_BUTTON_TEXT_COLOR
        )
        self.screen.blit(back, back.get_rect(center=self.character_back_button_rect.center))

    def _render_playing(self) -> None:
        self.screen.blit(self.background_image, (0, 0))
        panel_top_y = config.SCREEN_HEIGHT - config.BOTTOM_PANEL_HEIGHT
        self.attack_button_rects = draw_bottom_panel(
            self.screen,
            self.panel_image,
            config.SCREEN_HEIGHT,
            config.BOTTOM_PANEL_HEIGHT,
            [
                AttackButton(
                    config.ATTACK_BUTTON_LEFT,
                    config.ATTACK_BUTTON_TOP,
                    self.attack_button_image,
                    self.attack_button_pressed_image,
                    self.pressed_button_index == 0,
                    config.ATTACK_BUTTON_SCALE,
                ),
                AttackButton(
                    config.ATTACK_BUTTON2_LEFT,
                    config.ATTACK_BUTTON2_TOP,
                    self.attack_button2_image,
                    self.attack_button2_pressed_image,
                    self.pressed_button_index == 1,
                    config.ATTACK_BUTTON2_SCALE,
                ),
                AttackButton(
                    config.BLOCK_BUTTON_LEFT,
                    config.BLOCK_BUTTON_TOP,
                    self.block_button_image,
                    self.block_button_pressed_image,
                    self.pressed_button_index == 2,
                    config.BLOCK_BUTTON_SCALE,
                ),
            ],
        )
        for fighter in self.fighters:
            fighter.draw(self.screen, clip_bottom_y=panel_top_y)
            offset_x = (
                config.HEALTHBAR_OFFSET_X + 10
                if fighter.side == config.ALLY_SIDE
                else -config.HEALTHBAR_OFFSET_X - 40
            )
            draw_healthbar(
                self.screen,
                fighter_rect=fighter.rect,
                hp=fighter.hp,
                max_hp=fighter.max_hp,
                width=config.HEALTHBAR_WIDTH,
                height=config.HEALTHBAR_HEIGHT,
                offset_x=offset_x,
                offset_y=config.HEALTHBAR_OFFSET_Y,
                border_color=config.HEALTHBAR_BORDER_COLOR,
                empty_color=config.HEALTHBAR_EMPTY_COLOR,
                fill_color=config.HEALTHBAR_FILL_COLOR,
            )
            if fighter.side == config.ALLY_SIDE:
                draw_cooldownbar(
                    self.screen,
                    fighter_rect=fighter.rect,
                    ratio=self._get_attack2_cooldown_ratio(),
                    width=config.HEALTHBAR_WIDTH,
                    height=config.COOLDOWNBAR_HEIGHT,
                    offset_x=offset_x,
                    offset_y=(
                        config.HEALTHBAR_OFFSET_Y
                        + config.HEALTHBAR_HEIGHT
                        + config.COOLDOWNBAR_OFFSET_Y
                    ),
                    border_color=config.COOLDOWNBAR_BORDER_COLOR,
                    empty_color=config.COOLDOWNBAR_EMPTY_COLOR,
                    fill_color=config.COOLDOWNBAR_FILL_COLOR,
                )
        self._draw_turn_indicator()
        self._draw_win_coins_hud()
        self._draw_opponent_scaling_switch()
        if self.game_over:
            self._draw_restart_overlay()

    def _update_hover_cursor(self) -> None:
        mouse_position = pygame.mouse.get_pos()
        should_use_hand = False
        switch_hover = self.opponent_scaling_switch_rect.collidepoint(mouse_position)
        if self.app_state == "main_menu":
            should_use_hand = switch_hover or (
                self.main_menu_new_game_rect.collidepoint(mouse_position)
                or self.main_menu_character_rect.collidepoint(mouse_position)
            )
        elif self.app_state == "character_screen":
            should_use_hand = switch_hover or self.character_back_button_rect.collidepoint(
                mouse_position
            ) or any(
                slot.rect.collidepoint(mouse_position)
                for slot in self._character_portrait_slots
            )
        elif self.app_state == "upgrade_screen":
            should_use_hand = switch_hover or self.character_back_button_rect.collidepoint(
                mouse_position
            ) or any(
                r.collidepoint(mouse_position) for r in self.upgrade_option_rects.values()
            )
        elif self.app_state == "playing":
            should_use_hand = switch_hover or any(
                button_rect.collidepoint(mouse_position)
                for button_rect in self.attack_button_rects
            )
            if self.game_over and self.restart_button_rect is not None:
                should_use_hand = should_use_hand or self.restart_button_rect.collidepoint(
                    mouse_position
                )
        if should_use_hand == self.cursor_is_hand:
            return
        try:
            cursor_type = (
                pygame.SYSTEM_CURSOR_HAND if should_use_hand else pygame.SYSTEM_CURSOR_ARROW
            )
            pygame.mouse.set_cursor(cursor_type)
            self.cursor_is_hand = should_use_hand
        except pygame.error:
            return

    def _draw_turn_indicator(self) -> None:
        left = config.TURN_INDICATOR_LEFT
        top = config.TURN_INDICATOR_TOP
        size = config.TURN_INDICATOR_SIZE
        line_width = config.TURN_INDICATOR_LINE_WIDTH

        if self.current_turn == config.ALLY_SIDE:
            color = config.TURN_INDICATOR_TICK_COLOR
            pygame.draw.line(
                self.screen,
                color,
                (left, top + int(size * 0.6)),
                (left + int(size * 0.35), top + size),
                line_width,
            )
            pygame.draw.line(
                self.screen,
                color,
                (left + int(size * 0.35), top + size),
                (left + size, top),
                line_width,
            )
            return

        color = config.TURN_INDICATOR_X_COLOR
        pygame.draw.line(
            self.screen,
            color,
            (left, top),
            (left + size, top + size),
            line_width,
        )
        pygame.draw.line(
            self.screen,
            color,
            (left + size, top),
            (left, top + size),
            line_width,
        )

    def _draw_restart_overlay(self) -> None:
        overlay = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill(config.RESTART_OVERLAY_COLOR)
        self.screen.blit(overlay, (0, 0))

        button_x = (config.SCREEN_WIDTH - config.RESTART_BUTTON_WIDTH) // 2
        button_y = (config.SCREEN_HEIGHT - config.RESTART_BUTTON_HEIGHT) // 2
        self.restart_button_rect = pygame.Rect(
            button_x,
            button_y,
            config.RESTART_BUTTON_WIDTH,
            config.RESTART_BUTTON_HEIGHT,
        )
        pygame.draw.rect(self.screen, config.RESTART_BUTTON_BG_COLOR, self.restart_button_rect)
        pygame.draw.rect(
            self.screen,
            config.RESTART_BUTTON_BORDER_COLOR,
            self.restart_button_rect,
            config.RESTART_BUTTON_BORDER_WIDTH,
        )
        label = "RESTART"
        if self.winner_side == config.ALLY_SIDE:
            label = "VICTORY - RESTART"
        elif self.winner_side == config.OPPONENT_SIDE:
            label = "DEFEAT - RESTART"
        label_surface = self.restart_font.render(label, True, config.RESTART_BUTTON_TEXT_COLOR)
        label_rect = label_surface.get_rect(center=self.restart_button_rect.center)
        self.screen.blit(label_surface, label_rect)

    def _handoff_to_opponent_turn(self) -> None:
        self.current_turn = config.OPPONENT_SIDE
        interval = max(
            200,
            int(
                config.OPPONENT_ATTACK_INTERVAL_MS * self.opponent_interval_mult + 0.5
            ),
        )
        self.opponent_attack_due_ms = pygame.time.get_ticks() + interval

    def _handoff_to_ally_turn(self) -> None:
        self.current_turn = config.ALLY_SIDE
        if self.ally_attack2_cooldown_turns_remaining > 0:
            self.ally_attack2_cooldown_turns_remaining -= 1

    def _apply_damage_to_all_opponents(self, damage: int) -> None:
        """AoE: apply the same rolled damage to every living opponent."""
        for fighter in self.fighters:
            if fighter.side == config.OPPONENT_SIDE and fighter.alive:
                fighter.take_damage(damage)

    def _apply_first_turn_from_initiative(self) -> None:
        if self.ally_fighter is None or self.opponent_fighter is None:
            return
        now_ms = pygame.time.get_ticks()
        if self.ally_fighter.initiative >= self.opponent_fighter.initiative:
            self.current_turn = config.ALLY_SIDE
            self.opponent_attack_due_ms = 0
        else:
            self.current_turn = config.OPPONENT_SIDE
            self.opponent_attack_due_ms = now_ms

    def _get_attack2_cooldown_ratio(self) -> float:
        max_turns = self._ally_attack2_cooldown_max_turns()
        if max_turns <= 0:
            return 1.0
        remaining = max(0, self.ally_attack2_cooldown_turns_remaining)
        return max(
            0.0,
            min(1.0, (max_turns - remaining) / max_turns),
        )

    def _is_combat_active(self) -> bool:
        if self.ally_fighter is None or self.opponent_fighter is None:
            return False
        return self.ally_fighter.alive and self.opponent_fighter.alive

    def _is_side_wiped(self, side: str) -> bool:
        if not self.fighters:
            return False
        side_fighters = [fighter for fighter in self.fighters if fighter.side == side]
        return bool(side_fighters) and all(not fighter.alive for fighter in side_fighters)

    def _losing_side_death_animations_complete(self) -> bool:
        """True when every dead fighter on the losing side has finished death animation."""
        if self.winner_side is None:
            return False
        losing_side = (
            config.OPPONENT_SIDE
            if self.winner_side == config.ALLY_SIDE
            else config.ALLY_SIDE
        )
        dead_losers = [
            f for f in self.fighters if f.side == losing_side and not f.alive
        ]
        if not dead_losers:
            return False
        return all(f.death_animation_finished for f in dead_losers)

    def _go_to_character_select_after_game_over(self) -> None:
        """Leave game-over overlay and open the Ally character portrait screen."""
        self._restart_first_click_ms = None
        self._restart_pending_nav_ms = None
        self.game_over = False
        self.winner_side = None
        self.restart_button_rect = None
        self.pressed_button_index = None
        self.app_state = "character_screen"

    def _reset_game_state(self) -> None:
        self.ally_fighter = self._build_ally_from_selection()
        self.opponent_fighter = self._build_opponent_fridge()
        self.fighters = [self.ally_fighter, self.opponent_fighter]
        self.attack_button_rects = []
        self.pressed_button_index = None
        self.ally_attack2_cooldown_turns_remaining = 0
        self.game_over = False
        self.winner_side = None
        self.restart_button_rect = None
        self._restart_first_click_ms = None
        self._restart_pending_nav_ms = None
        self._win_coin_granted_this_match = False
        self._apply_first_turn_from_initiative()

    def run(self) -> None:
        while self.running:
            self.clock.tick(config.FPS)
            self.handle_input()
            self.update()
            self.render()
        pygame.quit()
