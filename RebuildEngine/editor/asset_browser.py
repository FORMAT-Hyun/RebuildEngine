"""Asset browser with thumbnails and sprite assignment."""

from __future__ import annotations

import os
import pygame
from typing import List, Optional, Callable, Dict
from .ui import draw_rect, draw_text, BG_PANEL, BG_HOVER, BG_ACTIVE, TEXT, TEXT_DIM, BORDER, ACCENT, SUCCESS


class AssetBrowser:
    def __init__(self, rect: pygame.Rect, assets_path: str, sprite_manager=None):
        self.rect = pygame.Rect(rect)
        self.assets_path = assets_path
        self.sprite_manager = sprite_manager
        self.files: List[str] = []
        self.selected: Optional[str] = None
        self.scroll = 0
        self.item_h = 40  # room for thumbnail
        self.on_select: Optional[Callable] = None
        self.on_assign: Optional[Callable] = None
        self._last_click_time = 0
        self._last_click_name = None
        self._thumbs: Dict[str, pygame.Surface] = {}
        self.refresh()

    def set_rect(self, rect):
        self.rect = pygame.Rect(rect)

    def set_sprite_manager(self, sm):
        self.sprite_manager = sm
        self._thumbs.clear()

    def refresh(self):
        self.files = []
        self._thumbs.clear()
        if not os.path.isdir(self.assets_path):
            return
        for name in sorted(os.listdir(self.assets_path)):
            lower = name.lower()
            if lower.endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif")):
                self.files.append(name)

    def _thumb(self, name: str) -> Optional[pygame.Surface]:
        if name in self._thumbs:
            return self._thumbs[name]
        path = os.path.join(self.assets_path, name)
        try:
            if self.sprite_manager:
                spr = self.sprite_manager.get(name)
                img = spr.get_frame(0)
            else:
                img = pygame.image.load(path).convert_alpha()
            thumb = pygame.transform.smoothscale(img, (28, 28))
            self._thumbs[name] = thumb
            return thumb
        except Exception:
            surf = pygame.Surface((28, 28))
            surf.fill((80, 80, 100))
            self._thumbs[name] = surf
            return surf

    def handle_event(self, event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not self.rect.collidepoint(event.pos):
                return False
            # assign button area at bottom of header
            local_y = event.pos[1] - self.rect.y - 32 + self.scroll
            if local_y < 0:
                return False
            idx = int(local_y // self.item_h)
            if 0 <= idx < len(self.files):
                name = self.files[idx]
                now = pygame.time.get_ticks()
                # double-click = assign
                if (
                    self._last_click_name == name
                    and now - self._last_click_time < 400
                    and self.on_assign
                ):
                    self.selected = name
                    self.on_assign(name)
                    self._last_click_time = 0
                    return True
                self._last_click_name = name
                self._last_click_time = now
                self.selected = name
                if self.on_select:
                    self.on_select(name)
                return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            if self.rect.collidepoint(event.pos):
                local_y = event.pos[1] - self.rect.y - 32 + self.scroll
                idx = int(local_y // self.item_h) if local_y >= 0 else -1
                if 0 <= idx < len(self.files):
                    self.selected = self.files[idx]
                if self.selected and self.on_assign:
                    self.on_assign(self.selected)
                    return True
        if event.type == pygame.MOUSEWHEEL and self.rect.collidepoint(pygame.mouse.get_pos()):
            self.scroll = max(0, self.scroll - event.y * 24)
            return True
        return False

    def draw(self, surf):
        draw_rect(surf, self.rect, BG_PANEL, border=1)
        header = pygame.Rect(self.rect.x, self.rect.y, self.rect.w, 28)
        draw_rect(surf, header, (45, 45, 58))
        draw_text(surf, "Assets", (self.rect.x + 10, self.rect.y + 6), TEXT, 14, bold=True)
        draw_text(surf, "더블클릭/우클릭=붙이기", (self.rect.x + 70, self.rect.y + 8), TEXT_DIM, 10)

        clip = surf.get_clip()
        content = pygame.Rect(self.rect.x, self.rect.y + 28, self.rect.w, self.rect.h - 28)
        surf.set_clip(content)

        if not self.files:
            draw_text(surf, "이미지 없음", (self.rect.x + 12, self.rect.y + 48), TEXT_DIM, 12)
            draw_text(surf, "[이미지] 버튼으로 가져오기", (self.rect.x + 12, self.rect.y + 68), TEXT_DIM, 11)
            surf.set_clip(clip)
            return

        y = self.rect.y + 32 - self.scroll
        for name in self.files:
            item = pygame.Rect(self.rect.x + 4, y, self.rect.w - 8, self.item_h - 2)
            if name == self.selected:
                draw_rect(surf, item, BG_ACTIVE, radius=3)
            elif item.collidepoint(pygame.mouse.get_pos()):
                draw_rect(surf, item, BG_HOVER, radius=3)
            th = self._thumb(name)
            if th:
                surf.blit(th, (item.x + 4, item.y + 4))
            draw_text(surf, name, (item.x + 38, item.y + 10), TEXT, 12)
            y += self.item_h

        surf.set_clip(clip)
