"""UI helpers — Korean font embedded (NanumGothic)."""

from __future__ import annotations

import os
import pygame
from typing import Optional, Tuple, Callable

BG_DARK = (22, 23, 28)
BG_PANEL = (32, 34, 42)
BG_PANEL2 = (42, 44, 54)
BG_HOVER = (55, 58, 72)
BG_ACTIVE = (55, 95, 160)
BORDER = (60, 64, 80)
TEXT = (225, 228, 235)
TEXT_DIM = (130, 136, 150)
ACCENT = (70, 140, 230)
DANGER = (210, 75, 75)
SUCCESS = (70, 175, 110)
INPUT_BG = (20, 22, 28)
TOOLBAR = (28, 30, 38)


def _find_font_file(bold: bool = False) -> Optional[str]:
    """Locate bundled NanumGothic or system Hangul fonts."""
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)
    candidates = []
    if bold:
        candidates += [
            os.path.join(root, "fonts", "NanumGothic-Bold.ttf"),
            os.path.join(here, "fonts", "NanumGothic-Bold.ttf"),
        ]
    candidates += [
        os.path.join(root, "fonts", "NanumGothic.ttf"),
        os.path.join(here, "fonts", "NanumGothic.ttf"),
        "/usr/share/fonts/SlidesCarnival/google/Nanum Gothic/NanumGothic-Regular.ttf",
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ]
    if bold:
        candidates.insert(0, "/usr/share/fonts/SlidesCarnival/google/Nanum Gothic/NanumGothic-Bold.ttf")
    for p in candidates:
        if p and os.path.isfile(p):
            return p
    return None


class Fonts:
    _cache = {}
    _path_regular = None
    _path_bold = None
    _resolved = False

    @classmethod
    def _resolve(cls):
        if cls._resolved:
            return
        cls._path_regular = _find_font_file(False)
        cls._path_bold = _find_font_file(True) or cls._path_regular
        cls._resolved = True

    @classmethod
    def get(cls, size: int = 16, bold: bool = False) -> pygame.font.Font:
        key = (size, bold)
        if key not in cls._cache:
            cls._resolve()
            path = cls._path_bold if bold else cls._path_regular
            font = None
            if path:
                try:
                    font = pygame.font.Font(path, size)
                except Exception as e:
                    print(f"[Fonts] load fail {path}: {e}")
            if font is None:
                # last resort
                try:
                    font = pygame.font.SysFont("nanumgothic, notosanscjk, sans-serif", size, bold=bold)
                except Exception:
                    font = pygame.font.Font(None, size)
            cls._cache[key] = font
        return cls._cache[key]


def draw_rect(surf, rect, color, border=0, border_color=BORDER, radius=0):
    if radius > 0:
        pygame.draw.rect(surf, color, rect, border_radius=radius)
        if border:
            pygame.draw.rect(surf, border_color, rect, border, border_radius=radius)
    else:
        pygame.draw.rect(surf, color, rect)
        if border:
            pygame.draw.rect(surf, border_color, rect, border)


def draw_text(surf, text: str, pos: Tuple[int, int], color=TEXT, size=14, bold=False, center=False):
    font = Fonts.get(size, bold)
    # ensure str
    text = str(text) if text is not None else ""
    try:
        img = font.render(text, True, color)
    except Exception:
        img = font.render(text.encode("utf-8", "replace").decode("utf-8", "replace"), True, color)
    r = img.get_rect()
    if center:
        r.center = pos
    else:
        r.topleft = pos
    surf.blit(img, r)
    return r


def text_width(text: str, size: int = 13, bold: bool = False) -> int:
    return Fonts.get(size, bold).size(str(text))[0]


class Button:
    def __init__(self, rect, label: str, on_click: Optional[Callable] = None, color=BG_PANEL2, accent=False, danger=False):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.on_click = on_click
        self.color = color
        self.accent = accent
        self.danger = danger
        self.hovered = False
        self.enabled = True

    def handle_event(self, event) -> bool:
        if not self.enabled:
            return False
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                if self.on_click:
                    self.on_click()
                return True
        return False

    def draw(self, surf):
        if not self.enabled:
            c = (45, 45, 50)
        elif self.hovered:
            c = (180, 60, 60) if self.danger else ((90, 160, 240) if self.accent else BG_HOVER)
        else:
            c = (140, 50, 50) if self.danger else (ACCENT if self.accent else self.color)
        draw_rect(surf, self.rect, c, border=1, radius=5)
        draw_text(surf, self.label, self.rect.center, TEXT, 13, center=True)


