"""In-editor file browser for importing external files (no tkinter required)."""

from __future__ import annotations

import os
import pygame
from typing import Optional, List, Callable, Tuple
from .ui import (
    draw_rect, draw_text, Button, TextInput, Fonts,
    BG_PANEL, BG_PANEL2, BG_HOVER, BG_ACTIVE, TEXT, TEXT_DIM,
    ACCENT, BORDER, INPUT_BG, DANGER,
)


class FileDialog:
    """Modal file browser. mode: 'open_file' | 'open_files' | 'save_file'"""

    def __init__(self):
        self.active = False
        self.mode = "open_file"
        self.title = "파일 열기"
        self.cwd = os.path.expanduser("~")
        self.extensions: Optional[List[str]] = None  # e.g. ['.png', '.jpg']
        self.entries: List[Tuple[str, bool]] = []  # (name, is_dir)
        self.selected: Optional[str] = None
        self.scroll = 0
        self.item_h = 24
        self.on_result: Optional[Callable[[Optional[str]], None]] = None
        self.path_input = TextInput((0, 0, 400, 26), "")
        self.error = ""
        self.rect = pygame.Rect(0, 0, 560, 420)

    def open(
        self,
        title: str = "파일 선택",
        start_dir: Optional[str] = None,
        extensions: Optional[List[str]] = None,
        on_result: Optional[Callable] = None,
        mode: str = "open_file",
    ):
        self.active = True
        self.title = title
        self.mode = mode
        self.extensions = [e.lower() if e.startswith(".") else f".{e.lower()}" for e in (extensions or [])] or None
        self.on_result = on_result
        self.selected = None
        self.error = ""
        self.scroll = 0
        if start_dir and os.path.isdir(start_dir):
            self.cwd = os.path.abspath(start_dir)
        else:
            self.cwd = os.path.abspath(os.path.expanduser("~"))
        if not os.path.isdir(self.cwd):
            self.cwd = os.path.abspath(".")
        self.path_input.set_value(self.cwd)
        self.path_input.active = False
        self._refresh()

    def _refresh(self):
        self.entries = []
        try:
            names = os.listdir(self.cwd)
        except Exception as e:
            self.error = str(e)
            names = []
        dirs = []
        files = []
        for n in names:
            if n.startswith("."):
                continue
            full = os.path.join(self.cwd, n)
            try:
                if os.path.isdir(full):
                    dirs.append(n)
                elif os.path.isfile(full):
                    if self.extensions:
                        ext = os.path.splitext(n)[1].lower()
                        if ext not in self.extensions:
                            continue
                    files.append(n)
            except Exception:
                continue
        for d in sorted(dirs, key=str.lower):
            self.entries.append((d, True))
        for f in sorted(files, key=str.lower):
            self.entries.append((f, False))
        self.scroll = 0
        self.selected = None

    def _go_up(self):
        parent = os.path.dirname(self.cwd.rstrip(os.sep))
        if parent and parent != self.cwd:
            self.cwd = parent
            self.path_input.set_value(self.cwd)
            self._refresh()

    def _enter(self, name: str, is_dir: bool):
        full = os.path.join(self.cwd, name)
        if is_dir:
            self.cwd = full
            self.path_input.set_value(self.cwd)
            self._refresh()
        else:
            self.selected = full
            self._confirm()

    def _confirm(self):
        # folder mode: use selected dir or current cwd
        if getattr(self, "mode", "") == "open_folder":
            path = self.selected
            if path and os.path.isfile(path):
                path = os.path.dirname(path)
            if not path or not os.path.isdir(path):
                path = self.cwd
            if not os.path.isdir(path):
                self.error = "폴더를 선택하세요"
                return
            self.active = False
            if self.on_result:
                self.on_result(path)
            return

        path = self.selected
        if not path:
            typed = self.path_input.value.strip()
            if typed and os.path.isfile(typed):
                path = typed
            elif typed and os.path.isdir(typed):
                self.cwd = typed
                self.path_input.set_value(self.cwd)
                self._refresh()
                return
            else:
                self.error = "파일을 선택하세요"
                return
        if self.extensions:
            ext = os.path.splitext(path)[1].lower()
            if ext not in self.extensions:
                self.error = f"지원 확장자: {', '.join(self.extensions)}"
                return
        self.active = False
        if self.on_result:
            self.on_result(path)

    def _cancel(self):
        self.active = False
        if self.on_result:
            self.on_result(None)

    def handle_event(self, event) -> bool:
        if not self.active:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._cancel()
                return True
            if event.key == pygame.K_RETURN:
                if self.path_input.active:
                    typed = self.path_input.value.strip()
                    if os.path.isdir(typed):
                        self.cwd = typed
                        self._refresh()
                    elif os.path.isfile(typed):
                        self.selected = typed
                        self._confirm()
                    return True
                if self.selected:
                    name = os.path.basename(self.selected)
                    is_dir = os.path.isdir(self.selected)
                    self._enter(name, is_dir)
                return True
            if event.key == pygame.K_BACKSPACE and not self.path_input.active:
                self._go_up()
                return True
        if self.path_input.handle_event(event):
            return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            # up button
            up_r = pygame.Rect(self.rect.x + 8, self.rect.y + 40, 50, 26)
            if up_r.collidepoint(mx, my):
                self._go_up()
                return True
            # list area
            list_r = pygame.Rect(self.rect.x + 8, self.rect.y + 100, self.rect.w - 16, self.rect.h - 160)
            if list_r.collidepoint(mx, my):
                local_y = my - list_r.y + self.scroll
                idx = int(local_y // self.item_h)
                if 0 <= idx < len(self.entries):
                    name, is_dir = self.entries[idx]
                    full = os.path.join(self.cwd, name)
                    # double-click detection simplified: single click select, second click same enters
                    if self.selected == full:
                        self._enter(name, is_dir)
                    else:
                        self.selected = full
                        if not is_dir:
                            self.path_input.set_value(full)
                return True
            # OK / Cancel
            ok_r = pygame.Rect(self.rect.right - 180, self.rect.bottom - 40, 80, 28)
            cancel_r = pygame.Rect(self.rect.right - 90, self.rect.bottom - 40, 80, 28)
            if ok_r.collidepoint(mx, my):
                self._confirm()
                return True
            if cancel_r.collidepoint(mx, my):
                self._cancel()
                return True
        if event.type == pygame.MOUSEWHEEL:
            list_r = pygame.Rect(self.rect.x + 8, self.rect.y + 100, self.rect.w - 16, self.rect.h - 160)
            if list_r.collidepoint(pygame.mouse.get_pos()):
                self.scroll = max(0, self.scroll - event.y * 30)
                return True
        return True  # consume all while modal

    def draw(self, surf: pygame.Surface):
        if not self.active:
            return
        sw, sh = surf.get_size()
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        surf.blit(overlay, (0, 0))

        self.rect = pygame.Rect((sw - 560) // 2, (sh - 420) // 2, 560, 420)
        draw_rect(surf, self.rect, BG_PANEL2, border=1, border_color=ACCENT, radius=8)
        draw_text(surf, self.title, (self.rect.x + 16, self.rect.y + 12), TEXT, 16, bold=True)

        # Up button
        up_r = pygame.Rect(self.rect.x + 8, self.rect.y + 40, 50, 26)
        draw_rect(surf, up_r, BG_HOVER, border=1, radius=4)
        draw_text(surf, "↑ 상위", (up_r.x + 6, up_r.y + 5), TEXT, 12)

        # path
        self.path_input.rect = pygame.Rect(self.rect.x + 64, self.rect.y + 40, self.rect.w - 72, 26)
        self.path_input.draw(surf)

        # list
        list_r = pygame.Rect(self.rect.x + 8, self.rect.y + 100, self.rect.w - 16, self.rect.h - 160)
        draw_rect(surf, list_r, INPUT_BG, border=1)
        clip = surf.get_clip()
        surf.set_clip(list_r)
        y = list_r.y + 2 - self.scroll
        for name, is_dir in self.entries:
            item = pygame.Rect(list_r.x + 2, y, list_r.w - 4, self.item_h - 2)
            full = os.path.join(self.cwd, name)
            if full == self.selected:
                draw_rect(surf, item, BG_ACTIVE, radius=2)
            elif item.collidepoint(pygame.mouse.get_pos()):
                draw_rect(surf, item, BG_HOVER, radius=2)
            prefix = "📁 " if is_dir else "📄 "
            draw_text(surf, prefix + name, (item.x + 6, item.y + 3), TEXT, 13)
            y += self.item_h
        surf.set_clip(clip)

        if self.error:
            draw_text(surf, self.error, (self.rect.x + 12, self.rect.bottom - 70), DANGER, 12)

        ok_r = pygame.Rect(self.rect.right - 180, self.rect.bottom - 40, 80, 28)
        cancel_r = pygame.Rect(self.rect.right - 90, self.rect.bottom - 40, 80, 28)
        draw_rect(surf, ok_r, ACCENT, border=1, radius=4)
        draw_text(surf, "선택", ok_r.center, TEXT, 13, center=True)
        draw_rect(surf, cancel_r, BG_HOVER, border=1, radius=4)
        draw_text(surf, "취소", cancel_r.center, TEXT, 13, center=True)
