"""Left panel: instance list in the current scene."""

import pygame
from typing import Optional, List, Callable, Any
from .ui import draw_rect, draw_text, BG_PANEL, BG_HOVER, BG_ACTIVE, BORDER, TEXT, TEXT_DIM, ACCENT


class ObjectList:
    def __init__(self, rect: pygame.Rect):
        self.rect = pygame.Rect(rect)
        self.selected_id: Optional[int] = None
        self.scroll = 0
        self.item_height = 28
        self.on_select: Optional[Callable] = None
        self.on_delete: Optional[Callable] = None

    def set_rect(self, rect):
        self.rect = pygame.Rect(rect)

    def handle_event(self, event, instances: List[Any]) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not self.rect.collidepoint(event.pos):
                return False
            local_y = event.pos[1] - self.rect.y - 32 + self.scroll
            if local_y < 0:
                return False
            idx = int(local_y // self.item_height)
            if 0 <= idx < len(instances):
                inst = instances[idx]
                self.selected_id = inst.id
                if self.on_select:
                    self.on_select(inst)
                return True
        if event.type == pygame.MOUSEWHEEL and self.rect.collidepoint(pygame.mouse.get_pos()):
            self.scroll = max(0, self.scroll - event.y * 20)
            return True
        if event.type == pygame.KEYDOWN and event.key == pygame.K_DELETE:
            if self.selected_id is not None and self.on_delete:
                self.on_delete(self.selected_id)
                return True
        return False

    def draw(self, surf, instances: List[Any]):
        draw_rect(surf, self.rect, BG_PANEL, border=1)
        # header
        header = pygame.Rect(self.rect.x, self.rect.y, self.rect.w, 28)
        draw_rect(surf, header, (45, 45, 58))
        draw_text(surf, "Object 목록", (self.rect.x + 10, self.rect.y + 6), TEXT, 14, bold=True)
        draw_text(surf, f"({len(instances)})", (self.rect.x + 110, self.rect.y + 7), TEXT_DIM, 12)

        clip = surf.get_clip()
        content = pygame.Rect(self.rect.x, self.rect.y + 28, self.rect.w, self.rect.h - 28)
        surf.set_clip(content)

        y = self.rect.y + 32 - self.scroll
        for inst in instances:
            item = pygame.Rect(self.rect.x + 4, y, self.rect.w - 8, self.item_height - 2)
            if inst.id == self.selected_id:
                draw_rect(surf, item, BG_ACTIVE, radius=3)
            elif item.collidepoint(pygame.mouse.get_pos()):
                draw_rect(surf, item, BG_HOVER, radius=3)
            name = inst.object_name
            draw_text(surf, name, (item.x + 8, item.y + 5), TEXT, 13)
            draw_text(surf, f"#{inst.id}", (item.right - 40, item.y + 6), TEXT_DIM, 11)
            y += self.item_height

        surf.set_clip(clip)
