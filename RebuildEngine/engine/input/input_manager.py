"""Input handling."""

import pygame
from typing import Set, Dict


class InputManager:
    # Korean / English key name mapping
    KEY_MAP = {
        "왼쪽": pygame.K_LEFT,
        "오른쪽": pygame.K_RIGHT,
        "위": pygame.K_UP,
        "아래": pygame.K_DOWN,
        "스페이스": pygame.K_SPACE,
        "엔터": pygame.K_RETURN,
        "쉬프트": pygame.K_LSHIFT,
        "컨트롤": pygame.K_LCTRL,
        "a": pygame.K_a,
        "b": pygame.K_b,
        "c": pygame.K_c,
        "d": pygame.K_d,
        "e": pygame.K_e,
        "f": pygame.K_f,
        "g": pygame.K_g,
        "h": pygame.K_h,
        "i": pygame.K_i,
        "j": pygame.K_j,
        "k": pygame.K_k,
        "l": pygame.K_l,
        "m": pygame.K_m,
        "n": pygame.K_n,
        "o": pygame.K_o,
        "p": pygame.K_p,
        "q": pygame.K_q,
        "r": pygame.K_r,
        "s": pygame.K_s,
        "t": pygame.K_t,
        "u": pygame.K_u,
        "v": pygame.K_v,
        "w": pygame.K_w,
        "x": pygame.K_x,
        "y": pygame.K_y,
        "z": pygame.K_z,
        "left": pygame.K_LEFT,
        "right": pygame.K_RIGHT,
        "up": pygame.K_UP,
        "down": pygame.K_DOWN,
        "space": pygame.K_SPACE,
        "enter": pygame.K_RETURN,
        "shift": pygame.K_LSHIFT,
        "ctrl": pygame.K_LCTRL,
    }

    def __init__(self):
        self.keys_held: Set[int] = set()
        self.keys_pressed: Set[int] = set()  # just pressed this frame
        self.keys_released: Set[int] = set()
        self.mouse_pos = (0, 0)
        self.mouse_buttons = [False, False, False]
        self.mouse_pressed = [False, False, False]

    def update(self, events):
        self.keys_pressed.clear()
        self.keys_released.clear()
        self.mouse_pressed = [False, False, False]

        for event in events:
            if event.type == pygame.KEYDOWN:
                self.keys_held.add(event.key)
                self.keys_pressed.add(event.key)
            elif event.type == pygame.KEYUP:
                self.keys_held.discard(event.key)
                self.keys_released.add(event.key)
            elif event.type == pygame.MOUSEMOTION:
                self.mouse_pos = event.pos
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button <= 3:
                    self.mouse_buttons[event.button - 1] = True
                    self.mouse_pressed[event.button - 1] = True
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button <= 3:
                    self.mouse_buttons[event.button - 1] = False

        # also poll current state for held
        pressed = pygame.key.get_pressed()
        # but we already track via events; keep consistent

    def is_key_held(self, name: str) -> bool:
        key = self.KEY_MAP.get(name.lower() if name.isascii() else name)
        if key is None:
            # try raw
            try:
                key = getattr(pygame, f"K_{name.upper()}", None)
            except Exception:
                return False
        if key is None:
            return False
        return key in self.keys_held or pygame.key.get_pressed()[key]

    def is_key_pressed(self, name: str) -> bool:
        key = self.KEY_MAP.get(name.lower() if name.isascii() else name)
        if key is None:
            return False
        return key in self.keys_pressed

    def is_key_released(self, name: str) -> bool:
        key = self.KEY_MAP.get(name.lower() if name.isascii() else name)
        if key is None:
            return False
        return key in self.keys_released