class TextInput:
    """Supports Korean via SDL TEXTINPUT + KEYDOWN unicode."""

    def __init__(self, rect, value: str = "", numeric: bool = False, on_change: Optional[Callable] = None):
        self.rect = pygame.Rect(rect)
        self.value = str(value)
        self.numeric = numeric
        self.on_change = on_change
        self.active = False
        self.cursor = len(self.value)

    def set_value(self, v):
        self.value = str(v) if v is not None else ""
        self.cursor = len(self.value)

    def _insert(self, text: str):
        if not text:
            return
        if self.numeric:
            text = "".join(ch for ch in text if ch in "0123456789.-")
            if not text:
                return
        self.value = self.value[: self.cursor] + text + self.value[self.cursor :]
        self.cursor += len(text)
        if self.on_change:
            self.on_change(self.value)

    def handle_event(self, event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            was = self.active
            self.active = self.rect.collidepoint(event.pos)
            if self.active:
                self.cursor = len(self.value)
                try:
                    pygame.key.start_text_input()
                    pygame.key.set_text_input_rect(self.rect)
                except Exception:
                    pass
            elif was:
                try:
                    pygame.key.stop_text_input()
                except Exception:
                    pass
            return self.active

        if not self.active:
            return False

        # IME composition result (Hangul 완성)
        if event.type == pygame.TEXTINPUT:
            self._insert(event.text)
            return True

        if event.type == pygame.TEXTEDITING:
            # composition preview — optional, skip for simplicity
            return True

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE, pygame.K_TAB):
                self.active = False
                try:
                    pygame.key.stop_text_input()
                except Exception:
                    pass
                if self.on_change:
                    self.on_change(self.value)
                return True
            if event.key == pygame.K_BACKSPACE:
                if self.cursor > 0:
                    self.value = self.value[: self.cursor - 1] + self.value[self.cursor :]
                    self.cursor -= 1
                    if self.on_change:
                        self.on_change(self.value)
                return True
            if event.key == pygame.K_DELETE:
                if self.cursor < len(self.value):
                    self.value = self.value[: self.cursor] + self.value[self.cursor + 1 :]
                    if self.on_change:
                        self.on_change(self.value)
                return True
            if event.key == pygame.K_LEFT:
                self.cursor = max(0, self.cursor - 1)
                return True
            if event.key == pygame.K_RIGHT:
                self.cursor = min(len(self.value), self.cursor + 1)
                return True
            if event.key == pygame.K_HOME:
                self.cursor = 0
                return True
            if event.key == pygame.K_END:
                self.cursor = len(self.value)
                return True
            # 문자 입력은 TEXTINPUT 만 사용 (KEYDOWN unicode 와 중복 방지)
            return True
        return False

    def draw(self, surf):
        c = INPUT_BG if not self.active else (30, 36, 50)
        border_c = ACCENT if self.active else BORDER
        draw_rect(surf, self.rect, c, border=1, border_color=border_c, radius=4)
        clip = surf.get_clip()
        inner = self.rect.inflate(-4, -2)
        surf.set_clip(inner)
        draw_text(surf, self.value, (self.rect.x + 6, self.rect.y + 4), TEXT, 13)
        if self.active:
            font = Fonts.get(13)
            prefix = font.render(self.value[: self.cursor], True, TEXT)
            cx = self.rect.x + 6 + prefix.get_width()
            pygame.draw.line(surf, TEXT, (cx, self.rect.y + 4), (cx, self.rect.bottom - 4), 1)
        surf.set_clip(clip)


class Checkbox:
    def __init__(self, rect, value: bool = True, on_change: Optional[Callable] = None):
        self.rect = pygame.Rect(rect)
        self.value = value
        self.on_change = on_change

    def handle_event(self, event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.value = not self.value
                if self.on_change:
                    self.on_change(self.value)
                return True
        return False

    def draw(self, surf):
        draw_rect(surf, self.rect, INPUT_BG, border=1, radius=3)
        if self.value:
            inner = self.rect.inflate(-6, -6)
            draw_rect(surf, inner, SUCCESS, radius=2)
