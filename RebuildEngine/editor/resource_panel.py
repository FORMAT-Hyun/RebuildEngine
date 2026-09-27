"""GameMaker-style resource panel: sprites and animations are one resource type."""
from __future__ import annotations
import os
import pygame
from typing import Optional, List, Callable
from .ui import draw_rect, draw_text, TEXT, TEXT_DIM, ACCENT, BORDER, BG_PANEL, BG_PANEL2, BG_HOVER, BG_ACTIVE, INPUT_BG


class ResourcePanel:
    CATEGORIES = ("objects", "sprites", "music", "scenes")
    LABELS = {"objects": "오브젝트", "sprites": "스프라이트", "music": "음악", "scenes": "씬"}
    ATTRS = {"objects": "object_names", "sprites": "sprite_files", "music": "music_files", "scenes": "scene_files"}

    def __init__(self, rect: pygame.Rect):
        self.rect = pygame.Rect(rect)
        self.object_names: List[str] = []
        self.sprite_files: List[str] = []
        self.music_files: List[str] = []
        self.scene_files: List[str] = []
        self.selected_object: Optional[str] = None
        self.selected_sprite: Optional[str] = None
        self.selected_music: Optional[str] = None
        self.selected_scene: Optional[str] = None
        self.active_category = "objects"
        self.scroll = 0
        self.item_h = 30
        self.on_select_object: Optional[Callable[[str], None]] = None
        self.on_select_sprite: Optional[Callable[[str], None]] = None
        self.on_select_music: Optional[Callable[[str], None]] = None
        self.on_select_scene: Optional[Callable[[str], None]] = None
        self.sprite_manager = None
        self.project = None
        self._thumb_cache = {}
        self._last_resource_signature = None
        self._last_action = ""

    def set_rect(self, rect):
        self.rect = pygame.Rect(rect)
        self._clamp_scroll()

    def set_data(self, object_names, sprite_files, music_files=None, scene_files=None):
        signature = (tuple(object_names), tuple(sprite_files), tuple(music_files or []), tuple(scene_files or []))
        self.object_names = list(object_names)
        self.sprite_files = list(sprite_files)
        self.music_files = list(music_files or [])
        self.scene_files = list(scene_files or [])
        if signature != self._last_resource_signature:
            self._last_resource_signature = signature
            valid = set(self.sprite_files)
            self._thumb_cache = {k:v for k,v in self._thumb_cache.items() if k in valid}
        self._clamp_scroll()

    def _items(self):
        return getattr(self, self.ATTRS[self.active_category])

    def _clamp_scroll(self):
        visible = max(1, (self.rect.h - 105) // self.item_h)
        self.scroll = max(0, min(self.scroll, max(0, len(self._items()) - visible)))

    def _tab_rects(self):
        tab_area = pygame.Rect(self.rect.x + 6, self.rect.y + 38, self.rect.w - 12, 56)
        half = tab_area.w // 2
        out = {}
        for i, cat in enumerate(self.CATEGORIES):
            row, col = divmod(i, 2)
            x = tab_area.x + col * half
            w = half if col == 0 else tab_area.right - x
            out[cat] = pygame.Rect(x, tab_area.y + row*27, w-3, 24)
        return out

    def _body_rect(self):
        return pygame.Rect(self.rect.x + 5, self.rect.y + 102, self.rect.w - 10, max(1, self.rect.h - 108))

    def _item_rect(self, index):
        body = self._body_rect()
        y = body.y + index*self.item_h - self.scroll*self.item_h
        return pygame.Rect(body.x, y, body.w, self.item_h - 3)

    def _thumb(self, name: str):
        cached = self._thumb_cache.get(name)
        if cached is not None:
            return cached
        if not self.sprite_manager:
            return None
        try:
            img = self.sprite_manager.get(name).get_frame(0)
            th = pygame.transform.scale(img, (22,22)).convert_alpha()
            self._thumb_cache[name] = th
            return th
        except Exception:
            return None

    def _selected_value(self):
        return {"objects":self.selected_object, "sprites":self.selected_sprite, "music":self.selected_music, "scenes":self.selected_scene}[self.active_category]

    def _select(self, item):
        if self.active_category == "objects":
            self.selected_object = item
            if self.on_select_object: self.on_select_object(item)
        elif self.active_category == "sprites":
            self.selected_sprite = item
            if self.on_select_sprite: self.on_select_sprite(item)
        elif self.active_category == "music":
            self.selected_music = item
            if self.on_select_music: self.on_select_music(item)
        else:
            self.selected_scene = item
            if self.on_select_scene: self.on_select_scene(item)

    def handle_event(self, event):
        self._last_action = ""
        if event.type == pygame.MOUSEWHEEL:
            if self._body_rect().collidepoint(pygame.mouse.get_pos()):
                self.scroll -= event.y
                self._clamp_scroll()
                return True
            return False
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1 or not self.rect.collidepoint(event.pos):
            return False
        for cat, r in self._tab_rects().items():
            if r.collidepoint(event.pos):
                self.active_category = cat
                self.scroll = 0
                self._last_action = "tab"
                return True
        for i, item in enumerate(self._items()):
            if self._item_rect(i).collidepoint(event.pos):
                self._select(item)
                self._last_action = "item"
                return True
        return True

    def _display_name(self, item: str):
        if self.active_category == "sprites" and item.endswith('.anim.json'):
            base = os.path.basename(item)[:-9]
            return f"{base}  ·  애니메이션"
        return os.path.basename(item)

    def draw(self, surf):
        draw_rect(surf, self.rect, BG_PANEL, border=1)
        header = pygame.Rect(self.rect.x, self.rect.y, self.rect.w, 32)
        draw_rect(surf, header, BG_PANEL2)
        draw_text(surf, "리소스", (header.x+10, header.y+7), TEXT, 14, bold=True)
        mouse = pygame.mouse.get_pos()
        for cat, r in self._tab_rects().items():
            active = cat == self.active_category
            draw_rect(surf, r, BG_ACTIVE if active else (BG_HOVER if r.collidepoint(mouse) else INPUT_BG), border=1, border_color=ACCENT if active else BORDER, radius=4)
            draw_text(surf, self.LABELS[cat], r.center, TEXT if active else TEXT_DIM, 12, bold=active, center=True)
        cap = pygame.Rect(self.rect.x+6, self.rect.y+94, self.rect.w-12, 22)
        draw_text(surf, self.LABELS[self.active_category], (cap.x+5, cap.y+3), TEXT_DIM, 11)
        pygame.draw.line(surf, BORDER, (cap.x, cap.bottom), (cap.right, cap.bottom))
        body = self._body_rect()
        clip = surf.get_clip(); surf.set_clip(body)
        items = self._items(); selected = self._selected_value()
        if not items:
            hints = {"objects":"+ → 오브젝트", "sprites":"+ → 스프라이트", "music":"+ → 음악", "scenes":"+ → 씬"}
            draw_text(surf, hints[self.active_category], (body.x+8, body.y+14), TEXT_DIM, 11)
        else:
            for i, item in enumerate(items):
                r = self._item_rect(i)
                if r.bottom < body.top or r.top > body.bottom: continue
                hover = r.collidepoint(mouse)
                if item == selected: draw_rect(surf, r, BG_ACTIVE, radius=4)
                elif hover: draw_rect(surf, r, BG_HOVER, radius=4)
                icon_x = r.x+8
                label_color = TEXT
                if self.active_category in ("objects","sprites"):
                    thumb_name = item
                    if self.active_category == "objects" and self.project and item in self.project.objects:
                        thumb_name = self.project.objects[item].sprite
                    th = self._thumb(thumb_name) if thumb_name else None
                    if th:
                        surf.blit(th, (r.x+5, r.y+4)); icon_x = r.x+33
                    else:
                        draw_text(surf, "◆" if self.active_category == "sprites" else "●", (r.x+8, r.y+5), ACCENT, 11); icon_x = r.x+27
                elif self.active_category == "music":
                    draw_text(surf, "♪", (r.x+8, r.y+5), ACCENT, 13); icon_x = r.x+29
                else:
                    draw_text(surf, "▣", (r.x+8, r.y+5), ACCENT, 12); icon_x = r.x+29
                draw_text(surf, self._display_name(item), (icon_x, r.y+7), label_color, 11)
        surf.set_clip(clip)
