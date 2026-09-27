"""Small sprite-sheet animation creation dialog."""
from __future__ import annotations
import pygame
from typing import Callable, Optional
from .ui import draw_rect, draw_text, TextInput, TEXT, TEXT_DIM, ACCENT, DANGER, BG_PANEL2, INPUT_BG, BORDER


class AnimationDialog:
    def __init__(self):
        self.active = False
        self.source_path: Optional[str] = None
        self.name = TextInput((0,0,1,1), "player_walk")
        self.frame_w = TextInput((0,0,1,1), "32", numeric=True)
        self.frame_h = TextInput((0,0,1,1), "32", numeric=True)
        self.fps = TextInput((0,0,1,1), "10", numeric=True)
        self.error = ""
        self.on_create: Optional[Callable] = None

    def open(self, source_path: str, default_w: int = 32, default_h: int = 32, on_create: Optional[Callable] = None):
        self.active = True
        self.source_path = source_path
        self.name.set_value("anim_" + source_path.rsplit("/", 1)[-1].rsplit("\\", 1)[-1].rsplit(".", 1)[0])
        self.frame_w.set_value(str(default_w))
        self.frame_h.set_value(str(default_h))
        self.fps.set_value("10")
        self.error = ""
        self.on_create = on_create
        self.name.active = True

    def close(self):
        self.active = False
        for f in (self.name, self.frame_w, self.frame_h, self.fps):
            f.active = False

    def confirm(self):
        try:
            name = self.name.value.strip()
            fw = int(float(self.frame_w.value))
            fh = int(float(self.frame_h.value))
            fps = float(self.fps.value)
            if not name:
                raise ValueError("애니메이션 이름을 입력하세요")
            if fw <= 0 or fh <= 0:
                raise ValueError("프레임 크기는 1 이상이어야 합니다")
            if fps <= 0 or fps > 120:
                raise ValueError("FPS는 0보다 크고 120 이하로 입력하세요")
            if self.on_create:
                self.on_create(name, fw, fh, fps)
            self.close()
        except Exception as e:
            self.error = str(e)

    def handle_event(self, event) -> bool:
        if not self.active:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.close(); return True
            if event.key == pygame.K_RETURN:
                self.confirm(); return True
        handled = False
        for f in (self.name, self.frame_w, self.frame_h, self.fps):
            if f.handle_event(event): handled = True
        return handled or self.active

    def draw(self, surf):
        if not self.active:
            return
        sw, sh = surf.get_size()
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0,0,0,150))
        surf.blit(overlay, (0,0))
        box = pygame.Rect(sw//2-220, sh//2-180, 440, 360)
        draw_rect(surf, box, BG_PANEL2, border=1, border_color=ACCENT, radius=8)
        draw_text(surf, "스프라이트 애니메이션 만들기", (box.x+20, box.y+18), TEXT, 16, bold=True)
        source = self.source_path or ""
        draw_text(surf, "스프라이트 시트: " + source, (box.x+20, box.y+48), TEXT_DIM, 11)
        rows = [("이름", self.name), ("프레임 너비", self.frame_w), ("프레임 높이", self.frame_h), ("FPS", self.fps)]
        y = box.y+82
        for label, field in rows:
            draw_text(surf, label, (box.x+20, y+5), TEXT_DIM, 11)
            field.rect = pygame.Rect(box.x+125, y, 270, 27)
            field.draw(surf)
            y += 45
        if self.error:
            draw_text(surf, self.error, (box.x+20, box.y+275), DANGER, 11)
        draw_text(surf, "Enter 생성 · Esc 취소", (box.x+20, box.bottom-28), TEXT_DIM, 11)
